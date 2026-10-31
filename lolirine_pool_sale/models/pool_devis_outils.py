# -*- coding: utf-8 -*-
"""Outils du devis piscine (inspirés des logiciels de gestion de chantier) :

- conditions de paiement calculées (matériel à la commande / main-d'œuvre à l'avancement)
  et acompte en ligne égal à la part matériel ;
- marge du matériel avant commande (coût des lignes), alerte sous 15 % ;
- autoliquidation (régime du cocontractant) pour les travaux immobiliers B2B ;
- avancement de la main-d'œuvre en % (facturation par états d'avancement) ;
- fiche de visite technique (local, électricité, accès, photos).
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

SEUIL_MARGE = 0.15

LOCAL_TECHNIQUE = [
    ('interieur', 'Dans un bâtiment (cave, garage…)'),
    ('abri', 'Abri ou coffre extérieur'),
    ('enterre', 'Local enterré'),
    ('aucun', 'Pas de local technique'),
]
ALIMENTATION = [('mono', 'Monophasé 230 V'), ('tri', 'Triphasé 400 V'), ('tri230', 'Triphasé 230 V')]
DIAMETRES = [('50', 'Ø50'), ('63', 'Ø63'), ('75', 'Ø75'), ('autre', 'Autre')]
ACCES = [('facile', 'Facile'), ('moyen', 'Moyen (portage, marches)'), ('difficile', 'Difficile (engin impossible…)')]


def montant_fr(valeur):
    """2866.04 -> '2 866,04'"""
    return '{:,.2f}'.format(valeur or 0.0).replace(',', ' ').replace('.', ',')


class SaleOrderLineOutils(models.Model):
    _inherit = 'sale.order.line'

    pool_est_mo = fields.Boolean("Main-d'œuvre", compute='_compute_pool_est_mo')
    pool_avancement = fields.Float(
        "Avancement (%)", digits=(5, 1), compute='_compute_pool_avancement', inverse='_inverse_pool_avancement',
        help="Part des travaux réalisée : sert à facturer la main-d'œuvre par états d'avancement "
             "(quantité livrée = avancement × quantité).")

    def _pool_ligne_mo(self):
        """Main-d'œuvre / déplacement : prestation du tableau, ou article MO-… / DEPL."""
        self.ensure_one()
        if self.display_type:
            return False
        if self.pool_prestation_id:
            return True
        code = (self.product_id.default_code or '').upper()
        return code.startswith('MO-') or code.startswith('DEPL')

    @api.depends('product_id', 'display_type', 'pool_prestation_id')
    def _compute_pool_est_mo(self):
        for line in self:
            line.pool_est_mo = line._pool_ligne_mo()

    @api.depends('qty_delivered', 'product_uom_qty')
    def _compute_pool_avancement(self):
        for line in self:
            line.pool_avancement = (line.qty_delivered / line.product_uom_qty * 100.0) if line.product_uom_qty else 0.0

    def _inverse_pool_avancement(self):
        for line in self:
            if line.qty_delivered_method != 'manual':
                raise UserError(_("L'avancement ne se saisit que sur une ligne à livraison manuelle "
                                  "(main-d'œuvre facturée à l'avancement) : %s") % line.name)
            pct = min(max(line.pool_avancement, 0.0), 100.0)
            line.qty_delivered = line.product_uom_qty * pct / 100.0


