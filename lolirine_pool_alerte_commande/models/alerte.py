"""Avertissement du gérant quand un client paie une commande du Pool Store.

* À la confirmation d'une commande du site 6 (sur le site, une commande est
  confirmée quand le paiement est accepté), un avertissement est mis en file.
* La tâche planifiée (toutes les 10 min, et tout de suite après le paiement)
  envoie :
    - un message d'OdooBot + une activité « Envoyer les bons fournisseurs » ;
    - un e-mail avec le détail par fournisseur et un PDF par bon de commande
      fournisseur (les articles d'un même fournisseur sont sur le même bon) ;
    - un WhatsApp de résumé via CallMeBot, seulement entre l'heure de début
      et l'heure de fin (8 h – 20 h par défaut, heure de Bruxelles) ; en
      dehors, il attend le lendemain matin.

Paramètres système (préfixe lolirine_pool_alerte_commande.) :
    email          destinataire(s) de l'e-mail (défaut : info@lolirinepoolstore.be)
    utilisateur    id de l'utilisateur prévenu par OdooBot (défaut : 2)
    callmebot_tel  numéro WhatsApp au format +32…
    callmebot_cle  clé fournie par CallMeBot
    heure_debut / heure_fin   plage d'envoi WhatsApp (défaut 8 et 20)
"""
import base64
import logging
from datetime import datetime

import pytz
import requests
from markupsafe import Markup, escape

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

P = 'lolirine_pool_alerte_commande.'
SITE_POOL_STORE = 6
RAPPORT_BC = 'lolirine_pool_dropship.report_dropship_purchase_order_document'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        Alerte = self.env['lolirine.alerte.commande'].sudo()
        nouvelles = False
        for order in self:
            if order.website_id.id == SITE_POOL_STORE and not Alerte.search_count([('order_id', '=', order.id)]):
                Alerte.create({'order_id': order.id})
                nouvelles = True
        if nouvelles:
            cron = self.env.ref('lolirine_pool_alerte_commande.cron_alerte_commande', raise_if_not_found=False)
            if cron:
                cron.sudo()._trigger()
        return res


