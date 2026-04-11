# -*- coding: utf-8 -*-
"""
Modèle de devis Pool Store — séparé du garde-meuble.
Séquence propre LPS-DEVIS/2025/0001.
Lié à sale.order via équipe de vente Pool Store.
"""
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PoolStoreQuote(models.Model):
    _name        = 'pool.store.quote'
    _description = 'Devis Pool Store'
    _order       = 'date_quote desc, id desc'
    _rec_name    = 'name'

    # ── Identification ────────────────────────────────────────────────────
    name = fields.Char(
        'Référence', required=True, copy=False, readonly=True,
        default=lambda self: _('Nouveau')
    )

    # ── Fiche liée ────────────────────────────────────────────────────────
    checklist_id = fields.Many2one(
        'pool.checklist.report', string='Fiche de visite',
        ondelete='set null'
    )

    # ── Client ────────────────────────────────────────────────────────────
    partner_id      = fields.Many2one('res.partner', string='Client', required=True)
    partner_type    = fields.Selection(
        [('particulier','Particulier'),('professionnel','Professionnel')],
        string='Type client', default='particulier'
    )
    intervention_type = fields.Selection([
        ('construction',    'Construction neuve'),
        ('renovation',      'Rénovation'),
        ('entretien',       'Entretien'),
        ('hivernage',       'Hivernage'),
        ('remise_en_route', 'Remise en route'),
        ('materiel',        'Changement de matériel'),
    ], string="Type d'intervention")

    # ── Dates ─────────────────────────────────────────────────────────────
    date_quote      = fields.Date('Date du devis', default=fields.Date.today, required=True)
    date_validity   = fields.Date('Valide jusqu\'au')
    date_confirmed  = fields.Date('Date de confirmation')

    # ── État ─────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft',      '📝 Brouillon'),
        ('sent',       '📨 Envoyé'),
        ('confirmed',  '✅ Confirmé'),
        ('po_created', '📦 Bon de commande créé'),
        ('done',       '🏁 Terminé'),
        ('cancelled',  '❌ Annulé'),
    ], string='État', default='draft', required=True, tracking=True)

    # ── Technicien ────────────────────────────────────────────────────────
    user_id = fields.Many2one(
        'res.users', string='Technicien/Commercial',
        default=lambda self: self.env.user
    )

    # ── Lignes ────────────────────────────────────────────────────────────
    line_ids = fields.One2many(
        'pool.store.quote.line', 'quote_id', string='Lignes'
    )

    # ── Totaux ────────────────────────────────────────────────────────────
    amount_materials = fields.Float('Matériaux HT',   compute='_compute_amounts', store=True)
    amount_labor     = fields.Float("Main d'œuvre HT", compute='_compute_amounts', store=True)
    amount_disposal  = fields.Float('Évacuation HT',   compute='_compute_amounts', store=True)
    amount_travel    = fields.Float('Déplacement HT',  compute='_compute_amounts', store=True)
    amount_untaxed   = fields.Float('Total HT',        compute='_compute_amounts', store=True)
    amount_tax       = fields.Float('TVA',             compute='_compute_amounts', store=True)
    amount_total     = fields.Float('Total TTC',       compute='_compute_amounts', store=True)
    vat_rate         = fields.Float('Taux TVA %', default=21.0)

    # ── Fournisseur dropshipping ──────────────────────────────────────────
    supplier_id = fields.Many2one(
        'res.partner', string='Fournisseur dropshipping',
        domain="[('supplier_rank','>',0)]"
    )
    supplier_type = fields.Selection([
        ('fluidra', 'Fluidra / SIBO'),
        ('scp',     'SCP Bénélux'),
        ('other',   'Autre'),
    ], string='Fournisseur type')

    # ── Commande & bon de commande liés ──────────────────────────────────
    sale_order_id     = fields.Many2one('sale.order',     'Commande client liée',   readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', 'Bon de commande fournisseur', readonly=True)

    # ── Notes ─────────────────────────────────────────────────────────────
    notes_internal = fields.Text('Notes internes')
    notes_client   = fields.Text('Conditions / Notes client')
    address_site   = fields.Char('Adresse du chantier')

    # ── Compute ───────────────────────────────────────────────────────────
    @api.depends('line_ids.subtotal', 'line_ids.line_type', 'vat_rate')
    def _compute_amounts(self):
        for rec in self:
            mat  = sum(l.subtotal for l in rec.line_ids if l.line_type == 'product')
            labor= sum(l.subtotal for l in rec.line_ids if l.line_type == 'labor')
            disp = sum(l.subtotal for l in rec.line_ids if l.line_type == 'disposal')
            trav = sum(l.subtotal for l in rec.line_ids if l.line_type == 'travel')
            untx = mat + labor + disp + trav
            tax  = untx * (rec.vat_rate / 100)
            rec.amount_materials = mat
            rec.amount_labor     = labor
            rec.amount_disposal  = disp
            rec.amount_travel    = trav
            rec.amount_untaxed   = untx
            rec.amount_tax       = tax
            rec.amount_total     = untx + tax

    # ── CRUD ──────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('pool.store.quote') or _('Nouveau')
        return super().create(vals_list)

    # ── Actions ───────────────────────────────────────────────────────────
    def action_send(self):
        self.write({'state': 'sent'})

    def action_confirm(self):
        self.write({'state': 'confirmed', 'date_confirmed': fields.Date.today()})
        # Créer la commande client Odoo
        return self._create_sale_order()

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_create_purchase_order(self):
        """Crée un bon de commande fournisseur pour les lignes dropshipping."""
        if not self.supplier_id:
            raise UserError("Veuillez sélectionner un fournisseur dropshipping avant de créer le bon de commande.")
        po = self._create_purchase_order()
        self.write({'state': 'po_created', 'purchase_order_id': po.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
        }

    def action_view_sale_order(self):
        if self.sale_order_id:
            return {'type':'ir.actions.act_window','res_model':'sale.order',
                    'res_id':self.sale_order_id.id,'view_mode':'form'}

    def action_view_purchase_order(self):
        if self.purchase_order_id:
            return {'type':'ir.actions.act_window','res_model':'purchase.order',
                    'res_id':self.purchase_order_id.id,'view_mode':'form'}

    def _create_sale_order(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin':     self.name,
            'note':       self.notes_client or '',
        })
        for line in self.line_ids:
            product = line.product_id
            if not product:
                # Créer produit de service si inexistant
                tmpl = self.env['product.template'].create({
                    'name':       line.name,
                    'type':       'service',
                    'list_price': line.unit_price,
                    'sale_ok':    True,
                })
                product = tmpl.product_variant_id
            self.env['sale.order.line'].create({
                'order_id':       order.id,
                'product_id':     product.id,
                'name':           line.name,
                'product_uom_qty':line.qty,
                'price_unit':     line.unit_price,
            })
        self.write({'sale_order_id': order.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
        }

    def _create_purchase_order(self):
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier_id.id,
            'origin':     self.name,
            'notes':      f"Dropshipping pour devis {self.name} — client {self.partner_id.name}",
        })
        for line in self.line_ids.filtered(lambda l: l.line_type == 'product'):
            product = line.product_id
            if not product:
                continue
            self.env['purchase.order.line'].create({
                'order_id':            po.id,
                'product_id':          product.id,
                'name':                line.name,
                'product_qty':         line.qty,
                'price_unit':          line.supplier_price or line.unit_price,
                'date_planned':        fields.Datetime.now(),
            })
        return po


