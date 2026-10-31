# -*- coding: utf-8 -*-
from odoo import api, fields, models

CATEGORIES = [
    ('construction', 'Construction'),
    ('local_technique', 'Local technique'),
    ('liner', 'Liner et membrane armée'),
    ('chauffage', 'Chauffage (pompe à chaleur…)'),
    ('traitement', 'Traitement de l\'eau'),
    ('electricite', 'Électricité'),
    ('plomberie', 'Plomberie / raccordement'),
    ('couverture', 'Couverture et volet'),
    ('entretien', 'Entretien, hivernage, remise en route'),
    ('autre', 'Autre'),
]


class PoolPrestation(models.Model):
    """Tableau de main-d'œuvre : prestations type à reprendre dans un devis piscine.

    Le client ne voit que le titre et la description des travaux ; le détail
    des heures reste interne (champ pool_mo_detail de la ligne de devis).
    """
    _name = 'lolirine.pool.prestation'
    _description = "Prestation de main-d'œuvre (devis piscine)"
    _order = 'categorie, sequence, name'

    name = fields.Char("Prestation (titre sur le devis)", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    categorie = fields.Selection(CATEGORIES, string='Catégorie', required=True, default='autre')
    description_client = fields.Text(
        "Travaux décrits au client",
        help="Texte imprimé sous le titre sur le devis : les travaux, SANS heures ni taux.")
    detail_interne = fields.Text(
        "Détail interne (étapes et heures)",
        help="Non imprimé. Sert à calculer le temps et reste visible sur la ligne du devis, en interne.")
    mode_prix = fields.Selection([('heures', 'Au temps passé (heures × taux)'), ('forfait', 'Prix au forfait')],
                                 string="Mode de prix", required=True, default='heures')
    forfait_fixe = fields.Float("Prix au forfait HT (€)", digits=(10, 2),
                                help="Utilisé quand le mode de prix est « Prix au forfait ».")
    heures = fields.Float("Heures estimées", digits=(10, 2))
    taux_horaire = fields.Float("Taux horaire HT (€)", digits=(10, 2), default=55.0)
    coef_difficulte = fields.Float("Coefficient de difficulté", digits=(10, 2), default=1.0)
    prix_forfait = fields.Float("Prix HT (€)", digits=(10, 2), compute='_compute_prix_forfait', store=True)
    product_id = fields.Many2one(
        'product.product', string="Article de main-d'œuvre",
        default=lambda self: self.env['product.product'].search([('default_code', '=', 'MO-FORFAIT')], limit=1))

    @api.depends('mode_prix', 'forfait_fixe', 'heures', 'taux_horaire', 'coef_difficulte')
    def _compute_prix_forfait(self):
        for p in self:
            p.prix_forfait = calcul_prix(p.mode_prix, p.forfait_fixe, p.heures, p.taux_horaire, p.coef_difficulte)


def calcul_prix(mode, forfait, heures, taux, coef):
    """Prix HT de la prestation : forfait saisi, ou heures × taux × coefficient arrondi à 5 €."""
    if mode == 'forfait':
        return forfait or 0.0
    return arrondi_5((heures or 0.0) * (taux or 0.0) * (coef or 1.0))


def arrondi_5(montant):
    """Arrondi au multiple de 5 € le plus proche (forfait lisible pour le client)."""
    return round((montant or 0.0) / 5.0) * 5.0


class SaleOrderLinePool(models.Model):
    _inherit = 'sale.order.line'

    pool_mo_detail = fields.Text(
        "Détail interne main-d'œuvre",
        help="Heures, taux et étapes de la prestation. Jamais imprimé sur le devis.")
    pool_prestation_id = fields.Many2one('lolirine.pool.prestation', string="Prestation", ondelete='set null')
    pool_image = fields.Image(
        "Photo", related='product_id.image_128',
        help="Photo du produit telle qu'elle apparaît sur le site, pour contrôler l'article choisi.")
