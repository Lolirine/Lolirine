# -*- coding: utf-8 -*-
"""Pool Store — circuit commande client → bons fournisseurs → factures.

Tout est calculé à la volée (aucun champ stocké) : marge prévue et réelle,
liens entre commande, bons, factures client et fournisseur, contrôle de la
facture fournisseur, lien de suivi du colis, garde-fou « client payé »,
estimation du port SCP et bons en retard.
"""
import logging
from datetime import timedelta

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

EXPEDITEUR = 'Lolirine Pool Store <info@lolirinepoolstore.be>'
TOLERANCE = 0.05  # € d'écart toléré entre facture fournisseur et bon

# Conditions de port SCP Benelux 2026 (catalogue p. 434)
SCP_FRANCO = 1200.0
SCP_TRANCHES = [(200, 7.5), (400, 12.0), (600, 15.0), (800, 20.0), (1000, 25.0), (1200, 35.0)]
SCP_ADRESSE_PRIVEE = 17.0
SCP_GESTION = 20.0

SUIVI_URLS = [
    (('bpost',), 'https://track.bpost.cloud/btr/web/#/search?itemCode={n}&lang={lg}'),
    (('dhl',), 'https://www.dhl.com/be-{lg}/home/tracking.html?tracking-id={n}'),
    (('ups',), 'https://www.ups.com/track?loc={lg}_BE&tracknum={n}'),
    (('dpd',), 'https://tracking.dpd.de/status/{lg}_BE/parcel/{n}'),
    (('gls',), 'https://gls-group.com/BE/{lg}/suivi-colis?match={n}'),
    (('postnl',), 'https://jouw.postnl.be/track-and-trace/{n}'),
    (('tnt',), 'https://www.tnt.com/express/{lg}_be/site/shipping-tools/tracking.html?searchType=con&cons={n}'),
    (('fedex',), 'https://www.fedex.com/fedextrack/?trknbr={n}'),
    (('colissimo', 'la poste'), 'https://www.laposte.fr/outils/suivre-vos-envois?code={n}'),
    (('chronopost',), 'https://www.chronopost.fr/tracking-no-cms/suivi-page?listeNumerosLT={n}'),
]


def _langue(partner):
    code = (partner.lang or 'fr').lower()
    return 'nl' if code.startswith('nl') else 'en' if code.startswith('en') else 'fr'


def _tr(lg, fr, nl, en):
    return {'fr': fr, 'nl': nl, 'en': en}[lg]


def lien_suivi(transporteur, numero, lg='fr'):
    """URL de suivi du colis, ou False si le transporteur n'est pas reconnu."""
    if not numero:
        return False
    t = (transporteur or '').lower()
    for cles, modele in SUIVI_URLS:
        if any(c in t for c in cles):
            return modele.format(n=numero.strip().replace(' ', ''), lg=lg if lg != 'en' else 'en')
    return False


