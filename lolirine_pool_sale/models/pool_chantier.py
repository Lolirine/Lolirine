# -*- coding: utf-8 -*-
"""Suivi des chantiers piscine : avenants, relances des devis, procès-verbal, dossier documents,
interventions d'entretien (hivernage, remise en route) et tableau de bord."""
import base64
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Conditions imprimées au bas des devis d'entretien (hivernage, remise en route).
# Modifiables sans toucher au code : paramètre système « lolirine_pool_sale.note_devis_entretien ».
NOTE_DEVIS_ENTRETIEN = (
    "<p>Merci pour votre confiance en Lolirine Pool Store.</p>"
    "<p>Ce devis est valable 30 jours. Pour confirmer l'intervention, renvoyez-nous ce devis signé par e-mail "
    "à info@lolirinepoolstore.be ou contactez-nous au +32 (0)497 44 41 46.</p>"
    "<p>Les prix sont indiqués hors TVA (21 %). Le forfait couvre les prestations décrites ci-dessus. "
    "Les produits de traitement, accessoires et pièces qui ne figurent pas au devis, ainsi que toute réparation "
    "jugée nécessaire sur place, ne sont réalisés et facturés qu'avec votre accord préalable.</p>"
    "<p>Merci de prévoir l'accès au bassin et au local technique, un point d'eau et une alimentation électrique. "
    "L'intervention peut être reportée si la météo ne permet pas de travailler dans de bonnes conditions.</p>"
    "<p>Paiement par virement à la réception de la facture, sur le compte mentionné au bas de ce document.</p>"
)

TYPES_ENTRETIEN = ('hivernage', 'remise_en_route', 'entretien')
RELANCE_APRES_JOURS = 7
RELANCE_AVANT_EXPIRATION = 3


class SaleOrderLineChantier(models.Model):
    _inherit = 'sale.order.line'

    def _timesheet_service_generation(self):
        """Pas de projet « chantier » pour un entretien : une tâche est créée dans « Entretiens piscine »."""
        entretien = self.filtered(lambda l: l.order_id.is_chantier
                                  and l.order_id.pool_intervention_type in TYPES_ENTRETIEN)
        return super(SaleOrderLineChantier, self - entretien)._timesheet_service_generation()


