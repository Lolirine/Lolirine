# -*- coding: utf-8 -*-
"""
pool_image_search_candidate
===========================
Un candidat = une image trouvée par le scraping pour un produit donné.

États :
- pending : à valider
- main    : sélectionné comme image principale
- gallery : sélectionné comme image secondaire (galerie)
- rejected: rejeté

L'utilisateur valide dans la vue kanban. Le champ `applied` indique si
l'image a déjà été poussée sur product.template / product.image.
"""
import base64
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PoolImageSearchCandidate(models.Model):
    _name = 'pool.image.search.candidate'
    _description = 'Candidat image produit'
    _order = 'product_id, rank, score desc'

    session_id = fields.Many2one(
        'pool.image.search.session', string='Session',
        required=True, ondelete='cascade', index=True,
    )
    product_id = fields.Many2one(
        'product.template', string='Produit',
        required=True, ondelete='cascade', index=True,
    )

    # Métadonnées source
    source_name = fields.Char(string='Source')
    source_url = fields.Char(string='URL de la page')
    image_url = fields.Char(string='URL de l\'image')

    # Variantes d'image stockées
    image_main = fields.Image(string='Image traitée', max_width=1200, max_height=1200)
    image_thumb = fields.Image(string='Miniature', max_width=300, max_height=300)
    image_raw = fields.Image(string='Image brute', attachment=True)
    image_no_bg = fields.Image(string='Sans fond', attachment=True)

    # Scoring & dimensions
    score = fields.Float(string='Score (%)', default=0.0, group_operator='avg')
    width = fields.Integer(string='Largeur')
    height = fields.Integer(string='Hauteur')
    phash = fields.Char(string='Hash perceptuel', index=True)

    rank = fields.Integer(string='Rang', default=1)

    # État de validation
    state = fields.Selection([
        ('pending', 'À valider'),
        ('main', 'Image principale'),
        ('gallery', 'Galerie'),
        ('rejected', 'Rejeté'),
    ], string='Statut', default='pending', tracking=True, index=True)

    auto_validated = fields.Boolean(string='Auto-validé', default=False)
    applied = fields.Boolean(string='Appliqué au produit', default=False)
    applied_date = fields.Datetime(string='Date d\'application')

    # Cosmétique
    quality_label = fields.Char(string='Qualité', compute='_compute_quality_label')
    color_class = fields.Char(string='Classe couleur', compute='_compute_quality_label')

    @api.depends('score')
    def _compute_quality_label(self):
        for rec in self:
            s = rec.score or 0
            if s >= 90:
                rec.quality_label = 'Excellent'
                rec.color_class = 'success'
            elif s >= 70:
                rec.quality_label = 'Bon'
                rec.color_class = 'info'
            elif s >= 50:
                rec.quality_label = 'Moyen'
                rec.color_class = 'warning'
            else:
                rec.quality_label = 'Faible'
                rec.color_class = 'danger'

    # --- Actions ---

    def action_set_main(self):
        """Définit comme image principale. Démet les autres candidats main du même produit."""
        for rec in self:
            others = self.search([
                ('product_id', '=', rec.product_id.id),
                ('state', '=', 'main'),
                ('id', '!=', rec.id),
            ])
            others.write({'state': 'pending'})
            rec.state = 'main'
            rec.apply_to_product()
        return True

    def action_set_gallery(self):
        for rec in self:
            rec.state = 'gallery'
            rec.apply_to_product()
        return True

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
        return True

    def action_reset_pending(self):
        for rec in self:
            rec.state = 'pending'
            rec.applied = False
            rec.applied_date = False
        return True

    def action_remove_bg_again(self):
        """Relance le background removal sur l'image brute."""
        from ..services.image_processor import ImageProcessor
        processor = ImageProcessor(enable_bg_removal=True, enable_webp=True, max_size=1200)
        for rec in self:
            if not rec.image_raw:
                continue
            raw_bytes = base64.b64decode(rec.image_raw)
            result = processor.process(raw_bytes)
            if result:
                rec.write({
                    'image_main': result.get('image_processed'),
                    'image_thumb': result.get('image_thumb'),
                    'image_no_bg': result.get('image_no_bg'),
                })
        return True

    def apply_to_product(self):
        """Pousse l'image sur le product.template selon le state."""
        ProductImage = self.env['product.image']
        for rec in self:
            if rec.state == 'main':
                # Image principale du produit
                rec.product_id.image_1920 = rec.image_main or rec.image_raw
            elif rec.state == 'gallery':
                # Ajoute en galerie via product.image
                ProductImage.create({
                    'product_tmpl_id': rec.product_id.id,
                    'name': f"{rec.product_id.name} - {rec.source_name}",
                    'image_1920': rec.image_main or rec.image_raw,
                })
            else:
                continue
            rec.applied = True
            rec.applied_date = fields.Datetime.now()
        return True
