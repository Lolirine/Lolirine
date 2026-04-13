# -*- coding: utf-8 -*-
from odoo import models, fields, api


# ──────────────────────────────────────────────────────────────────
#  Constantes
# ──────────────────────────────────────────────────────────────────
INTERVENTION_TYPES = [
    ('construction',    '🏗️ Construction neuve'),
    ('renovation',      '🔧 Rénovation'),
    ('entretien',       '🧹 Entretien régulier'),
    ('hivernage',       '❄️ Hivernage'),
    ('remise_en_route', '🌱 Remise en route'),
    ('materiel',        '⚙️ Changement de matériel'),
]

BASIN_SHAPES = [
    ('rectangulaire', 'Rectangulaire'),
    ('carre',         'Carré'),
    ('l',             'En L'),
    ('ovale',         'Ovale'),
    ('haricot',       'Haricot / Libre'),
    ('spa',           'Spa / Jacuzzi'),
]

VISIT_STATUTS = [
    ('en_cours',        '🔄 En cours'),
    ('termine',         '✅ Terminée'),
    ('a_replanifier',   '🔁 À replanifier'),
    ('attente_pieces',  '⏳ Attente pièces'),
]

FOURNISSEURS = [
    ('fluidra',     'Fluidra / SIBO'),
    ('scp',         'SCP Bénélux'),
    ('hth',         'HTH / BWT'),
    ('zodiac',      'Zodiac / Fluidra'),
    ('hayward',     'Hayward'),
    ('astralpool',  'Astralpool'),
    ('pentair',     'Pentair'),
    ('autre',       'Autre'),
]

EVACUATION = [
    ('client',  'Évacuation prise en charge par le client'),
    ('forfait', 'Forfait évacuation Lolirine (150 € HT)'),
    ('sans',    'Sans évacuation'),
]


class SaleOrderPool(models.Model):
    _inherit = 'sale.order'

    # ── Identification ────────────────────────────────────────────
    is_pool_quote = fields.Boolean(
        string='Devis piscine',
        default=False,
        help='Activez pour utiliser la séquence PSC et les onglets piscine.',
    )

    # ── Chantier ──────────────────────────────────────────────────
    pool_intervention_type = fields.Selection(
        INTERVENTION_TYPES,
        string="Type d'intervention",
    )
    pool_technicien = fields.Char(string='Technicien')
    pool_adresse_chantier = fields.Char(string='Adresse du chantier')
    pool_ref_dossier = fields.Char(string='Référence dossier')
    pool_date_visite = fields.Date(string='Date de visite')

    # ── Bassin ────────────────────────────────────────────────────
    pool_basin_shape = fields.Selection(BASIN_SHAPES, string='Forme du bassin')
    pool_basin_longueur = fields.Float(string='Longueur (m)', digits=(6, 2))
    pool_basin_largeur  = fields.Float(string='Largeur (m)',  digits=(6, 2))
    pool_basin_profondeur = fields.Float(string='Profondeur max (m)', digits=(6, 2))
    pool_basin_surface  = fields.Float(
        string='Surface (m²)',
        compute='_compute_basin_metrics',
        store=True,
    )
    pool_basin_volume   = fields.Float(
        string='Volume estimé (m³)',
        compute='_compute_basin_metrics',
        store=True,
    )
    pool_basin_notes = fields.Text(string='Notes bassin')

    @api.depends('pool_basin_longueur', 'pool_basin_largeur', 'pool_basin_profondeur')
    def _compute_basin_metrics(self):
        for rec in self:
            l = rec.pool_basin_longueur or 0
            w = rec.pool_basin_largeur  or 0
            d = rec.pool_basin_profondeur or 0
            rec.pool_basin_surface = round(l * w, 2) if l and w else 0
            rec.pool_basin_volume  = round(l * w * d * 0.8, 2) if l and w and d else 0

    # ── Fiche de visite ───────────────────────────────────────────
    pool_visit_statut = fields.Selection(
        VISIT_STATUTS,
        string='Statut de la visite',
        default='en_cours',
    )
    pool_visit_observations = fields.Text(string='Observations de visite')
    pool_visit_checklist_pct = fields.Integer(
        string='Progression check-list (%)',
        default=0,
    )

    # ── Dropshipping ──────────────────────────────────────────────
    pool_fournisseur = fields.Selection(FOURNISSEURS, string='Fournisseur principal')
    pool_fournisseur_other = fields.Char(string='Autre fournisseur')
    pool_fournisseur_ref_cmd = fields.Char(string='Réf. commande fournisseur')
    pool_fournisseur_ref_prod = fields.Char(string='Réf. produit fournisseur')
    pool_delai_livraison = fields.Char(
        string='Délai de livraison estimé',
        default='5-10 jours ouvrés',
    )
    pool_livraison_directe = fields.Boolean(
        string='Livraison directe sur chantier',
        default=True,
    )
    pool_livraison_adresse = fields.Char(string='Adresse de livraison')

    # ── Frais & services ──────────────────────────────────────────
    pool_evacuation = fields.Selection(
        EVACUATION,
        string='Évacuation déchets',
        default='client',
    )
    pool_frais_deplacement = fields.Float(
        string='Frais de déplacement HT (€)',
        digits=(10, 2),
    )
    pool_km = fields.Integer(string='Distance (km depuis Boninne)')
    pool_moeuvre = fields.Float(
        string="Main d'œuvre HT (€)",
        digits=(10, 2),
    )
    pool_conditions_particulieres = fields.Text(string='Conditions particulières')

    # ── Séquence dédiée PSC ───────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_pool_quote') and vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('lolirine.pool.sale.order') or '/'
        return super().create(vals_list)

    def action_confirm(self):
        """Lors de la confirmation, assigner la séquence si pas encore fait."""
        for rec in self:
            if rec.is_pool_quote and rec.name == '/':
                rec.name = self.env['ir.sequence'].next_by_code('lolirine.pool.sale.order') or '/'
        return super().action_confirm()

    def action_open_checklist(self):
        """Ouvrir la fiche de visite dans un nouvel onglet."""
        return {
            'type': 'ir.actions.act_url',
            'url': '/visite-chantier',
            'target': 'new',
        }

    def _compute_pool_totals_note(self):
        """Génère une note de synthèse chantier pour le chatter."""
        self.ensure_one()
        lines = []
        if self.pool_intervention_type:
            lines.append(f"Type : {dict(INTERVENTION_TYPES).get(self.pool_intervention_type, '')}")
        if self.pool_adresse_chantier:
            lines.append(f"Chantier : {self.pool_adresse_chantier}")
        if self.pool_technicien:
            lines.append(f"Technicien : {self.pool_technicien}")
        if self.pool_basin_surface:
            lines.append(f"Bassin : {self.pool_basin_surface} m² — {self.pool_basin_volume} m³ estimé")
        if self.pool_fournisseur:
            lines.append(f"Fournisseur : {dict(FOURNISSEURS).get(self.pool_fournisseur, '')}")
        return '\n'.join(lines)
