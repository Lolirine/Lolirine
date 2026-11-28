# -*- coding: utf-8 -*-
"""Trajets kilométriques des interventions piscine.

Chaque entretien ou intervention sur place suppose deux déplacements :
la visite en vue du devis, puis l'intervention elle-même. Les deux trajets sont
créés en brouillon (activité « Piscine ») et restent à relire avant validation.
"""
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

TYPES_TRAJET = [('visite', "Visite en vue du devis"), ('intervention', "Intervention sur place")]


class KmTrajetPiscine(models.Model):
    _inherit = 'km.trajet'

    pool_order_id = fields.Many2one('sale.order', string="Devis / commande piscine", copy=False, index=True,
                                    ondelete='set null')
    pool_type_trajet = fields.Selection(TYPES_TRAJET, string="Déplacement piscine", copy=False)
    auto_source = fields.Selection(selection_add=[('piscine', "Intervention piscine")],
                                   ondelete={'piscine': 'set null'})

    @api.depends('pool_order_id')
    def _compute_activite(self):
        super()._compute_activite()
        for trajet in self:
            if trajet.pool_order_id:
                trajet.activite = 'piscine'


class SaleOrderTrajetsKm(models.Model):
    _inherit = 'sale.order'

    pool_trajet_km_ids = fields.One2many('km.trajet', 'pool_order_id', string="Trajets kilométriques")

    def _pool_creer_trajet_km(self, type_trajet, date_trajet=False):
        """Crée (une seule fois par devis et par type) le trajet aller-retour Boninne → chantier, en brouillon."""
        self.ensure_one()
        Trajet = self.env['km.trajet'].sudo()
        if not self.is_pool_quote or Trajet.search_count(
                [('pool_order_id', '=', self.id), ('pool_type_trajet', '=', type_trajet)]):
            return Trajet.browse()
        base = Trajet._km_auto_base_vals()
        if not base.get('employee_id'):
            _logger.warning("Trajet km piscine %s : aucun employé configuré", self.name)
            return Trajet.browse()
        km = float(self.pool_km or 0.0)
        if not km:
            try:
                km = self._pool_distance_depuis_boninne()
            except Exception as e:
                _logger.info("Trajet km piscine %s : distance non calculée (%s)", self.name, e)
        Lieu = self.env['km.lieu.depart'].sudo()
        depart = Lieu.search([('is_default', '=', True)], limit=1) or Lieu.search([], limit=1)
        livraison = self.partner_shipping_id or self.partner_id
        arrivee = self.pool_adresse_chantier or self.partner_id.pool_adresse_piscine or ", ".join(
            x for x in (livraison.street, " ".join(filter(None, [livraison.zip, livraison.city]))) if x)
        client = self.partner_id.commercial_partner_id
        if type_trajet == 'visite':
            code, motif = 'PROSPECT', _("Visite sur place en vue du devis %(devis)s – %(client)s") % {
                'devis': self.name, 'client': client.name}
            note = _("Créé automatiquement pour le devis %s. À refuser s'il n'y a pas eu de visite préalable ; "
                     "date à confirmer.") % self.name
        else:
            code, motif = 'CHANTIER', _("Intervention sur place – %(devis)s – %(client)s") % {
                'devis': self.name, 'client': client.name}
            note = _("Créé automatiquement à la clôture de l'intervention %s. À relire avant validation.") % self.name
        categorie = Trajet._km_categorie(code) or Trajet._km_categorie('CLIENT') or Trajet._km_categorie('AUTRE')
        vals = dict(base)
        vals.update({
            'date': date_trajet or fields.Date.context_today(self),
            'partner_id': client.id,
            'categorie_id': categorie.id or False,
            'origine_trajet': 'rdv_client',
            'motif': motif,
            'use_predefined': False,
            'lieu_depart': depart.adresse_complete or '',
            'lieu_arrivee': arrivee or (client.name or ''),
            'aller_retour': True,
            'distance_aller': km,
            'auto_source': 'piscine',
            'activite': 'piscine',
            'state': 'brouillon',
            'notes': note if km else "%s %s" % (note, _("Distance non calculée : à compléter.")),
            'pool_order_id': self.id,
            'pool_type_trajet': type_trajet,
        })
        trajet = Trajet.create(vals)
        self.message_post(body=_("Trajet kilométrique créé en brouillon : %(nom)s (%(type)s, %(km)s km aller).") % {
            'nom': trajet.name, 'type': dict(TYPES_TRAJET)[type_trajet].lower(), 'km': km})
        return trajet

    def action_pool_creer_trajets_km(self, types=None, date_intervention=False):
        """Crée les trajets manquants du devis (visite et intervention par défaut)."""
        trajets = self.env['km.trajet'].sudo()
        for order in self:
            for type_trajet in (types or ['visite', 'intervention']):
                if type_trajet == 'visite':
                    jour = order.pool_date_visite or fields.Date.to_date(order.date_order)
                else:
                    jour = fields.Date.to_date(date_intervention) if date_intervention else False
                    if not jour and order.commitment_date:
                        jour = fields.Date.context_today(order, order.commitment_date)
                trajets |= order._pool_creer_trajet_km(type_trajet, jour)
        return trajets.ids

    def write(self, vals):
        res = super().write(vals)
        if vals.get('pool_date_visite'):
            for order in self.filtered('is_pool_quote'):
                try:
                    existant = self.env['km.trajet'].sudo().search(
                        [('pool_order_id', '=', order.id), ('pool_type_trajet', '=', 'visite')], limit=1)
                    if existant and existant.state == 'brouillon':
                        existant.date = order.pool_date_visite
                    elif not existant:
                        order._pool_creer_trajet_km('visite', order.pool_date_visite)
                except Exception as e:
                    _logger.warning("Trajet km de visite %s non créé : %s", order.name, e)
        return res


class ProjectTaskTrajetsKm(models.Model):
    _inherit = 'project.task'

    def _pool_commande_piscine(self):
        self.ensure_one()
        order = self.sale_order_id if 'sale_order_id' in self._fields else self.env['sale.order']
        if not order and 'sale_line_id' in self._fields:
            order = self.sale_line_id.order_id
        return order if order and order.is_pool_quote else self.env['sale.order']

    def write(self, vals):
        avant = {t.id: t.state for t in self} if ('state' in vals or 'stage_id' in vals) else {}
        res = super().write(vals)
        if avant:
            for task in self:
                termine = task.state == '1_done' or (task.stage_id.fold and 'stage_id' in vals)
                if not termine or avant.get(task.id) == '1_done' and 'stage_id' not in vals:
                    continue
                order = task._pool_commande_piscine()
                if not order:
                    continue
                try:
                    today = fields.Date.context_today(task)
                    prevu = fields.Date.context_today(task, task.date_deadline) if task.date_deadline else today
                    jour = prevu if prevu <= today else today
                    # l'intervention, et la visite préalable si elle n'a pas encore son trajet
                    order._pool_creer_trajet_km('intervention', jour)
                    order._pool_creer_trajet_km(
                        'visite', order.pool_date_visite or fields.Date.to_date(order.date_order))
                except Exception as e:
                    _logger.warning("Trajets km de l'intervention %s non créés : %s", order.name, e)
        return res