def _eur(montant):
    return ('%.2f €' % (montant or 0.0)).replace('.', ',')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    pool_achats_ht = fields.Monetary('Achats fournisseurs HT', compute='_compute_pool_chiffres')
    pool_port_estime = fields.Monetary('Port fournisseur estimé', compute='_compute_pool_chiffres')
    pool_marge = fields.Monetary('Marge prévue', compute='_compute_pool_chiffres')
    pool_marge_pct = fields.Float('Marge prévue (%)', compute='_compute_pool_chiffres')
    pool_marge_reelle = fields.Monetary('Marge réelle (factures)', compute='_compute_pool_chiffres')
    pool_marge_reelle_ok = fields.Boolean(compute='_compute_pool_chiffres')
    pool_client_paye = fields.Boolean('Client payé', compute='_compute_pool_chiffres')
    pool_paiement_txt = fields.Char('Paiement client', compute='_compute_pool_chiffres')
    pool_bill_count = fields.Integer('Factures fournisseurs', compute='_compute_pool_chiffres')
    pool_tracking_url = fields.Char('Suivi du colis', compute='_compute_pool_chiffres')
    pool_compte_id = fields.Many2one('account.analytic.account', compute='_compute_pool_chiffres')

    def _pool_bons(self):
        return self.dropship_purchase_ids.filtered(lambda p: p.state != 'cancel')

    def _pool_paye(self):
        """Montant reçu du client : paiements en ligne + factures payées."""
        self.ensure_one()
        recu = self.amount_paid or 0.0
        factures = self.invoice_ids.filtered(lambda m: m.state == 'posted' and m.move_type == 'out_invoice')
        recu = max(recu, sum(f.amount_total - f.amount_residual for f in factures))
        return recu

    @api.depends('amount_untaxed', 'amount_total', 'dropship_purchase_ids.amount_untaxed',
                 'dropship_purchase_ids.state', 'invoice_ids.state')
    def _compute_pool_chiffres(self):
        Compte = self.env['account.analytic.account'].sudo()
        for o in self:
            bons = o._pool_bons() if o.id else self.env['purchase.order']
            achats = sum(bons.mapped('amount_untaxed'))
            port = sum(b._pool_port_estime() for b in bons)
            o.pool_achats_ht = achats
            o.pool_port_estime = port
            o.pool_marge = o.amount_untaxed - achats - port
            o.pool_marge_pct = (o.pool_marge / o.amount_untaxed * 100.0) if o.amount_untaxed else 0.0
            # marge réelle : factures validées (avoirs déduits)
            fact_cli = o.invoice_ids.filtered(lambda m: m.state == 'posted')
            fact_four = bons.mapped('invoice_ids').filtered(lambda m: m.state == 'posted')
            o.pool_bill_count = len(bons.mapped('invoice_ids'))
            o.pool_marge_reelle_ok = bool(fact_cli and fact_four)
            o.pool_marge_reelle = sum(fact_cli.mapped('amount_untaxed_signed')) \
                + sum(fact_four.mapped('amount_untaxed_signed'))  # factures fournisseurs : montants négatifs
            recu = o._pool_paye() if o.id else 0.0
            o.pool_client_paye = o.amount_total > 0 and recu >= o.amount_total - 0.01
            o.pool_paiement_txt = _('Payé') if o.pool_client_paye else \
                _('Non payé — %s reçus sur %s') % (_eur(recu), _eur(o.amount_total))
            avec_suivi = bons.filtered('dropship_tracking_number')[:1]
            o.pool_tracking_url = avec_suivi.pool_tracking_url if avec_suivi else False
            o.pool_compte_id = Compte.search([('code', '=', o.name)], limit=1) if o.name else False

    def action_pool_factures_fournisseurs(self):
        self.ensure_one()
        factures = self._pool_bons().mapped('invoice_ids')
        return {
            'name': _('Factures fournisseurs — %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', factures.ids)],
            'context': {'default_move_type': 'in_invoice', 'create': False},
        }

    def action_pool_marge_analytique(self):
        self.ensure_one()
        compte = self.pool_compte_id or self._pool_compte_analytique()
        if not compte:
            raise UserError(_("Pas de compte analytique pour %s.") % self.name)
        return {
            'name': _('Marge — %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_mode': 'list,pivot,form',
            'domain': [('auto_account_id', '=', compte.id)],
            'context': {'create': False},
        }


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    pool_vente_ht = fields.Monetary('Vente client HT', compute='_compute_pool_transversal')
    pool_achats_ht = fields.Monetary('Achats HT (tous les bons)', compute='_compute_pool_transversal')
    pool_port_estime = fields.Monetary('Port fournisseur estimé', compute='_compute_pool_transversal')
    pool_port_detail = fields.Char('Détail du port', compute='_compute_pool_transversal')
    pool_marge = fields.Monetary('Marge prévue', compute='_compute_pool_transversal')
    pool_marge_pct = fields.Float('Marge prévue (%)', compute='_compute_pool_transversal')
    pool_marge_reelle = fields.Monetary('Marge réelle', compute='_compute_pool_transversal')
    pool_marge_reelle_ok = fields.Boolean(compute='_compute_pool_transversal')
    pool_client_paye = fields.Boolean('Client payé', compute='_compute_pool_transversal')
    pool_paiement_txt = fields.Char('Paiement client', compute='_compute_pool_transversal')
    pool_client_invoice_count = fields.Integer('Factures client', compute='_compute_pool_transversal')
    pool_autres_bc_count = fields.Integer('Autres bons', compute='_compute_pool_transversal')
    pool_facture_etat = fields.Selection([
        ('attente', 'En attente de facture'),
        ('conforme', 'Facture conforme'),
        ('ecart', 'Écart facture / bon'),
    ], string='Facture fournisseur', compute='_compute_pool_transversal')
    pool_facture_ecart = fields.Monetary('Écart facture − bon', compute='_compute_pool_transversal')
    pool_tracking_url = fields.Char('Lien de suivi', compute='_compute_pool_transversal')
    pool_en_retard = fields.Boolean('En retard', compute='_compute_pool_transversal')
    pool_retard_txt = fields.Char('Retard', compute='_compute_pool_transversal')

    # ── calculs ───────────────────────────────────────────────────────────
    def _pool_est_scp(self):
        return 'scp' in (self.partner_id.commercial_partner_id.name or '').lower()

    def _pool_port_detail(self):
        """[(libellé, montant)] du port fournisseur estimé (SCP uniquement)."""
        self.ensure_one()
        if not self.is_dropship_order or not self._pool_est_scp():
            return []
        net = self.amount_untaxed
        lignes = []
        if net < SCP_FRANCO:
            forfait = next((m for seuil, m in SCP_TRANCHES if net < seuil), SCP_TRANCHES[-1][1])
            lignes.append((_('forfait < franco'), forfait))
        adresse = self.dest_address_id or self.dropship_sale_id.partner_shipping_id
        if adresse and not adresse.commercial_partner_id.is_company:
            lignes.append((_('adresse privée'), SCP_ADRESSE_PRIVEE))
        lignes.append((_('gestion'), SCP_GESTION))
        return lignes

    def _pool_port_estime(self):
        return sum(m for _l, m in self._pool_port_detail())

    @api.depends('amount_untaxed', 'state', 'invoice_ids.state', 'dropship_sale_id',
                 'dropship_tracking_number', 'dropship_carrier', 'dropship_status', 'date_planned')
    def _compute_pool_transversal(self):
        maintenant = fields.Datetime.now()
        aujourdhui = fields.Date.context_today(self)
        for po in self:
            so = po.dropship_sale_id
            detail = po._pool_port_detail() if po.id else []
            po.pool_port_detail = ' + '.join('%s %s' % (l, _eur(m)) for l, m in detail)
            if so:
                po.pool_vente_ht = so.amount_untaxed
                po.pool_achats_ht = so.pool_achats_ht
                po.pool_port_estime = so.pool_port_estime
                po.pool_marge = so.pool_marge
                po.pool_marge_pct = so.pool_marge_pct
                po.pool_marge_reelle = so.pool_marge_reelle
                po.pool_marge_reelle_ok = so.pool_marge_reelle_ok
                po.pool_client_paye = so.pool_client_paye
                po.pool_paiement_txt = so.pool_paiement_txt
                po.pool_client_invoice_count = len(so.invoice_ids)
                po.pool_autres_bc_count = len(so._pool_bons() - po)
            else:
                po.pool_vente_ht = po.pool_achats_ht = po.pool_port_estime = 0.0
                po.pool_marge = po.pool_marge_pct = po.pool_marge_reelle = 0.0
                po.pool_marge_reelle_ok = False
                po.pool_client_paye = True
                po.pool_paiement_txt = False
                po.pool_client_invoice_count = po.pool_autres_bc_count = 0
            # contrôle facture fournisseur (avoirs déduits)
            factures = po.invoice_ids.filtered(lambda m: m.state == 'posted')
            if not factures:
                po.pool_facture_etat = 'attente'
                po.pool_facture_ecart = 0.0
            else:
                facture = -sum(factures.mapped('amount_untaxed_signed'))
                po.pool_facture_ecart = facture - po.amount_untaxed
                po.pool_facture_etat = 'conforme' if abs(po.pool_facture_ecart) <= TOLERANCE else 'ecart'
            po.pool_tracking_url = lien_suivi(po.dropship_carrier, po.dropship_tracking_number) or False
            # retard : pas expédié après la date prévue, ou pas livré après la livraison prévue
            retard = False
            if po.is_dropship_order and po.state != 'cancel':
                if po.dropship_status in ('draft', 'sent', 'confirmed') and po.date_planned \
                        and po.date_planned + timedelta(days=1) < maintenant:
                    jours = (maintenant - po.date_planned).days
                    retard = _("Pas encore expédié — %d jour(s) après la date prévue") % jours
                elif po.dropship_status == 'shipped' and po.dropship_expected_delivery \
                        and po.dropship_expected_delivery < aujourdhui:
                    jours = (aujourdhui - po.dropship_expected_delivery).days
                    retard = _("Pas encore livré — %d jour(s) après la livraison prévue") % jours
            po.pool_en_retard = bool(retard)
            po.pool_retard_txt = retard or False

    # ── liens ─────────────────────────────────────────────────────────────
    def action_pool_factures_client(self):
        self.ensure_one()
        so = self.dropship_sale_id
        action = {
            'name': _('Factures client — %s') % so.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', so.invoice_ids.ids)],
            'context': {'create': False},
        }
        if len(so.invoice_ids) == 1:
            action.update(view_mode='form', res_id=so.invoice_ids.id)
        return action

    def action_pool_autres_bons(self):
        self.ensure_one()
        autres = self.dropship_sale_id._pool_bons() - self
        return {
            'name': _('Autres bons de %s') % self.dropship_sale_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', autres.ids)],
            'context': {'create': False},
        }

    def action_pool_marge_analytique(self):
        self.ensure_one()
        if not self.dropship_sale_id:
            raise UserError(_("Ce bon n'est lié à aucune commande client."))
        return self.dropship_sale_id.action_pool_marge_analytique()

    def action_pool_ouvrir_suivi(self):
        self.ensure_one()
        if not self.pool_tracking_url:
            raise UserError(_("Transporteur non reconnu ou numéro de suivi absent."))
        return {'type': 'ir.actions.act_url', 'url': self.pool_tracking_url, 'target': 'new'}

    # ── garde-fou : client payé ───────────────────────────────────────────
    def _pool_verifier_paiement(self):
        if self.env.context.get('pool_forcer_envoi'):
            return
        for po in self.filtered(lambda p: p.is_dropship_order and p.dropship_sale_id):
            if not po.pool_client_paye:
                raise UserError(_(
                    "La commande client %(so)s n'est pas payée (%(txt)s).\n\n"
                    "Enregistrez le paiement, ou utilisez « Envoyer quand même » si vous "
                    "acceptez d'avancer la marchandise.", so=po.dropship_sale_id.name,
                    txt=po.pool_paiement_txt))

    def action_send_dropship_email(self):
        self._pool_verifier_paiement()
        return super().action_send_dropship_email()

    def action_rfq_send(self):
        self._pool_verifier_paiement()
        return super().action_rfq_send()

    def action_pool_envoyer_quand_meme(self):
        self.ensure_one()
        self.message_post(body=_("⚠ Envoi au fournisseur forcé alors que le client n'a pas payé (%s).")
                          % (self.pool_paiement_txt or ''))
        return self.with_context(pool_forcer_envoi=True).action_send_dropship_email()

    # ── e-mail au fournisseur : PDF joint, adresses de commande ───────────
    def _pool_emails_commande(self):
        self.ensure_one()
        infos = self.order_line.mapped('sale_line_id.dropship_supplier_info_id')
        emails = [e for e in infos.mapped('order_email') if e]
        return emails[0] if emails else (self.partner_id.dropship_order_email or self.partner_id.email)

    def _send_via_email(self):
        self.ensure_one()
        template = self.env.ref('lolirine_pool_dropship.email_template_dropship_po', raise_if_not_found=False)
        if not template:
            return super()._send_via_email()
        email_to = self._pool_emails_commande()
        rapport = self.env.ref('lolirine_pool_dropship.action_report_dropship_purchase_order',
                               raise_if_not_found=False)
        valeurs = {'email_to': email_to}
        if rapport:
            import base64
            pdf, _t = self.env['ir.actions.report'].sudo()._render_qweb_pdf(rapport, self.ids)
            piece = self.env['ir.attachment'].sudo().create({
                'name': 'Bon de commande %s.pdf' % self.name, 'datas': base64.b64encode(pdf),
                'mimetype': 'application/pdf', 'res_model': 'purchase.order', 'res_id': self.id})
            valeurs['attachment_ids'] = [(4, piece.id)]
        template.send_mail(self.id, force_send=True, email_values=valeurs)
        self.message_post(body=_("📧 Bon envoyé par e-mail à %s (PDF joint)") % email_to)

    # ── suivi : e-mail au client ──────────────────────────────────────────
    def write(self, vals):
        a_expedier = self.browse()
        if vals.get('dropship_tracking_number') and not self.env.context.get('pool_sans_auto'):
            a_expedier = self.filtered(lambda p: p.is_dropship_order
                                       and p.dropship_status in ('draft', 'sent', 'confirmed'))
        res = super().write(vals)
        for po in a_expedier:
            po.with_context(pool_sans_auto=True).action_mark_shipped()
        return res

    def _notify_customer_shipment(self):
        """E-mail d'expédition au client, dans sa langue, avec le lien de suivi."""
        self.ensure_one()
        so = self.dropship_sale_id
        if not so or not so.partner_id.email:
            return
        client = so.partner_id
        lg = _langue(client)
        lien = lien_suivi(self.dropship_carrier, self.dropship_tracking_number, lg)
        adresse = so.partner_shipping_id
        corps = Markup('<p>%s</p><p>%s</p>') % (
            _tr(lg, 'Bonjour %s,', 'Beste %s,', 'Hello %s,') % client.name,
            _tr(lg, 'Bonne nouvelle : votre commande %s vient d\'être expédiée.',
                'Goed nieuws: uw bestelling %s is zonet verzonden.',
                'Good news: your order %s has just been shipped.') % (so.dropship_ref or so.name))
        details = []
        if self.dropship_carrier:
            details.append(Markup('<strong>%s</strong> %s') % (_tr(lg, 'Transporteur :', 'Vervoerder:', 'Carrier:'),
                                                              self.dropship_carrier))
        if self.dropship_tracking_number:
            numero = Markup('<a href="%s">%s</a>') % (lien, self.dropship_tracking_number) if lien \
                else escape(self.dropship_tracking_number)
            details.append(Markup('<strong>%s</strong> %s') % (_tr(lg, 'N° de suivi :', 'Trackingnummer:',
                                                                   'Tracking number:'), numero))
        if self.dropship_expected_delivery:
            details.append(Markup('<strong>%s</strong> %s') % (
                _tr(lg, 'Livraison prévue :', 'Verwachte levering:', 'Expected delivery:'),
                self.dropship_expected_delivery.strftime('%d/%m/%Y')))
        if adresse:
            details.append(Markup('<strong>%s</strong> %s, %s %s %s') % (
                _tr(lg, 'Adresse de livraison :', 'Leveringsadres:', 'Delivery address:'),
                adresse.name or '', adresse.street or '', adresse.zip or '', adresse.city or ''))
        corps += Markup('<p>%s</p>') % Markup('<br/>').join(details)
        if lien:
            corps += Markup('<p><a href="%s" style="background:#0078D4;color:#fff;padding:10px 18px;'
                            'border-radius:6px;text-decoration:none;display:inline-block;">%s</a></p>') % (
                lien, _tr(lg, 'Suivre mon colis', 'Mijn pakket volgen', 'Track my parcel'))
        corps += Markup('<p>%s<br/>%s</p>') % (
            _tr(lg, 'Merci pour votre confiance,', 'Bedankt voor uw vertrouwen,', 'Thank you for your trust,'),
            "L'équipe Lolirine Pool Store")
        so.message_post(
            body=corps, partner_ids=[client.id], email_from=EXPEDITEUR,
            subject=_tr(lg, 'Votre commande %s est expédiée', 'Uw bestelling %s is verzonden',
                        'Your order %s has been shipped') % (so.dropship_ref or so.name),
            message_type='comment', subtype_xmlid='mail.mt_comment')

    def action_mark_delivered(self):
        res = super().action_mark_delivered()
        for po in self:
            so = po.dropship_sale_id
            if not so or not so.partner_id.email:
                continue
            if any(b.dropship_status != 'delivered' for b in so._pool_bons()):
                continue  # d'autres colis sont encore en route
            client = so.partner_id
            lg = _langue(client)
            corps = Markup('<p>%s</p><p>%s</p><p>%s<br/>%s</p>') % (
                _tr(lg, 'Bonjour %s,', 'Beste %s,', 'Hello %s,') % client.name,
                _tr(lg, 'Votre commande %s a été livrée. Une question ? Répondez simplement à cet e-mail '
                        'ou appelez-nous au +32 (0)497 44 41 46.',
                    'Uw bestelling %s is geleverd. Een vraag? Antwoord gewoon op deze e-mail '
                    'of bel ons op +32 (0)497 44 41 46.',
                    'Your order %s has been delivered. Any question? Simply reply to this e-mail '
                    'or call us on +32 (0)497 44 41 46.') % (so.dropship_ref or so.name),
                _tr(lg, 'Merci pour votre confiance,', 'Bedankt voor uw vertrouwen,', 'Thank you for your trust,'),
                "L'équipe Lolirine Pool Store")
            so.message_post(
                body=corps, partner_ids=[client.id], email_from=EXPEDITEUR,
                subject=_tr(lg, 'Votre commande %s est livrée', 'Uw bestelling %s is geleverd',
                            'Your order %s has been delivered') % (so.dropship_ref or so.name),
                message_type='comment', subtype_xmlid='mail.mt_comment')
        return res

    # ── bons en retard : récapitulatif quotidien OdooBot ──────────────────
    @api.model
    def _cron_pool_bons_en_retard(self, utilisateur_id=2):
        bons = self.search([('is_dropship_order', '=', True), ('state', '!=', 'cancel'),
                            ('dropship_status', 'in', ('draft', 'sent', 'confirmed', 'shipped'))])
        retard = bons.filtered('pool_en_retard')
        if not retard:
            return
        user = self.env['res.users'].sudo().browse(utilisateur_id).exists()
        if not user:
            return
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        lignes = Markup('').join(
            Markup('<li><a href="%s/odoo/purchase/%d">%s</a> — %s — %s (%s)</li>') % (
                base, po.id, po.name, po.partner_id.name, po.pool_retard_txt,
                po.dropship_sale_id.name or '-') for po in retard)
        corps = Markup('<p>⏰ <strong>%s</strong></p><ul>%s</ul>') % (
            _('%d bon(s) fournisseur en retard') % len(retard), lignes)
        try:
            canal = self.env['discuss.channel'].with_user(self.env.ref('base.user_root')) \
                .sudo()._get_or_create_chat([user.partner_id.id])
            canal.sudo().message_post(body=corps, author_id=self.env.ref('base.partner_root').id,
                                      message_type='comment', subtype_xmlid='mail.mt_comment')
        except Exception:  # noqa: BLE001
            _logger.exception("Récapitulatif des bons en retard non posté")


class AccountMove(models.Model):
    _inherit = 'account.move'

    pool_ecart_bc = fields.Html('Écarts avec le bon de commande', compute='_compute_pool_ecart_bc',
                                sanitize=False)

    @api.depends('invoice_line_ids.price_unit', 'invoice_line_ids.discount', 'invoice_line_ids.quantity',
                 'invoice_line_ids.purchase_line_id')
    def _compute_pool_ecart_bc(self):
        for move in self:
            ecarts = []
            if move.move_type in ('in_invoice', 'in_refund'):
                for l in move.invoice_line_ids.filtered('purchase_line_id'):
                    pl = l.purchase_line_id
                    if not pl.order_id.is_dropship_order:
                        continue
                    net_f = l.price_unit * (1 - (l.discount or 0.0) / 100.0)
                    net_b = pl.price_unit * (1 - (pl.discount or 0.0) / 100.0)
                    if abs(net_f - net_b) > 0.005:
                        ecarts.append(Markup('<li><strong>%s</strong> : %s → %s (%s)</li>') % (
                            pl.supplier_product_ref or pl.product_id.default_code or pl.name[:40],
                            _('net facturé %s') % _eur(net_f), _('bon %s') % _eur(net_b),
                            _eur(net_f - net_b)))
                    if abs(l.quantity - pl.product_qty) > 0.001:
                        ecarts.append(Markup('<li><strong>%s</strong> : %s</li>') % (
                            pl.supplier_product_ref or pl.name[:40],
                            _('quantité facturée %g, commandée %g') % (l.quantity, pl.product_qty)))
            move.pool_ecart_bc = (Markup('<ul class="mb-0">%s</ul>') % Markup('').join(ecarts)) if ecarts else False

    def action_post(self):
        res = super().action_post()
        for move in self.filtered(lambda m: m.move_type in ('in_invoice', 'in_refund')):
            bons = move.invoice_line_ids.mapped('purchase_line_id.order_id').filtered('is_dropship_order')
            for po in bons:
                po.invalidate_recordset(['pool_facture_etat', 'pool_facture_ecart'])
                if po.pool_facture_etat == 'conforme':
                    po.message_post(body=_("✅ Facture fournisseur %s conforme au bon.") % move.name)
                elif po.pool_facture_etat == 'ecart':
                    po.message_post(body=_("⚠ Facture fournisseur %s : écart de %s avec le bon.")
                                    % (move.name, _eur(po.pool_facture_ecart)))
        return res
