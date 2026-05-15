# -*- coding: utf-8 -*-
"""
Extension product.template
==========================
Ajoute :
- Champ candidate_ids (O2M vers pool.image.search.candidate)
- Bouton stat box "Candidats images"
- Indicateur "image manquante ou de mauvaise qualité"
- Action pour lancer une recherche d'images sur les produits sélectionnés
"""
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    image_candidate_ids = fields.One2many(
        'pool.image.search.candidate', 'product_id',
        string='Candidats images',
    )
    image_candidate_count = fields.Integer(
        string='Nb candidats',
        compute='_compute_image_candidate_count',
    )
    image_needs_review = fields.Boolean(
        string='Image à revoir',
        compute='_compute_image_needs_review',
        store=False,
        search='_search_image_needs_review',
        help="Produit sans image ou avec image de mauvaise qualité (extraction PDF)",
    )

    @api.depends('image_candidate_ids')
    def _compute_image_candidate_count(self):
        for rec in self:
            rec.image_candidate_count = len(rec.image_candidate_ids)

    def _compute_image_needs_review(self):
        for rec in self:
            rec.image_needs_review = not rec.image_1920

    def _search_image_needs_review(self, operator, value):
        if operator == '=' and value:
            return [('image_1920', '=', False)]
        if operator == '=' and not value:
            return [('image_1920', '!=', False)]
        return []

    # --- Actions ---

    def action_view_image_candidates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Candidats - {self.name}',
            'res_model': 'pool.image.search.candidate',
            'view_mode': 'kanban,list,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }

    def action_launch_image_search(self):
        """Action multi-records : lance le wizard de recherche."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rechercher images web',
            'res_model': 'pool.image.search.launch.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_ids': [(6, 0, self.ids)],
            },
        }