class SaleOrderOutils(models.Model):
    _inherit = 'sale.order'

    # ── Conditions de paiement ───────────────────────────────────────
    pool_mat_ht = fields.Monetary("Matériel HT", compute='_compute_pool_paiement')
    pool_mat_ttc = fields.Monetary("Matériel TVAC", compute='_compute_pool_paiement')
    pool_mo_ht = fields.Monetary("Main-d'œuvre HT", compute='_compute_pool_paiement')
    pool_mo_ttc = fields.Monetary("Main-d'œuvre TVAC", compute='_compute_pool_paiement')
    pool_conditions_actives = fields.Boolean(compute='_compute_pool_paiement')

    # ── Marge du matériel (avant commande) ───────────────────────────
    pool_marge_mat = fields.Monetary("Marge matériel", compute='_compute_pool_marge_mat')
    pool_marge_mat_pct = fields.Float("Marge matériel (%)", compute='_compute_pool_marge_mat')
    pool_lignes_sans_cout = fields.Char(compute='_compute_pool_marge_mat')
    pool_marge_alerte = fields.Boolean(compute='_compute_pool_marge_mat')

    # ── Autoliquidation ──────────────────────────────────────────────
    pool_autoliquidation = fields.Boolean(
        "Autoliquidation (cocontractant)", tracking=True, copy=False,
        help="Travaux immobiliers pour un client assujetti déposant des déclarations TVA périodiques : "
             "la TVA est due par le client (position fiscale « Cocontractant », mention légale sur la facture).")
    pool_autoliq_suggeree = fields.Boolean(compute='_compute_pool_autoliq_suggeree')

    # ── Visite technique ─────────────────────────────────────────────
    pool_vt_local = fields.Selection(LOCAL_TECHNIQUE, string="Local technique")
    pool_vt_dist_local = fields.Float("Distance bassin → local (m)", digits=(6, 1))
    pool_vt_dist_pac = fields.Float("Distance local → emplacement PAC (m)", digits=(6, 1))
    pool_vt_diametre = fields.Selection(DIAMETRES, string="Diamètre de la tuyauterie")
    pool_vt_alimentation = fields.Selection(ALIMENTATION, string="Alimentation électrique")
    pool_vt_tableau = fields.Char("Tableau électrique", help="ex. 40 A, différentiel 30 mA présent")
    pool_vt_place_tableau = fields.Boolean("Place libre au tableau")
    pool_vt_dist_tableau = fields.Float("Distance tableau → équipement (m)", digits=(6, 1))
    pool_vt_acces = fields.Selection(ACCES, string="Accès au chantier")
    pool_vt_acces_note = fields.Char("Précision sur l'accès")
    pool_vt_evacuation = fields.Boolean("Évacuation à l'égout possible")
    pool_vt_equipements = fields.Text("Équipements existants")
    pool_vt_photo_ids = fields.Many2many(
        'ir.attachment', 'sale_order_pool_vt_photo_rel', 'order_id', 'attachment_id',
        string="Photos de la visite")

    # ─────────────────────────────────────────────────────────────────
    #  Conditions de paiement
    # ─────────────────────────────────────────────────────────────────
    @api.depends('is_pool_quote', 'order_line.price_subtotal', 'order_line.price_total',
                 'order_line.product_id', 'order_line.display_type', 'amount_untaxed', 'amount_total')
    def _compute_pool_paiement(self):
        for order in self:
            mo = order.order_line.filtered(lambda l: l._pool_ligne_mo())
            arrondi = order.currency_id.round if order.currency_id else (lambda v: round(v, 2))
            order.pool_mo_ht = arrondi(sum(mo.mapped('price_subtotal')))
            order.pool_mo_ttc = arrondi(sum(mo.mapped('price_total')))
            order.pool_mat_ht = arrondi(order.amount_untaxed - order.pool_mo_ht)
            order.pool_mat_ttc = arrondi(order.amount_total - order.pool_mo_ttc)
            order.pool_conditions_actives = bool(
                order.is_pool_quote and order.pool_mo_ht > 0 and order.pool_mat_ht > 0)

    def _pool_conditions_lignes(self):
        """Textes de l'encadré « Conditions de paiement » (PDF et portail)."""
        self.ensure_one()
        return [
            ("1) Matériel : %s € TVAC (%s € HT), payable intégralement à la commande."
             % (montant_fr(self.pool_mat_ttc), montant_fr(self.pool_mat_ht)),
             "La livraison du matériel chez le client n'a lieu qu'après réception de ce paiement."),
            ("2) Main-d'œuvre et déplacements : %s € TVAC (%s € HT), payables par acomptes "
             "au fur et à mesure de l'avancement du chantier."
             % (montant_fr(self.pool_mo_ttc), montant_fr(self.pool_mo_ht)), ""),
        ]

    @api.depends('company_id', 'is_pool_quote', 'order_line.price_total', 'order_line.product_id')
    def _compute_prepayment_percent(self):
        """Devis piscine avec main-d'œuvre : l'acompte en ligne = la part matériel TVAC."""
        super()._compute_prepayment_percent()
        for order in self:
            if not order.is_pool_quote or order.state not in ('draft', 'sent'):
                continue
            mo_ttc = sum(order.order_line.filtered(lambda l: l._pool_ligne_mo()).mapped('price_total'))
            total = sum(order.order_line.filtered(lambda l: not l.display_type).mapped('price_total'))
            if mo_ttc > 0 and total > mo_ttc:
                order.prepayment_percent = (total - mo_ttc) / total

    # ─────────────────────────────────────────────────────────────────
    #  Marge du matériel
    # ─────────────────────────────────────────────────────────────────
    @api.depends('order_line.price_subtotal', 'order_line.purchase_price', 'order_line.product_uom_qty',
                 'order_line.product_id', 'is_pool_quote')
    def _compute_pool_marge_mat(self):
        for order in self:
            mat = order.order_line.filtered(
                lambda l: not l.display_type and not l._pool_ligne_mo() and l.product_uom_qty)
            vente = sum(mat.mapped('price_subtotal'))
            cout = sum(l.purchase_price * l.product_uom_qty for l in mat)
            sans_cout = mat.filtered(lambda l: not l.purchase_price)
            order.pool_marge_mat = vente - cout
            order.pool_marge_mat_pct = ((vente - cout) / vente * 100.0) if vente else 0.0
            order.pool_lignes_sans_cout = ", ".join(
                (l.name or '').split('\n')[0][:40] for l in sans_cout) if sans_cout else False
            order.pool_marge_alerte = bool(
                order.is_pool_quote and vente and (order.pool_marge_mat_pct < SEUIL_MARGE * 100 or sans_cout))

    # ─────────────────────────────────────────────────────────────────
    #  Autoliquidation
    # ─────────────────────────────────────────────────────────────────
    def _pool_position_cocontractant(self):
        self.ensure_one()
        fp = self.env.ref('account.%s_fiscal_position_template_4' % self.company_id.id, raise_if_not_found=False)
        if not fp:
            fp = self.env['account.fiscal.position'].search(
                [('company_id', 'in', [self.company_id.id, False]),
                 '|', '|', ('name', 'ilike', 'cocontractant'), ('name', 'ilike', 'co-contractant'),
                 ('name', 'ilike', 'medecontractant')], limit=1)
        if not fp:
            raise UserError(_("Position fiscale « Cocontractant » introuvable (plan comptable belge)."))
        return fp

    @api.depends('is_pool_quote', 'partner_id', 'pool_autoliquidation', 'order_line.product_id')
    def _compute_pool_autoliq_suggeree(self):
        for order in self:
            client = order.partner_id.commercial_partner_id
            order.pool_autoliq_suggeree = bool(
                order.is_pool_quote and not order.pool_autoliquidation
                and client.is_company and (client.vat or '').upper().startswith('BE')
                and any(l._pool_ligne_mo() for l in order.order_line))

    @api.onchange('pool_autoliquidation')
    def _onchange_pool_autoliquidation(self):
        if self.pool_autoliquidation:
            self.fiscal_position_id = self._pool_position_cocontractant()
        else:
            self._compute_fiscal_position_id()

    def _pool_appliquer_autoliquidation(self):
        for order in self:
            if order.state not in ('draft', 'sent'):
                continue
            if order.pool_autoliquidation:
                fp = order._pool_position_cocontractant()
                if order.fiscal_position_id != fp:
                    order.fiscal_position_id = fp
            else:
                order._compute_fiscal_position_id()
            order._recompute_taxes()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        # devis créé avec ses lignes : l'acompte précalculé ignorait encore les lignes
        orders.filtered(lambda o: o.is_pool_quote and o.order_line)._compute_prepayment_percent()
        orders.filtered('pool_autoliquidation')._pool_appliquer_autoliquidation()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if 'pool_autoliquidation' in vals:
            self._pool_appliquer_autoliquidation()
        return res

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.pool_autoliquidation:
            vals['fiscal_position_id'] = self._pool_position_cocontractant().id
        return vals

    # ─────────────────────────────────────────────────────────────────
    #  Actions
    # ─────────────────────────────────────────────────────────────────
    def action_pool_enregistrer_ouvrage(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Enregistrer comme ouvrage",
            'res_model': 'lolirine.pool.ouvrage.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }
