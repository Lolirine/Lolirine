# -*- coding: utf-8 -*-
"""
launch_search_wizard
====================
Wizard pour lancer une recherche d'images depuis l'action de masse
sur la liste des produits.
"""
from odoo import api, fields, models


class LaunchSearchWizard(models.TransientModel):
    _name = 'pool.image.search.launch.wizard'
    _description = 'Lancer une recherche d\'images web'

    name = fields.Char(string='Nom de la session', default='Recherche images')

    product_ids = fields.Many2many(
        'product.template',
        string='Produits',
        required=True,
    )
    product_count = fields.Integer(
        string='Nb produits', compute='_compute_product_count'
    )

    only_missing_image = fields.Boolean(
        string='Uniquement produits sans image', default=True,
        help="Exclure les produits qui ont déjà une image principale"
    )

    max_candidates_per_product = fields.Integer(string='Max candidats/produit', default=5)
    auto_validate_threshold = fields.Float(
        string='Seuil auto-validation (%)', default=90.0
    )
    enable_bg_removal = fields.Boolean(string='Background removal', default=True)
    enable_webp = fields.Boolean(string='Conversion WebP', default=True)
    enable_phash_dedup = fields.Boolean(string='Détection doublons', default=True)
    max_image_size = fields.Integer(string='Taille max (px)', default=1200)

    run_mode = fields.Selection([
        ('queue', 'En file (cron en arrière-plan)'),
        ('now', 'Immédiat (synchrone, pour test)'),
    ], string='Mode d\'exécution', default='queue', required=True)

    @api.depends('product_ids')
    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.product_ids)

    def action_launch(self):
        self.ensure_one()
        products = self.product_ids
        if self.only_missing_image:
            products = products.filtered(lambda p: not p.image_1920)

        if not products:
            raise models.ValidationError(
                "Aucun produit à traiter après filtrage."
            )

        session = self.env['pool.image.search.session'].create({
            'name': self.name,
            'product_ids': [(6, 0, products.ids)],
            'max_candidates_per_product': self.max_candidates_per_product,
            'auto_validate_threshold': self.auto_validate_threshold,
            'enable_bg_removal': self.enable_bg_removal,
            'enable_webp': self.enable_webp,
            'enable_phash_dedup': self.enable_phash_dedup,
            'max_image_size': self.max_image_size,
        })

        if self.run_mode == 'queue':
            session.action_queue()
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'pool.image.search.session',
                'res_id': session.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return session.action_run_now()