class PoolStoreQuoteLine(models.Model):
    _name        = 'pool.store.quote.line'
    _description = 'Ligne de devis Pool Store'
    _order       = 'sequence, id'

    quote_id   = fields.Many2one('pool.store.quote', ondelete='cascade', required=True)
    sequence   = fields.Integer(default=10)
    line_type  = fields.Selection([
        ('product',  '📦 Matériel / Produit'),
        ('labor',    "🔨 Main d'œuvre"),
        ('disposal', '🗑️ Évacuation déchets'),
        ('travel',   '🚗 Frais de déplacement'),
    ], string='Type', default='product', required=True)

    product_id    = fields.Many2one('product.product', string='Produit')
    name          = fields.Char('Désignation', required=True)
    ref           = fields.Char('Référence')
    supplier_ref  = fields.Char('Réf. fournisseur')
    supplier_price= fields.Float("Prix d'achat HT")

    qty           = fields.Float('Quantité', default=1.0)
    unit          = fields.Char('Unité', default='pièce')
    unit_price    = fields.Float('Prix unitaire HT')
    discount      = fields.Float('Remise %')
    subtotal      = fields.Float('Sous-total HT', compute='_compute_subtotal', store=True)

    @api.depends('qty', 'unit_price', 'discount')
    def _compute_subtotal(self):
        for l in self:
            l.subtotal = l.qty * l.unit_price * (1 - l.discount / 100)
