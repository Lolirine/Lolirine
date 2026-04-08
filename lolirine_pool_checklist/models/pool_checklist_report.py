# -*- coding: utf-8 -*-
"""
Modèle de persistance des fiches de visite chantier piscine.
"""
import json
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PoolChecklistReport(models.Model):
    _name = 'pool.checklist.report'
    _description = 'Fiche de visite chantier piscine'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'

    # ── Identification ────────────────────────────────────────────────────
    name = fields.Char('Référence', required=True, copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('pool.checklist.report'))
    display_name = fields.Char('Nom', compute='_compute_display_name', store=True)

    # ── Client & chantier ─────────────────────────────────────────────────
    partner_id  = fields.Many2one('res.partner', string='Client', ondelete='set null')
    client_name = fields.Char('Nom client (libre)', help="Si pas encore dans les contacts")
    address     = fields.Char('Adresse chantier')
    tel         = fields.Char('Téléphone')

    # ── Intervention ─────────────────────────────────────────────────────
    intervention_type = fields.Selection([
        ('construction',    '🏗️ Construction neuve'),
        ('renovation',      '🔧 Rénovation'),
        ('entretien',       '🧹 Entretien régulier'),
        ('hivernage',       '❄️ Hivernage'),
        ('remise_en_route', '☀️ Remise en route'),
        ('materiel',        '⚙️ Changement de matériel'),
    ], string='Type d\'intervention', required=True)

    plan_type = fields.Selection([
        ('rect',    'Rectangulaire'),
        ('square',  'Carrée'),
        ('l_shape', 'En L'),
        ('oval',    'Ovale / Ronde'),
        ('kidney',  'Forme libre / Haricot'),
        ('spa',     'Rect. + Spa intégré'),
    ], string='Plan de bassin')

    # ── Technicien & dates ────────────────────────────────────────────────
    technician_id = fields.Many2one('res.users', string='Technicien',
                                    default=lambda self: self.env.user)
    date          = fields.Date('Date de visite', required=True, default=fields.Date.today)
    ref_dossier   = fields.Char('Référence dossier')

    # ── État ─────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft',    'Brouillon'),
        ('done',     'Validée'),
        ('archived', 'Archivée'),
    ], default='draft', string='État', required=True)

    # ── Données JSON (points de contrôle, produits liés) ─────────────────
    checklist_data = fields.Text('Données checklist (JSON)',
                                  help="Stocke l'état complet des points de contrôle")
    linked_products_data = fields.Text('Produits liés (JSON)')

    # ── Totaux ────────────────────────────────────────────────────────────
    items_total   = fields.Integer('Total points',   compute='_compute_stats', store=True)
    items_ok      = fields.Integer('Points OK',      compute='_compute_stats', store=True)
    items_warning = fields.Integer('À surveiller',   compute='_compute_stats', store=True)
    items_action  = fields.Integer('Action requise', compute='_compute_stats', store=True)
    completion_pct= fields.Float('Complétion %',     compute='_compute_stats', store=True)
    estimate_total= fields.Float('Estimation HT €',  compute='_compute_stats', store=True)

    # ── Signature ─────────────────────────────────────────────────────────
    signature_technicien = fields.Binary('Signature technicien')
    signature_client     = fields.Binary('Signature client')

    # ── Notes générales ───────────────────────────────────────────────────
    notes = fields.Text('Remarques générales')

    # ── Devis lié ─────────────────────────────────────────────────────────
    sale_order_id = fields.Many2one('sale.order', string='Devis/Commande lié',
                                     ondelete='set null', readonly=True)

    # ── Compute ───────────────────────────────────────────────────────────
    @api.depends('partner_id', 'client_name', 'intervention_type', 'date')
    def _compute_display_name(self):
        for rec in self:
            client = rec.partner_id.name or rec.client_name or 'Sans nom'
            itype  = dict(rec._fields['intervention_type'].selection).get(
                rec.intervention_type, rec.intervention_type or '')
            rec.display_name = f"{client} — {itype} — {rec.date or ''}"

    @api.depends('checklist_data', 'linked_products_data')
    def _compute_stats(self):
        for rec in self:
            try:
                data = json.loads(rec.checklist_data or '{}')
            except Exception:
                data = {}
            try:
                prods = json.loads(rec.linked_products_data or '[]')
            except Exception:
                prods = []

            total = ok = warn = action = 0
            for key, val in data.items():
                total += 1
                status = val.get('status', 'pending') if isinstance(val, dict) else ('ok' if val else 'pending')
                if status == 'ok':      ok     += 1
                elif status == 'warn':  warn   += 1
                elif status == 'action':action += 1

            estimate = sum((p.get('price', 0) or 0) * (p.get('qty', 1) or 1) for p in prods)

            rec.items_total    = total
            rec.items_ok       = ok
            rec.items_warning  = warn
            rec.items_action   = action
            rec.completion_pct = round((ok / total * 100) if total else 0, 1)
            rec.estimate_total = estimate

    # ── Méthodes ──────────────────────────────────────────────────────────
    def action_validate(self):
        self.write({'state': 'done'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_sale_order(self):
        if self.sale_order_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': self.sale_order_id.id,
                'view_mode': 'form',
            }

    def create_sale_order(self, products_data):
        """Crée un devis Odoo depuis la liste des produits liés."""
        partner = self.partner_id or self.env.ref('base.partner_admin')
        order_vals = {
            'partner_id': partner.id,
            'note': f"Fiche de visite chantier {self.name} — {self.display_name}",
            'origin': self.name,
        }
        order = self.env['sale.order'].create(order_vals)
        for p in products_data:
            product = self.env['product.template'].browse(int(p.get('id', 0)))
            if not product.exists():
                continue
            variant = product.product_variant_id
            if not variant:
                continue
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': variant.id,
                'product_uom_qty': p.get('qty', 1),
                'price_unit': p.get('price', 0) or variant.lst_price,
                'name': p.get('name', variant.name),
            })
        self.write({'sale_order_id': order.id, 'state': 'done'})
        return order.id


class PoolChecklistReportSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.model
    def _get_pool_sequence(self):
        seq = self.search([('code', '=', 'pool.checklist.report')], limit=1)
        if not seq:
            seq = self.create({
                'name': 'Fiche de visite piscine',
                'code': 'pool.checklist.report',
                'prefix': 'LPS/%(year)s/',
                'padding': 4,
                'number_next': 1,
                'number_increment': 1,
            })
        return seq
