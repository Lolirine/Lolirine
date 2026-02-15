# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_dropship_product = fields.Boolean(string='Produit dropshipping', default=False)
    dropship_supplier_ids = fields.One2many(
        'supplier.dropship.info', 'product_tmpl_id', string='Fournisseurs dropshipping',
    )
    dropship_supplier_count = fields.Integer(
        string='Nb fournisseurs', compute='_compute_dropship_supplier_count',
    )
    preferred_dropship_supplier_id = fields.Many2one(
        'res.partner', string='Fournisseur préféré',
        domain=[('is_dropship_supplier', '=', True)],
    )
    best_margin_supplier_id = fields.Many2one(
        'res.partner', string='Meilleure marge',
        compute='_compute_best_suppliers', store=True,
    )
    fastest_supplier_id = fields.Many2one(
        'res.partner', string='Plus rapide',
        compute='_compute_best_suppliers', store=True,
    )
    best_overall_supplier_id = fields.Many2one(
        'res.partner', string='Meilleur global',
        compute='_compute_best_suppliers', store=True,
    )
    supplier_stock_available = fields.Boolean(
        string='Dispo fournisseur', compute='_compute_supplier_stock',
    )
    supplier_lead_time = fields.Integer(
        string='Délai fournisseur (jours)', compute='_compute_supplier_stock',
    )

    @api.depends('dropship_supplier_ids')
    def _compute_dropship_supplier_count(self):
        for product in self:
            product.dropship_supplier_count = len(
                product.dropship_supplier_ids.filtered('is_active')
            )

    @api.depends('dropship_supplier_ids.negotiated_price', 'dropship_supplier_ids.delay',
                 'dropship_supplier_ids.reliability_score', 'dropship_supplier_ids.is_active')
    def _compute_best_suppliers(self):
        for product in self:
            active_infos = product.dropship_supplier_ids.filtered('is_active')
            if not active_infos:
                product.best_margin_supplier_id = False
                product.fastest_supplier_id = False
                product.best_overall_supplier_id = False
                continue

            # Meilleure marge = prix négocié le plus bas
            best_margin = min(active_infos, key=lambda i: i.negotiated_price or 999999)
            product.best_margin_supplier_id = best_margin.supplier_id.id

            # Plus rapide
            best_speed = min(active_infos, key=lambda i: i.delay or 999)
            product.fastest_supplier_id = best_speed.supplier_id.id

            # Meilleur global (combinaison prix + fiabilité + délai)
            def score(info):
                price_score = (1 - (info.negotiated_price / info.price)) if info.price else 0
                delay_score = max(0, 1 - (info.delay / 30)) if info.delay else 0.5
                reliability = (info.reliability_score or 50) / 100
                return price_score * 0.4 + delay_score * 0.3 + reliability * 0.3

            best_overall = max(active_infos, key=score)
            product.best_overall_supplier_id = best_overall.supplier_id.id

    def _compute_supplier_stock(self):
        for product in self:
            pref_info = product.dropship_supplier_ids.filtered(
                lambda i: i.is_active and i.supplier_id == product.preferred_dropship_supplier_id
            )
            if not pref_info:
                pref_info = product.dropship_supplier_ids.filtered('is_active')[:1]

            if pref_info:
                product.supplier_stock_available = pref_info[0].supplier_stock > 0
                product.supplier_lead_time = pref_info[0].delay
            else:
                product.supplier_stock_available = False
                product.supplier_lead_time = 0
