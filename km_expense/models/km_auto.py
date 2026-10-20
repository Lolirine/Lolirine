# -*- coding: utf-8 -*-
"""Creation automatique des trajets kilometriques.

* Nouveau client : a la confirmation de son premier contrat d'abonnement,
  deux allers-retours siege -> hangar (visite du box + signature du contrat).
* Fournisseur physique : a la validation de sa facture (voir account_move.py),
  un aller-retour par jour d'achat.
* Hangar : nettoyages (lundi et jeudi) et maintenance (1er samedi du mois),
  crees chaque jour par une action planifiee, jours feries belges exclus.

Tous les trajets sont crees en brouillon et doivent etre valides.
Reglages (Parametres techniques > Parametres systeme) :
    km_expense.auto_employee_id           employe du trajet
    km_expense.auto_vehicule_personnel_id vehicule personnel
    km_expense.auto_hangar_km             distance aller siege -> hangar (1.0)
    km_expense.auto_client_active         1 = trajets nouveaux clients actifs
    km_expense.auto_hangar_active         1 = nettoyages / maintenances actifs
    km_expense.auto_nettoyage_jours       jours de nettoyage (0 = lundi) : "0,3"
    km_expense.auto_maintenance_jour      jour de la maintenance mensuelle : "5"
    km_expense.auto_hangar_last_date      dernier jour traite par le cron
"""
import logging
from datetime import date, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

PARAM = 'km_expense.%s'

MOTIF_NETTOYAGE = 'Nettoyage du garde-meuble (hangar)'
MOTIF_MAINTENANCE = 'Maintenance mensuelle du garde-meuble (hangar)'


def _paques(annee):
    """Dimanche de Paques (algorithme de Meeus / Butcher)."""
    a, b, c = annee % 19, annee // 100, annee % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois = (h + l - 7 * m + 114) // 31
    jour = ((h + l - 7 * m + 114) % 31) + 1
    return date(annee, mois, jour)


def jours_feries_belges(annee):
    p = _paques(annee)
    return {
        date(annee, 1, 1), p + timedelta(days=1), date(annee, 5, 1),
        p + timedelta(days=39), p + timedelta(days=50), date(annee, 7, 21),
        date(annee, 8, 15), date(annee, 11, 1), date(annee, 11, 11), date(annee, 12, 25),
    }