class SaleOrderChantier(models.Model):
    _inherit = 'sale.order'

    # ── Avenants ─────────────────────────────────────────────────────
    pool_avenant_parent_id = fields.Many2one('sale.order', string="Avenant du chantier", copy=False, index=True,
                                             readonly=True)
    pool_avenant_ids = fields.One2many('sale.order', 'pool_avenant_parent_id', string="Avenants")
    pool_avenant_count = fields.Integer("Nombre d'avenants", compute='_compute_pool_avenants')
    pool_avenants_total = fields.Monetary("Avenants signés (HT)", compute='_compute_pool_avenants')

    # ── Relances ─────────────────────────────────────────────────────
    pool_envoye_le = fields.Date("Devis envoyé le", copy=False)
    pool_relance_nb = fields.Integer("Relances envoyées", copy=False, default=0)
    pool_relance_le = fields.Date("Dernière relance", copy=False)
    pool_sans_relance = fields.Boolean("Ne pas relancer", copy=False)

    # ── Procès-verbal ────────────────────────────────────────────────
    pool_pv_ids = fields.One2many('lolirine.pool.pv', 'order_id', string="Procès-verbaux")
    pool_pv_signe = fields.Boolean("PV signé", compute='_compute_pool_pv', store=True)

    # ── Tableau de bord ──────────────────────────────────────────────
    pool_heures = fields.Float("Heures pointées", compute='_compute_pool_tableau')
    pool_cout_mo_reel = fields.Monetary("Coût main-d'œuvre réel", compute='_compute_pool_tableau')
    pool_resultat_mo = fields.Monetary("Résultat main-d'œuvre", compute='_compute_pool_tableau',
                                       help="Main-d'œuvre vendue HT − heures pointées × coût horaire.")
    pool_reste_a_facturer = fields.Monetary("Reste à facturer", compute='_compute_pool_tableau')

    @api.depends('pool_avenant_ids.state', 'pool_avenant_ids.amount_untaxed')
    def _compute_pool_avenants(self):
        for o in self:
            o.pool_avenant_count = len(o.pool_avenant_ids)
            o.pool_avenants_total = sum(o.pool_avenant_ids.filtered(lambda a: a.state == 'sale').mapped('amount_untaxed'))

    @api.depends('pool_pv_ids.state')
    def _compute_pool_pv(self):
        for o in self:
            o.pool_pv_signe = any(pv.state == 'signe' for pv in o.pool_pv_ids)

    def _pool_projet(self):
        self.ensure_one()
        if self.pool_avenant_parent_id:
            return self.pool_avenant_parent_id._pool_projet()
        return self.sudo().project_ids[:1] or self.sudo().project_id

    def _compute_pool_tableau(self):
        Ligne = self.env['account.analytic.line'].sudo()
        for o in self:
            projet = o._pool_projet() if o.id else False
            heures = cout = 0.0
            if projet and 'project_id' in Ligne._fields:
                pointages = Ligne.search([('project_id', '=', projet.id)])
                heures = sum(pointages.mapped('unit_amount'))
                cout = -sum(pointages.mapped('amount'))
            o.pool_heures = heures
            o.pool_cout_mo_reel = cout
            o.pool_resultat_mo = o.pool_mo_ht - cout
            o.pool_reste_a_facturer = o.amount_to_invoice if o.state == 'sale' else 0.0

    # ─────────────────────────────────────────────────────────────────
    #  Avenants
    # ─────────────────────────────────────────────────────────────────
    def action_pool_creer_avenant(self):
        self.ensure_one()
        if self.state != 'sale':
            raise UserError(_("Un avenant se crée sur un chantier confirmé."))
        parent = self.pool_avenant_parent_id or self
        numero = len(parent.pool_avenant_ids) + 1
        avenant = self.create({
            'partner_id': parent.partner_id.id,
            'partner_invoice_id': parent.partner_invoice_id.id,
            'partner_shipping_id': parent.partner_shipping_id.id,
            'is_pool_quote': parent.is_pool_quote,
            'chantier_domaine': parent.chantier_domaine,
            'pool_avenant_parent_id': parent.id,
            'pool_intervention_type': parent.pool_intervention_type,
            'pool_adresse_chantier': parent.pool_adresse_chantier,
            'pool_technicien': parent.pool_technicien,
            'pool_autoliquidation': parent.pool_autoliquidation,
            'client_order_ref': parent.client_order_ref,
            'require_signature': True,
            'require_payment': parent.require_payment,
            'note': parent.note,
            'order_line': [(0, 0, {
                'display_type': 'line_section',
                'name': _("Avenant n° %(n)s au devis %(devis)s — travaux supplémentaires", n=numero, devis=parent.name),
            })],
        })
        avenant.name = "%s-A%s" % (parent.name, numero)
        parent.message_post(body=_("Avenant %s créé.") % avenant.name)
        return {'type': 'ir.actions.act_window', 'res_model': 'sale.order', 'res_id': avenant.id,
                'view_mode': 'form', 'target': 'current'}

    def action_pool_voir_avenants(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'sale.order', 'name': _("Avenants — %s") % self.name,
                'view_mode': 'list,form', 'domain': [('pool_avenant_parent_id', '=', self.id)],
                'context': {'create': False}}

    # ─────────────────────────────────────────────────────────────────
    #  Procès-verbal de réception
    # ─────────────────────────────────────────────────────────────────
    def action_pool_pv(self):
        self.ensure_one()
        if self.state != 'sale':
            raise UserError(_("Le procès-verbal se fait sur un chantier confirmé."))
        pv = self.pool_pv_ids.filtered(lambda p: p.state == 'draft')[:1] or \
            self.env['lolirine.pool.pv'].create({'order_id': self.id})
        return {'type': 'ir.actions.act_window', 'res_model': 'lolirine.pool.pv', 'res_id': pv.id,
                'view_mode': 'form', 'target': 'current'}

    # ─────────────────────────────────────────────────────────────────
    #  Confirmation : avenant rattaché au chantier, tâche d'entretien, dossier documents
    # ─────────────────────────────────────────────────────────────────
    def _action_confirm(self):
        for o in self.filtered('pool_avenant_parent_id'):
            projet = o.pool_avenant_parent_id._pool_projet()
            if projet:
                if projet.allow_billable and not o.project_id:
                    o.project_id = projet
                for l in o.order_line.filtered(lambda x: not x.display_type and not x.project_id
                                               and x.product_id.service_tracking in ('project_only', 'task_in_project')):
                    l.project_id = projet
        res = super()._action_confirm()
        for o in self.filtered(lambda x: x.is_chantier):
            try:
                if o.pool_intervention_type in TYPES_ENTRETIEN:
                    o._pool_creer_tache_entretien()
                else:
                    o._pool_classer_devis_et_photos()
            except Exception as e:
                _logger.warning("Suivi du chantier %s non préparé : %s", o.name, e)
        return res

    def _pool_creer_tache_entretien(self):
        self.ensure_one()
        projet = self.env.ref('lolirine_pool_sale.project_entretiens_piscine', raise_if_not_found=False)
        if not projet:
            return
        libelle = dict(self._fields['pool_intervention_type'].selection).get(self.pool_intervention_type, '')
        mo = self.order_line.filtered(lambda l: l._pool_ligne_mo())[:1]
        vals = {
            'name': "%s — %s" % (libelle.split(' ', 1)[-1], self.partner_id.name),
            'project_id': projet.id,
            'partner_id': self.partner_id.id,
            'description': "<p>%s</p><p>%s</p>" % (self.name, self.pool_adresse_chantier or self.partner_shipping_id.contact_address or ''),
        }
        if self.commitment_date:
            vals['date_deadline'] = self.commitment_date
        if mo and 'sale_line_id' in self.env['project.task']._fields:
            vals['sale_line_id'] = mo.id
        self.env['project.task'].sudo().create(vals)

    def _pool_dossier_documents(self):
        """Dossier « Documents » du projet du chantier (application Documents), s'il existe."""
        self.ensure_one()
        projet = self._pool_projet()
        if not projet or 'documents_folder_id' not in projet._fields:
            return False
        return projet.sudo().documents_folder_id

    def _pool_classer_documents(self, attachments):
        self.ensure_one()
        dossier = self._pool_dossier_documents()
        if not dossier or 'documents.document' not in self.env:
            return
        Document = self.env['documents.document'].sudo()
        for att in attachments:
            try:
                Document.create({'attachment_id': att.copy({'res_model': False, 'res_id': False}).id,
                                 'folder_id': dossier.id, 'name': att.name})
            except Exception as e:
                _logger.warning("Document %s non classé pour %s : %s", att.name, self.name, e)

    def _pool_classer_devis_et_photos(self):
        self.ensure_one()
        if not self._pool_dossier_documents():
            return
        pieces = self.pool_vt_photo_ids
        try:
            pdf, _type = self.env['ir.actions.report']._render_qweb_pdf(
                'lolirine_pool_dropship.action_report_pool_devis', self.ids)
            pieces |= self.env['ir.attachment'].create({
                'name': "Devis signé %s.pdf" % self.name.replace('/', '_'),
                'datas': base64.b64encode(pdf), 'mimetype': 'application/pdf',
                'res_model': 'sale.order', 'res_id': self.id,
            })
        except Exception as e:
            _logger.warning("PDF du devis %s non généré : %s", self.name, e)
        self._pool_classer_documents(pieces)

    # ─────────────────────────────────────────────────────────────────
    #  Relances automatiques des devis non signés
    # ─────────────────────────────────────────────────────────────────
    def write(self, vals):
        if vals.get('state') == 'sent':
            for o in self.filtered(lambda x: x.is_chantier and not x.pool_envoye_le):
                o.pool_envoye_le = fields.Date.context_today(o)
        return super().write(vals)

    @api.model
    def _cron_pool_relances(self):
        modele = self.env.ref('lolirine_pool_sale.mail_template_pool_relance', raise_if_not_found=False)
        if not modele:
            return
        today = fields.Date.context_today(self)
        devis = self.search([('is_chantier', '=', True), ('state', '=', 'sent'), ('pool_sans_relance', '=', False),
                             ('pool_envoye_le', '!=', False), ('pool_relance_nb', '<', 2)])
        for o in devis:
            if o.signature:
                continue
            premiere = o.pool_relance_nb == 0 and today >= o.pool_envoye_le + timedelta(days=RELANCE_APRES_JOURS)
            avant_fin = (o.validity_date and today <= o.validity_date
                         and today >= o.validity_date - timedelta(days=RELANCE_AVANT_EXPIRATION)
                         and (not o.pool_relance_le or o.pool_relance_le < today - timedelta(days=1)))
            if o.validity_date and today > o.validity_date:
                continue
            if not (premiere or avant_fin):
                continue
            try:
                o.message_post_with_source(modele, message_type='comment', subtype_xmlid='mail.mt_comment')
                o.write({'pool_relance_nb': o.pool_relance_nb + 1, 'pool_relance_le': today})
            except Exception as e:
                _logger.warning("Relance du devis %s impossible : %s", o.name, e)

    # ─────────────────────────────────────────────────────────────────
    #  Devis d'entretien : hivernage, remise en route
    # ─────────────────────────────────────────────────────────────────
    @api.model
    def _pool_formule_defaut(self, type_intervention):
        xmlid = {'hivernage': 'lolirine_pool_sale.prestation_hivernage',
                 'remise_en_route': 'lolirine_pool_sale.prestation_mise_en_route'}.get(type_intervention)
        return self.env.ref(xmlid, raise_if_not_found=False) if xmlid else self.env['lolirine.pool.prestation']

    # ─────────────────────────────────────────────────────────────────
    #  Frais de déplacement : distance depuis Boninne (module « Trajets kilomètres »)
    # ─────────────────────────────────────────────────────────────────
    def _pool_distance_depuis_boninne(self):
        """Distance aller (km) entre le lieu de départ par défaut des trajets kilomètres
        (siège, Boninne) et l'adresse du chantier. 0.0 si le calcul est impossible."""
        self.ensure_one()
        if 'km.distance.calculator' not in self.env or 'km.lieu.depart' not in self.env:
            return 0.0
        Depart = self.env['km.lieu.depart'].sudo()
        depart = Depart.search([('is_default', '=', True)], limit=1) or Depart.search([], limit=1)
        livraison = self.partner_shipping_id or self.partner_id
        destination = self.pool_adresse_chantier or self.partner_id.pool_adresse_piscine or ", ".join(
            x for x in (livraison.street, " ".join(filter(None, [livraison.zip, livraison.city]))) if x)
        if not depart or not destination:
            return 0.0
        if 'belg' not in destination.lower():
            destination = "%s, Belgique" % destination
        return self.env['km.distance.calculator'].sudo().calculate_distance(depart.adresse_complete, destination) or 0.0

    def action_pool_calculer_deplacement(self):
        """Calcule la distance depuis Boninne et ajoute (ou met à jour) la ligne de frais de déplacement.
        Tarif : paramètre « lolirine_pool_sale.deplacement_taux_km » (€ HTVA par km aller, défaut 1,00)."""
        params = self.env['ir.config_parameter'].sudo()
        taux = float(params.get_param('lolirine_pool_sale.deplacement_taux_km', '1.0') or 0.0)
        Product = self.env['product.product']
        article = Product.browse(int(params.get_param('lolirine_pool_sale.deplacement_product_id', '0') or 0)).exists() \
            or Product.search([('default_code', '=', 'DEPL')], order='id desc', limit=1)
        for order in self:
            if order.state not in ('draft', 'sent'):
                raise UserError(_("Les frais de déplacement ne se recalculent que sur un devis."))
            km = order._pool_distance_depuis_boninne()
            if not km:
                raise UserError(_("Distance non calculée : vérifiez l'adresse du chantier et la clé de calcul "
                                  "des trajets kilomètres."))
            if not article:
                raise UserError(_("Article de frais de déplacement (référence DEPL) introuvable."))
            km_arrondi = int(round(km))
            montant = order.currency_id.round(km_arrondi * taux)
            livraison = order.partner_shipping_id or order.partner_id
            ville = livraison.city or order.partner_id.city or ''
            libelle = _("Frais de déplacement Boninne – %(ville)s (± %(km)s km), par déplacement") % {
                'ville': ville or _("chantier"), 'km': km_arrondi}
            lignes = order.order_line.filtered(
                lambda l: not l.display_type and (l.product_id.default_code or '').upper().startswith('DEPL'))
            if lignes:
                lignes[0].write({'name': libelle, 'price_unit': montant})
            else:
                mo = order.order_line.filtered(lambda l: l._pool_ligne_mo())
                sequence = (max(mo.mapped('sequence')) + 1) if mo else 15
                ligne = self.env['sale.order.line'].create({
                    'order_id': order.id, 'product_id': article.id, 'name': libelle,
                    'product_uom_qty': 1, 'sequence': sequence})
                ligne.write({'name': libelle, 'price_unit': montant})
            order.write({'pool_km': km_arrondi, 'pool_frais_deplacement': montant})
        return True

    @api.model
    def _pool_creer_devis_entretien(self, partner, type_intervention, prestation=False, adresse=False,
                                    date_souhaitee=False, avec_options=True, note_interne=False):
        """Crée un devis piscine d'hivernage / de remise en route avec l'ouvrage choisi."""
        if not prestation:
            prestation = partner.pool_formule_hivernage_id if type_intervention == 'hivernage' \
                else partner.pool_formule_remise_id
        prestation = prestation or self._pool_formule_defaut(type_intervention)
        if not prestation:
            raise UserError(_("Aucune formule (prestation) trouvée pour ce type d'intervention."))
        vals = {
            'partner_id': partner.id,
            'is_pool_quote': True,
            'pool_intervention_type': type_intervention,
            'pool_adresse_chantier': adresse or partner.pool_adresse_piscine or partner.contact_address,
            'require_signature': True,
            # entretien : la signature suffit à confirmer, paiement à la réception de la facture
            'require_payment': False,
            'note': self.env['ir.config_parameter'].sudo().get_param(
                'lolirine_pool_sale.note_devis_entretien') or NOTE_DEVIS_ENTRETIEN,
        }
        if date_souhaitee:
            vals['commitment_date'] = date_souhaitee
        order = self.create(vals)
        assistant = self.env['lolirine.pool.prestation.wizard'].create({
            'order_id': order.id, 'prestation_id': prestation.id, 'titre': prestation.name,
            'description_client': prestation.description_client, 'detail_interne': prestation.detail_interne,
            'mode_prix': prestation.mode_prix, 'forfait_fixe': prestation.forfait_fixe, 'heures': prestation.heures,
            'taux_horaire': prestation.taux_horaire, 'coef_difficulte': prestation.coef_difficulte or 1.0,
            'avec_fournitures': True, 'avec_options': avec_options,
        })
        assistant.action_ajouter()
        # frais de déplacement depuis Boninne (sans bloquer la création du devis si le calcul échoue)
        try:
            order.action_pool_calculer_deplacement()
        except Exception as e:
            _logger.info("Devis %s : frais de déplacement non calculés (%s)", order.name, e)
        parc = partner.pool_equipement_ids
        if parc:
            order.pool_vt_equipements = "\n".join(
                "%s%s%s" % (e.name, (" — " + e.marque) if e.marque else "",
                            (" (n° %s)" % e.numero_serie) if e.numero_serie else "") for e in parc)
        if note_interne:
            order.message_post(body=note_interne)
        return order

    @api.model
    def _cron_pool_campagne_saisonniere(self, forcer=None):
        """1er septembre : devis d'hivernage ; 1er mars : devis de remise en route — en brouillon,
        pour chaque client « Entretien saisonnier », sans doublon sur 120 jours."""
        today = fields.Date.context_today(self)
        type_intervention = forcer or {(9, 1): 'hivernage', (3, 1): 'remise_en_route'}.get((today.month, today.day))
        if not type_intervention:
            return self.browse()
        clients = self.env['res.partner'].search([('pool_entretien_auto', '=', True)])
        crees = self.browse()
        for client in clients:
            deja = self.search_count([('partner_id', '=', client.id), ('pool_intervention_type', '=', type_intervention),
                                      ('create_date', '>=', fields.Datetime.now() - timedelta(days=120))])
            if deja:
                continue
            try:
                crees |= self._pool_creer_devis_entretien(client, type_intervention)
            except Exception as e:
                _logger.warning("Campagne %s : devis non créé pour %s : %s", type_intervention, client.name, e)
        if crees:
            libelle = "d'hivernage" if type_intervention == 'hivernage' else "de remise en route"
            crees[0].activity_schedule(
                'mail.mail_activity_data_todo', user_id=crees[0].user_id.id or self.env.ref('base.user_admin').id,
                summary=_("Campagne %s : %s devis à vérifier et envoyer") % (libelle, len(crees)),
                note=_("Devis créés : %s") % ", ".join(crees.mapped('name')))
        return crees
