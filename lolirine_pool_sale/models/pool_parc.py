# -*- coding: utf-8 -*-
"""Parc installé : équipements posés chez les clients (garanties, SAV, entretien saisonnier)."""
import re

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

CATEGORIES_EQUIPEMENT = [
    ('pac', 'Pompe à chaleur'),
    ('pompe', 'Pompe de filtration'),
    ('filtre', 'Filtre'),
    ('traitement', 'Traitement (électrolyseur, régulation…)'),
    ('robot', 'Robot nettoyeur'),
    ('couverture', 'Couverture / volet'),
    ('eclairage', 'Éclairage'),
    ('electricite', 'Coffret / électricité'),
    ('autre', 'Autre'),
]

MOTS_CATEGORIE = [
    ('pac', ('pompe à chaleur', 'inverter', 'heat pump')),
    ('pompe', ('pompe',)),
    ('filtre', ('filtre',)),
    ('traitement', ('électrolys', 'electrolys', 'régulat', 'regulat', 'chlorinat', 'uv-c', ' uv ')),
    ('robot', ('robot',)),
    ('couverture', ('couverture', 'volet', 'bâche', 'enrouleur')),
    ('eclairage', ('projecteur', 'éclairage', ' led')),
    ('electricite', ('coffret', 'différentiel', 'disjoncteur', 'horloge')),
]


def deviner_categorie(texte):
    texte = (texte or '').lower()
    if re.search(r'\bpac\b', texte):
        return 'pac'
    for cat, mots in MOTS_CATEGORIE:
        if any(m in texte for m in mots):
            return cat
    return 'autre'


class PoolEquipement(models.Model):
    _name = 'lolirine.pool.equipement'
    _description = "Équipement installé chez un client (parc piscine)"
    _inherit = ['mail.thread']
    _order = 'partner_id, date_pose desc, id desc'

    name = fields.Char("Équipement", required=True)
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one('res.partner', string="Client", required=True, index=True, tracking=True)
    adresse_chantier = fields.Char("Adresse de la piscine")
    categorie = fields.Selection(CATEGORIES_EQUIPEMENT, string="Catégorie", default='autre', required=True)
    product_id = fields.Many2one('product.product', string="Article")
    marque = fields.Char("Marque")
    modele = fields.Char("Modèle / référence")
    numero_serie = fields.Char("Numéro de série", tracking=True)
    date_pose = fields.Date("Date de pose", tracking=True)
    garantie_mois = fields.Integer("Garantie (mois)", default=24)
    date_fin_garantie = fields.Date("Fin de garantie", compute='_compute_garantie', store=True)
    sous_garantie = fields.Boolean("Sous garantie", compute='_compute_sous_garantie', search='_search_sous_garantie')
    order_id = fields.Many2one('sale.order', string="Devis / commande d'origine")
    pv_id = fields.Many2one('lolirine.pool.pv', string="Procès-verbal de réception")
    notes = fields.Text("Notes (SAV, entretien…)")

    @api.depends('date_pose', 'garantie_mois')
    def _compute_garantie(self):
        for e in self:
            e.date_fin_garantie = (e.date_pose + relativedelta(months=e.garantie_mois)) if e.date_pose and e.garantie_mois else False

    def _compute_sous_garantie(self):
        today = fields.Date.context_today(self)
        for e in self:
            e.sous_garantie = bool(e.date_fin_garantie and e.date_fin_garantie >= today)

    def _search_sous_garantie(self, operator, value):
        today = fields.Date.context_today(self)
        positif = (operator == '=' and value) or (operator == '!=' and not value)
        return [('date_fin_garantie', '>=', today)] if positif else \
            ['|', ('date_fin_garantie', '=', False), ('date_fin_garantie', '<', today)]

    @api.onchange('product_id')
    def _onchange_product_id(self):
        p = self.product_id
        if p:
            self.name = self.name or p.name
            self.modele = self.modele or p.default_code
            if 'pool_brand_id' in p._fields and p.pool_brand_id:
                self.marque = self.marque or p.pool_brand_id.display_name
            self.categorie = deviner_categorie(p.name)


class ResPartnerPool(models.Model):
    _inherit = 'res.partner'

    pool_equipement_ids = fields.One2many('lolirine.pool.equipement', 'partner_id', string="Parc installé")
    pool_equipement_count = fields.Integer("Équipements", compute='_compute_pool_equipement_count')
    pool_entretien_auto = fields.Boolean(
        "Entretien saisonnier",
        help="Le client reçoit chaque saison une proposition d'hivernage (septembre) et de remise en route (mars).")
    pool_formule_hivernage_id = fields.Many2one(
        'lolirine.pool.prestation', string="Formule d'hivernage", domain=[('categorie', '=', 'entretien')])
    pool_formule_remise_id = fields.Many2one(
        'lolirine.pool.prestation', string="Formule de remise en route", domain=[('categorie', '=', 'entretien')])
    pool_adresse_piscine = fields.Char("Adresse de la piscine")

    def _compute_pool_equipement_count(self):
        donnees = self.env['lolirine.pool.equipement']._read_group(
            [('partner_id', 'in', self.ids)], ['partner_id'], ['__count'])
        compte = {p.id: n for p, n in donnees}
        for partner in self:
            partner.pool_equipement_count = compte.get(partner.id, 0)

    def action_pool_parc(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Parc installé — %s" % self.display_name,
            'res_model': 'lolirine.pool.equipement',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id, 'default_adresse_chantier': self.pool_adresse_piscine},
        }
