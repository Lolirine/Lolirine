# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

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

BC_STATUTS = [
    ('draft',    '📝 Non préparé'),
    ('ready',    '✅ Prêt à envoyer'),
    ('sent',     '📤 Envoyé fournisseur'),
    ('received', '📦 Accusé de réception'),
    ('partial',  '⚠️ Livraison partielle'),
    ('done',     '✅ Livraison complète'),
]


class SaleOrderPool(models.Model):
    _inherit = 'sale.order'

    # ── Identification ─────────────────────────────────────────────
    is_pool_quote = fields.Boolean(
        string='Devis piscine',
        default=False,
    )

    # ── Lien fiche de visite ───────────────────────────────────────
    pool_fiche_id = fields.Char(
        string='ID fiche de visite',
        help='Identifiant unique de la fiche localStorage pour retrouver la visite d\'origine.',
    )

    # ── Chantier ───────────────────────────────────────────────────
    pool_intervention_type = fields.Selection(INTERVENTION_TYPES, string="Type d'intervention")
    pool_technicien        = fields.Char(string='Technicien')
    pool_adresse_chantier  = fields.Char(string='Adresse du chantier')
    pool_ref_dossier       = fields.Char(string='Référence dossier')
    pool_date_visite       = fields.Date(string='Date de visite')

    # ── Bassin ─────────────────────────────────────────────────────
    pool_basin_shape      = fields.Selection(BASIN_SHAPES, string='Forme du bassin')
    pool_basin_longueur   = fields.Float(string='Longueur (m)',      digits=(6, 2))
    pool_basin_largeur    = fields.Float(string='Largeur (m)',       digits=(6, 2))
    pool_basin_profondeur = fields.Float(string='Profondeur max (m)',digits=(6, 2))
    pool_basin_surface    = fields.Float(
        string='Surface (m²)', compute='_compute_basin_metrics', store=True)
    pool_basin_volume     = fields.Float(
        string='Volume estimé (m³)', compute='_compute_basin_metrics', store=True)
    pool_basin_notes      = fields.Text(string='Notes bassin')

    @api.depends('pool_basin_longueur', 'pool_basin_largeur', 'pool_basin_profondeur')
    def _compute_basin_metrics(self):
        for rec in self:
            l = rec.pool_basin_longueur or 0
            w = rec.pool_basin_largeur  or 0
            d = rec.pool_basin_profondeur or 0
            rec.pool_basin_surface = round(l * w, 2) if l and w else 0
            rec.pool_basin_volume  = round(l * w * d * 0.8, 2) if l and w and d else 0

    # ── Fiche de visite ────────────────────────────────────────────
    pool_visit_statut         = fields.Selection(VISIT_STATUTS, string='Statut visite', default='en_cours')
    pool_visit_observations   = fields.Text(string='Observations de visite')
    pool_visit_checklist_pct  = fields.Integer(string='Progression check-list (%)', default=0)

    # ── Dropshipping & fournisseur ─────────────────────────────────
    pool_fournisseur          = fields.Selection(FOURNISSEURS, string='Fournisseur principal')
    pool_fournisseur_other    = fields.Char(string='Autre fournisseur')
    pool_fournisseur_ref_cmd  = fields.Char(string='Réf. commande fournisseur')
    pool_fournisseur_ref_prod = fields.Char(string='Réf. produit fournisseur')
    pool_delai_livraison      = fields.Char(string='Délai de livraison estimé', default='5-10 jours ouvrés')
    pool_livraison_directe    = fields.Boolean(string='Livraison directe sur chantier', default=True)
    pool_livraison_adresse    = fields.Char(string='Adresse de livraison')

    # ── Bon de commande fournisseur ────────────────────────────────
    pool_bc_statut       = fields.Selection(
        BC_STATUTS, string='Statut BC fournisseur', default='draft',
        tracking=True,
    )
    pool_purchase_ids    = fields.Many2many(
        'purchase.order',
        'sale_pool_purchase_rel', 'sale_id', 'purchase_id',
        string='Bons de commande fournisseur',
    )
    pool_purchase_count  = fields.Integer(
        string='Nb BC', compute='_compute_purchase_count', store=False)

    @api.depends('pool_purchase_ids')
    def _compute_purchase_count(self):
        for rec in self:
            rec.pool_purchase_count = len(rec.pool_purchase_ids)

    # ── Frais & services ───────────────────────────────────────────
    pool_evacuation             = fields.Selection(EVACUATION, string='Évacuation déchets', default='client')
    pool_frais_deplacement      = fields.Float(string='Frais déplacement HT (€)', digits=(10, 2))
    pool_km                     = fields.Integer(string='Distance (km depuis Boninne)')
    pool_moeuvre                = fields.Float(string="Main d'oeuvre HT (€)", digits=(10, 2))
    pool_conditions_particulieres = fields.Text(string='Conditions particulières')

    # ══════════════════════════════════════════════════════════════
    #  Séquence dédiée PSC
    # ══════════════════════════════════════════════════════════════
    def _get_pool_template_id(self):
        tmpl = self.env['sale.order.template'].sudo().search(
            ['|', ('name', 'ilike', 'piscine'), ('name', 'ilike', 'pool')], limit=1)
        return tmpl.id if tmpl else False

    @api.model_create_multi
    def create(self, vals_list):
        pool_template_id = None
        for vals in vals_list:
            if vals.get('is_pool_quote'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'lolirine.pool.sale.order') or '/'
                if pool_template_id is None:
                    pool_template_id = self._get_pool_template_id()
                if pool_template_id and not vals.get('sale_order_template_id'):
                    vals['sale_order_template_id'] = pool_template_id
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.is_pool_quote and (not rec.name or rec.name == '/'):
                rec.name = self.env['ir.sequence'].next_by_code(
                    'lolirine.pool.sale.order') or '/'
        return super().action_confirm()

    def write(self, vals):
        if vals.get('is_pool_quote'):
            for rec in self:
                if not rec.name or rec.name == '/':
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'lolirine.pool.sale.order') or '/'
                    break
            if not vals.get('sale_order_template_id'):
                tmpl_id = self._get_pool_template_id()
                if tmpl_id:
                    vals['sale_order_template_id'] = tmpl_id
        return super().write(vals)

    # ══════════════════════════════════════════════════════════════
    #  Actions boutons
    # ══════════════════════════════════════════════════════════════
    def action_open_checklist(self):
        """Ouvre la fiche de visite — pointe sur la fiche d'origine si pool_fiche_id."""
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        url = '/visite-chantier'
        if self.pool_fiche_id:
            url += f'?fiche_id={self.pool_fiche_id}'
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}

    def action_view_purchases(self):
        """Ouvre les bons de commande fournisseur liés."""
        self.ensure_one()
        return {
            'type':    'ir.actions.act_window',
            'name':    'Bons de commande fournisseur',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain':  [('id', 'in', self.pool_purchase_ids.ids)],
            'context': {'default_origin': self.name},
        }

    def action_create_purchase_order(self):
        """
        Génère un bon de commande fournisseur depuis les lignes du devis piscine.
        Crée une PO par fournisseur présent sur les lignes.
        """
        self.ensure_one()
        if not self.is_pool_quote:
            raise UserError(_('Ce bouton est réservé aux devis piscine.'))
        if not self.order_line:
            raise UserError(_('Aucune ligne de commande à transférer.'))

        PO   = self.env['purchase.order'].sudo()
        POL  = self.env['purchase.order.line'].sudo()
        Partner = self.env['res.partner'].sudo()

        # Déterminer le partenaire fournisseur principal
        fourn_name = dict(FOURNISSEURS).get(self.pool_fournisseur, '') or self.pool_fournisseur_other or ''
        fourn_partner = False
        if fourn_name:
            fourn_partner = Partner.search(
                [('name', 'ilike', fourn_name.split('/')[0].strip()), ('supplier_rank', '>', 0)],
                limit=1
            )

        # Regrouper les lignes par fournisseur (via seller_ids ou le fourn principal)
        lines_by_vendor = {}
        for line in self.order_line:
            if line.display_type:
                continue
            vendor = False
            if line.product_id:
                seller = line.product_id.seller_ids[:1]
                vendor = seller.partner_id if seller else False
            if not vendor:
                vendor = fourn_partner
            if not vendor:
                continue
            if vendor.id not in lines_by_vendor:
                lines_by_vendor[vendor.id] = {'partner': vendor, 'lines': []}
            lines_by_vendor[vendor.id]['lines'].append(line)

        if not lines_by_vendor:
            raise UserError(_(
                'Impossible de déterminer le fournisseur.\n'
                'Vérifiez que les produits ont un fournisseur configuré ou renseignez le fournisseur principal dans l\'onglet Dropshipping.'
            ))

        created_pos = self.env['purchase.order']
        for vendor_id, data in lines_by_vendor.items():
            po_vals = {
                'partner_id':    data['partner'].id,
                'origin':        f'{self.name} — {self.partner_id.name}',
                'date_order':    fields.Datetime.now(),
                'notes':         (
                    f'Devis piscine : {self.name}\n'
                    f'Client : {self.partner_id.name}\n'
                    f'Chantier : {self.pool_adresse_chantier or ""}\n'
                    f'Livraison directe : {" Oui — " + (self.pool_livraison_adresse or self.pool_adresse_chantier or "") if self.pool_livraison_directe else "Non"}\n'
                    f'Délai souhaité : {self.pool_delai_livraison or ""}\n'
                    f'Réf. commande fourn : {self.pool_fournisseur_ref_cmd or "À compléter"}'
                ),
            }
            po = PO.create(po_vals)
            for line in data['lines']:
                product = line.product_id
                if not product:
                    continue
                # Prix d'achat depuis seller_ids ou prix de vente
                seller = product.seller_ids.filtered(
                    lambda s: s.partner_id.id == vendor_id)[:1]
                price = seller.price if seller else product.standard_price or line.price_unit
                POL.create({
                    'order_id':         po.id,
                    'product_id':       product.id,
                    'name':             line.name or product.display_name,
                    'product_qty':      line.product_uom_qty,
                    'product_uom':      line.product_uom.id,
                    'price_unit':       price,
                    'date_planned':     fields.Datetime.now(),
                })
            created_pos |= po

        # Lier les PO au devis
        self.pool_purchase_ids = [(4, po.id) for po in created_pos]
        self.pool_bc_statut = 'ready'

        # Ouvrir la première PO ou la liste
        if len(created_pos) == 1:
            return {
                'type':      'ir.actions.act_window',
                'res_model': 'purchase.order',
                'res_id':    created_pos.id,
                'view_mode': 'form',
                'target':    'current',
            }
        return self.action_view_purchases()