class KmTrajetAuto(models.Model):
    _inherit = 'km.trajet'

    auto_source = fields.Selection([
        ('client', 'Client'),
        ('fournisseur', 'Facture fournisseur'),
        ('nettoyage', 'Nettoyage hangar'),
        ('maintenance', 'Maintenance hangar'),
    ], string='Création automatique', copy=False, index=True, readonly=True,
        help="Renseigné quand le trajet a été créé automatiquement par Odoo.")

    # ------------------------------------------------------------------
    # Reglages
    # ------------------------------------------------------------------
    @api.model
    def _km_param(self, key, default=False):
        return self.env['ir.config_parameter'].sudo().get_param(PARAM % key, default)

    @api.model
    def _km_auto_base_vals(self):
        """Employe et vehicule des trajets crees automatiquement."""
        Employee = self.env['hr.employee'].sudo()
        employee = Employee.browse(int(self._km_param('auto_employee_id', 0) or 0)).exists()
        if not employee:
            employee = self.env.user.employee_id or Employee.search(
                [('company_id', 'in', [False, self.env.company.id])], order='id', limit=1)
        Vehicule = self.env['km.vehicule.personnel'].sudo()
        vehicule = Vehicule.browse(int(self._km_param('auto_vehicule_personnel_id', 0) or 0)).exists()
        if not vehicule and employee:
            vehicule = Vehicule.search([('employee_id', '=', employee.id)], limit=1)
        vals = {'employee_id': employee.id or False, 'type_vehicule_utilise': 'personnel'}
        if vehicule:
            vals['vehicule_personnel_id'] = vehicule.id
        return vals

    @api.model
    def _km_hangar_vals(self):
        """Trajet siege -> hangar en aller-retour (adresses saisies, comme la reconstitution)."""
        Lieu = self.env['km.lieu.depart'].sudo()
        siege = Lieu.search([('code', '=', 'SIEGE')], limit=1) or Lieu.get_default()
        hangar = Lieu.search([('code', '=', 'HANGAR')], limit=1)
        return {
            'use_predefined': False,
            'lieu_depart': siege.adresse_complete or '',
            'lieu_arrivee': '%s (%s)' % (hangar.adresse_complete, hangar.name) if hangar else 'Hangar',
            'aller_retour': True,
            'distance_aller': float(self._km_param('auto_hangar_km', '1.0') or 1.0),
        }

    @api.model
    def _km_categorie(self, code):
        return self.env['km.trajet.categorie'].sudo().search([('code', '=', code)], limit=1)

    # ------------------------------------------------------------------
    # Nouveau client
    # ------------------------------------------------------------------
    @api.model
    def _km_create_trajets_nouveau_client(self, order):
        """Visite + signature au hangar pour le premier contrat d'un client."""
        partner = order.partner_id.commercial_partner_id
        if self.sudo().search_count([
            ('partner_id', 'child_of', partner.id),
            ('origine_trajet', 'in', ('visite_box', 'signature_contrat')),
        ]):
            return self.browse()
        base = self._km_auto_base_vals()
        if not base.get('employee_id'):
            _logger.warning("Trajets km nouveau client %s : aucun employe configure", order.name)
            return self.browse()
        orders = self.env['sale.order'].sudo().search([('partner_id', 'child_of', partner.id)])
        d_sign = fields.Date.to_date(order.start_date) if 'start_date' in order._fields and order.start_date \
            else fields.Date.to_date(order.date_order) or fields.Date.context_today(self)
        d_visite = min([fields.Date.to_date(o.create_date) for o in orders if o.create_date] or [d_sign])
        d_visite = min(d_visite, d_sign)
        a_confirmer = ' (même jour que la signature : date de visite à confirmer)' if d_visite == d_sign else ''
        categorie = self._km_categorie('CLIENT')
        vals_list = []
        for d, origine, motif in (
            (d_visite, 'visite_box', 'Visite du box avec %s avant contrat %s%s' % (partner.name, order.name, a_confirmer)),
            (d_sign, 'signature_contrat', 'Signature du contrat %s sur place avec %s' % (order.name, partner.name)),
        ):
            vals = dict(base, **self._km_hangar_vals())
            vals.update({
                'date': d,
                'partner_id': partner.id,
                'categorie_id': categorie.id or False,
                'origine_trajet': origine,
                'motif': motif,
                'auto_source': 'client',
                'state': 'brouillon',
                'notes': "Créé automatiquement à la confirmation du contrat %s. A relire avant validation." % order.name,
            })
            vals_list.append(vals)
        trajets = self.sudo().create(vals_list)
        order.message_post(body="Trajets kilométriques créés en brouillon : %s" % ', '.join(trajets.mapped('name')))
        return trajets

    # ------------------------------------------------------------------
    # Nettoyages et maintenance du hangar (action planifiee quotidienne)
    # ------------------------------------------------------------------
    @api.model
    def _km_jours_hangar(self, d):
        """Liste des (source, categorie, motif) a creer pour le jour d."""
        if d in jours_feries_belges(d.year):
            return []
        jours_net = [int(x) for x in (self._km_param('auto_nettoyage_jours', '0,3') or '').split(',') if x.strip()]
        jour_mai = int(self._km_param('auto_maintenance_jour', '5') or 5)
        out = []
        if d.weekday() in jours_net:
            out.append(('nettoyage', self._km_categorie('AUTRE'), MOTIF_NETTOYAGE))
        if d.weekday() == jour_mai and d.day <= 7:
            out.append(('maintenance', self._km_categorie('CHANTIER'), MOTIF_MAINTENANCE))
        return out

    @api.model
    def cron_trajets_hangar(self):
        if self._km_param('auto_hangar_active', '0') not in ('1', 'True', 'true'):
            return
        ICP = self.env['ir.config_parameter'].sudo()
        today = fields.Date.context_today(self)
        last = self._km_param('auto_hangar_last_date')
        d = (fields.Date.to_date(last) + timedelta(days=1)) if last else today
        d = max(d, today - timedelta(days=31))   # rattrapage limite a un mois
        base = self._km_auto_base_vals()
        if not base.get('employee_id'):
            _logger.warning("Trajets km hangar : aucun employe configure")
            return
        vals_list = []
        while d <= today:
            for source, categorie, motif in self._km_jours_hangar(d):
                if self.sudo().search_count([('date', '=', d), ('motif', '=', motif)]):
                    continue
                vals = dict(base, **self._km_hangar_vals())
                vals.update({
                    'date': d,
                    'categorie_id': categorie.id or False,
                    'origine_trajet': 'autre',
                    'motif': motif,
                    'auto_source': source,
                    'state': 'brouillon',
                    'notes': "Créé automatiquement (%s). A supprimer si le passage n'a pas eu lieu." % (
                        'nettoyage bihebdomadaire' if source == 'nettoyage' else 'maintenance mensuelle'),
                })
                vals_list.append(vals)
            d += timedelta(days=1)
        if vals_list:
            created = self.sudo().create(vals_list)
            _logger.info("Trajets km hangar crees : %s", created.mapped('name'))
        ICP.set_param(PARAM % 'auto_hangar_last_date', fields.Date.to_string(today))


class SaleOrderKm(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        Trajet = self.env['km.trajet']
        if Trajet._km_param('auto_client_active', '0') not in ('1', 'True', 'true'):
            return res
        for order in self:
            if not order._km_est_premier_contrat():
                continue
            try:
                with self.env.cr.savepoint():
                    Trajet._km_create_trajets_nouveau_client(order)
            except Exception:
                _logger.exception("Creation des trajets km pour %s", order.name)
        return res

    def _km_est_premier_contrat(self):
        """Premier contrat d'abonnement confirme du client (pas un renouvellement)."""
        self.ensure_one()
        if 'is_subscription' not in self._fields or not self.is_subscription:
            return False
        if 'origin_order_id' in self._fields and self.origin_order_id:
            return False
        partner = self.partner_id.commercial_partner_id
        return not self.search_count([
            ('id', '!=', self.id),
            ('partner_id', 'child_of', partner.id),
            ('is_subscription', '=', True),
            ('state', '=', 'sale'),
        ])