class LolirineAlerteCommande(models.Model):
    _name = 'lolirine.alerte.commande'
    _description = 'Avertissement de commande payée (Pool Store)'
    _order = 'id desc'

    order_id = fields.Many2one('sale.order', 'Commande', required=True, ondelete='cascade', index=True)
    state = fields.Selection([('a_envoyer', 'À envoyer'), ('envoye', 'Envoyé'), ('erreur', 'Erreur')],
                             'E-mail et OdooBot', default='a_envoyer', index=True)
    whatsapp_state = fields.Selection([('attente', 'En attente'), ('envoye', 'Envoyé'),
                                       ('non_configure', 'Non configuré'), ('erreur', 'Erreur')],
                                      'WhatsApp', default='attente', index=True)
    date_envoi = fields.Datetime('Envoyé le')
    whatsapp_date = fields.Datetime('WhatsApp envoyé le')
    note = fields.Text()

    # ── paramètres ────────────────────────────────────────────────────────
    @api.model
    def _param(self, cle, defaut=''):
        return self.env['ir.config_parameter'].sudo().get_param(P + cle) or defaut

    @api.model
    def _dans_les_heures(self):
        maintenant = datetime.now(pytz.timezone('Europe/Brussels'))
        debut = int(self._param('heure_debut', '8'))
        fin = int(self._param('heure_fin', '20'))
        return debut <= maintenant.hour < fin

    # ── contenu ───────────────────────────────────────────────────────────
    def _bons_fournisseurs(self):
        return self.env['purchase.order'].sudo().search([('dropship_sale_id', '=', self.order_id.id)])

    def _lignes_sans_fournisseur(self):
        res = self.env['sale.order.line']
        for ligne in self.order_id.order_line:
            if ligne.display_type or not ligne.product_id or ligne.product_id.type == 'service':
                continue
            if 'is_delivery' in ligne._fields and ligne.is_delivery:
                continue
            if 'dropship_supplier_id' in ligne._fields and not ligne.dropship_supplier_id:
                res |= ligne
        return res

    def _lien(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        return '%s/odoo/sales/%s' % (base, self.order_id.id)

    def _montant(self):
        o = self.order_id
        return '%s %s' % (('{:,.2f}'.format(o.amount_total)).replace(',', ' ').replace('.', ','),
                          o.currency_id.symbol or '€')

    def _texte_whatsapp(self):
        o = self.order_id
        lignes = ['🛒 Commande payée %s — %s' % (o.name, self._montant()),
                  '%s · %s' % (o.partner_id.name or '', o.partner_shipping_id.city or '')]
        for po in self._bons_fournisseurs():
            lignes.append('📦 %s : bon %s (%d art.)' % (po.partner_id.name, po.name, len(po.order_line)))
        sans = self._lignes_sans_fournisseur()
        if sans:
            lignes.append('⚠ %d article(s) sans fournisseur : à attribuer' % len(sans))
        lignes.append(self._lien())
        return '\n'.join(lignes)

    def _html_email(self):
        o = self.order_id
        h = [Markup('<p>Le client <b>%s</b> a payé la commande <b>%s</b> (%s).</p>') % (
            o.partner_id.name or '', o.name, self._montant())]
        adr = o.partner_shipping_id
        h.append(Markup('<p>Livraison : %s, %s %s %s</p>') % (
            adr.name or '', adr.street or '', adr.zip or '', adr.city or ''))
        for po in self._bons_fournisseurs():
            h.append(Markup('<h3 style="margin:16px 0 4px">%s — bon %s (%s)</h3><ul>') % (
                po.partner_id.name, po.name, dict(po._fields['state'].selection).get(po.state, po.state)))
            for l in po.order_line:
                ref = l.supplier_product_ref if 'supplier_product_ref' in l._fields else ''
                h.append(Markup('<li>%s × %s%s</li>') % (
                    ('%g' % l.product_qty), l.name or l.product_id.display_name,
                    Markup(' <small>(réf. fournisseur %s)</small>') % ref if ref else ''))
            h.append(Markup('</ul>'))
        sans = self._lignes_sans_fournisseur()
        if sans:
            h.append(Markup('<p style="color:#b91c1c"><b>⚠ Articles sans fournisseur retenu</b> '
                            '(aucun bon créé pour eux) :</p><ul>'))
            for l in sans:
                h.append(Markup('<li style="color:#b91c1c">%s × %s</li>') % ('%g' % l.product_uom_qty,
                                                                          l.product_id.display_name))
            h.append(Markup('</ul>'))
        h.append(Markup('<p>Les bons fournisseurs sont en pièces jointes, en brouillon : vérifiez-les puis '
                        'envoyez-les depuis la commande.</p><p><a href="%s">Ouvrir la commande %s</a></p>') % (
            self._lien(), o.name))
        return Markup('').join(h)

    # ── envois ────────────────────────────────────────────────────────────
    def _envoyer_email_et_odoobot(self):
        self.ensure_one()
        o = self.order_id
        corps = self._html_email()
        # pièces jointes : un PDF par bon fournisseur
        pieces = []
        Rapport = self.env['ir.actions.report'].sudo()
        for po in self._bons_fournisseurs():
            try:
                pdf, _t = Rapport._render_qweb_pdf(RAPPORT_BC, po.ids)
                pieces.append(self.env['ir.attachment'].sudo().create({
                    'name': 'Bon fournisseur %s - %s.pdf' % (po.name, po.partner_id.name),
                    'datas': base64.b64encode(pdf), 'mimetype': 'application/pdf',
                    'res_model': 'purchase.order', 'res_id': po.id,
                }).id)
            except Exception:  # noqa: BLE001
                _logger.exception("Avertissement %s : PDF du bon %s non généré", o.name, po.name)
        destinataires = self._param('email', 'info@lolirinepoolstore.be')
        expediteur = self._param('expediteur', 'Lolirine Pool Store <info@lolirinepoolstore.be>')
        mail = self.env['mail.mail'].sudo().create({
            'subject': '🛒 Commande payée %s — %s — bons fournisseurs à envoyer' % (o.name, self._montant()),
            'body_html': corps,
            'email_to': destinataires,
            'email_from': expediteur,
            'attachment_ids': [(6, 0, pieces)],
            'auto_delete': False,
        })
        mail.send()

        # OdooBot + activité pour le gérant
        user = self.env['res.users'].sudo().browse(int(self._param('utilisateur', '2'))).exists()
        if user:
            try:
                odoobot = self.env.ref('base.partner_root')
                canal = self.env['discuss.channel'].with_user(self.env.ref('base.user_root')) \
                    .sudo()._get_or_create_chat([user.partner_id.id])
                canal.sudo().message_post(body=corps, author_id=odoobot.id, message_type='comment',
                                          subtype_xmlid='mail.mt_comment')
            except Exception:  # noqa: BLE001
                _logger.exception("Avertissement %s : message OdooBot non posté", o.name)
            o.sudo().activity_schedule(
                'mail.mail_activity_data_todo', user_id=user.id,
                summary='Envoyer les bons fournisseurs',
                note=Markup('Commande payée : vérifier et envoyer %d bon(s) fournisseur.') % len(
                    self._bons_fournisseurs()))

    def _envoyer_whatsapp(self):
        self.ensure_one()
        tel, cle = self._param('callmebot_tel'), self._param('callmebot_cle')
        if not tel or not cle:
            self.whatsapp_state = 'non_configure'
            return
        rep = requests.get('https://api.callmebot.com/whatsapp.php',
                           params={'phone': tel, 'text': self._texte_whatsapp(), 'apikey': cle}, timeout=30)
        if rep.status_code == 200 and 'error' not in rep.text.lower()[:200]:
            self.write({'whatsapp_state': 'envoye', 'whatsapp_date': fields.Datetime.now()})
        else:
            self.write({'whatsapp_state': 'erreur', 'note': ('WhatsApp %s : %s' % (rep.status_code, rep.text))[:1000]})

    @api.model
    def _cron_traiter(self):
        for a in self.search([('state', '=', 'a_envoyer')], limit=20):
            try:
                a._envoyer_email_et_odoobot()
                a.write({'state': 'envoye', 'date_envoi': fields.Datetime.now()})
            except Exception as e:  # noqa: BLE001
                self.env.cr.rollback()
                _logger.exception("Avertissement de la commande %s non envoyé", a.order_id.name)
                a.write({'state': 'erreur', 'note': str(e)[:1000]})
            self.env.cr.commit()
        if not self._dans_les_heures():
            return
        for a in self.search([('whatsapp_state', '=', 'attente')], limit=20):
            try:
                a._envoyer_whatsapp()
            except Exception as e:  # noqa: BLE001
                _logger.exception("WhatsApp de la commande %s non envoyé", a.order_id.name)
                a.write({'whatsapp_state': 'erreur', 'note': str(e)[:1000]})
            self.env.cr.commit()

    def action_renvoyer(self):
        """Bouton : renvoyer l'avertissement (e-mail, OdooBot, WhatsApp)."""
        self.write({'state': 'a_envoyer', 'whatsapp_state': 'attente', 'note': False})
        self._cron_traiter()
