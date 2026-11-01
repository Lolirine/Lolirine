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
    # Bâtiment
    ('bat_demolition', 'Bâtiment — Démolition, évacuation'),
    ('bat_gros_oeuvre', 'Bâtiment — Gros œuvre, maçonnerie'),
    ('bat_charpente', 'Bâtiment — Charpente, ossature bois'),
    ('bat_toiture', 'Bâtiment — Toiture, couverture, zinguerie'),
    ('bat_isolation', 'Bâtiment — Isolation'),
    ('bat_menuiserie', 'Bâtiment — Menuiseries, portes, fenêtres'),
    ('bat_cloisons', 'Bâtiment — Cloisons, plafonds, plafonnage'),
    ('bat_sols', 'Bâtiment — Sols, carrelage, chapes'),
    ('bat_peinture', 'Bâtiment — Peinture, finitions'),
    ('bat_electricite', 'Bâtiment — Électricité'),
    ('bat_plomberie', 'Bâtiment — Plomberie, sanitaire, chauffage'),
    ('bat_exterieur', 'Bâtiment — Terrassement, aménagements extérieurs'),
    ('autre', 'Autre'),
]

DOMAINES = [('piscine', 'Piscine'), ('batiment', 'Bâtiment')]
UNITES = [('forfait', 'Forfait'), ('m2', 'm²'), ('ml', 'm (mètre linéaire)'), ('m3', 'm³'),
          ('piece', 'pièce'), ('h', 'heure')]
UNITES_COURTES = {'forfait': 'forfait', 'm2': 'm²', 'ml': 'm', 'm3': 'm³', 'piece': 'pc', 'h': 'h'}


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
    domaine = fields.Selection(DOMAINES, string="Domaine", required=True, default='piscine', index=True)
    unite = fields.Selection(
        UNITES, string="Unité", required=True, default='forfait',
        help="Unité de l'ouvrage : le prix de la main-d'œuvre et les quantités de fournitures sont donnés "
             "pour 1 unité (1 m², 1 m…) et multipliés par le métré saisi dans le devis.")
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

    # ── Ouvrage : fournitures ajoutées avec la prestation ─────────────
    fourniture_ids = fields.One2many('lolirine.pool.prestation.fourniture', 'prestation_id',
                                     string="Fournitures de l'ouvrage", copy=True)
    section_fournitures = fields.Char(
        "Titre de la section fournitures",
        help="Section du devis où les fournitures sont ajoutées (par défaut : le titre de la prestation).")
    total_fournitures = fields.Float("Fournitures HT (€)", digits=(10, 2), compute='_compute_totaux')
    cout_fournitures = fields.Float("Coût fournitures (€)", digits=(10, 2), compute='_compute_totaux')
    total_ouvrage = fields.Float("Ouvrage complet HT (€)", digits=(10, 2), compute='_compute_totaux',
                                 help="Main-d'œuvre + fournitures (hors options).")
    nb_fournitures = fields.Integer("Fournitures", compute='_compute_totaux')

    @api.depends('fourniture_ids.quantite', 'fourniture_ids.prix_unitaire', 'fourniture_ids.cout_unitaire',
                 'fourniture_ids.optionnel', 'prix_forfait')
    def _compute_totaux(self):
        for p in self:
            fixes = p.fourniture_ids.filtered(lambda f: not f.optionnel)
            p.total_fournitures = sum(f.quantite * f.prix_unitaire for f in fixes)
            p.cout_fournitures = sum(f.quantite * f.cout_unitaire for f in fixes)
            p.total_ouvrage = p.total_fournitures + p.prix_forfait
            p.nb_fournitures = len(p.fourniture_ids)

    @api.depends('mode_prix', 'forfait_fixe', 'heures', 'taux_horaire', 'coef_difficulte', 'unite')
    def _compute_prix_forfait(self):
        for p in self:
            p.prix_forfait = calcul_prix(p.mode_prix, p.forfait_fixe, p.heures, p.taux_horaire, p.coef_difficulte, p.unite)


class PoolPrestationFourniture(models.Model):
    """Fourniture type d'un ouvrage (tés, vannes, colliers, câble…), ajoutée au devis avec la prestation."""
    _name = 'lolirine.pool.prestation.fourniture'
    _description = "Fourniture d'un ouvrage (devis piscine)"
    _order = 'prestation_id, sequence, id'

    prestation_id = fields.Many2one('lolirine.pool.prestation', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one('product.product', string="Article", required=True,
                                 domain=[('sale_ok', '=', True)])
    name = fields.Text("Libellé sur le devis",
                       help="Vide : le libellé de l'article. Indispensable pour un article générique "
                            "(« Fourniture diverse », « Fourniture électrique »).")
    quantite = fields.Float("Quantité", digits=(10, 4), default=1.0,
                            help="Pour un ouvrage au m² ou au mètre : quantité pour 1 unité (ex. 0,6944 panneau par m²).")
    prix_unitaire = fields.Float("Prix unitaire HT (€)", digits=(10, 2))
    cout_unitaire = fields.Float("Coût unitaire (€)", digits=(10, 2))
    optionnel = fields.Boolean("Option", help="Proposée en option : le client peut l'ajouter lui-même sur le devis en ligne.")
    perte_pct = fields.Float("Perte (%)", digits=(5, 1),
                             help="Chutes et recouvrements ajoutés à la quantité (ex. 10 % pour des panneaux).")
    arrondir = fields.Boolean("Arrondir", default=True,
                              help="Quantité arrondie à l'unité supérieure (panneaux, rouleaux, boîtes…).")
    sous_total = fields.Float("Sous-total HT (€)", digits=(10, 2), compute='_compute_sous_total')

    @api.depends('quantite', 'prix_unitaire')
    def _compute_sous_total(self):
        for f in self:
            f.sous_total = f.quantite * f.prix_unitaire

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.prix_unitaire = self.product_id.lst_price
            self.cout_unitaire = self.product_id.standard_price


def calcul_prix(mode, forfait, heures, taux, coef, unite='forfait'):
    """Prix HT de la prestation (pour 1 unité) : forfait saisi, ou heures × taux × coefficient,
    arrondi à 5 € pour un forfait, au centime pour un prix au m², au mètre, à la pièce…"""
    if mode == 'forfait':
        return forfait or 0.0
    brut = (heures or 0.0) * (taux or 0.0) * (coef or 1.0)
    return arrondi_5(brut) if (unite or 'forfait') == 'forfait' else round(brut, 2)


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
