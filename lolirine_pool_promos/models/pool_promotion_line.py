from odoo import models, fields, api


class PoolPromotionLine(models.Model):
    _name = 'pool.promotion.line'
    _description = 'Ligne de promotion'
    _order = 'sequence, id'

    promotion_id = fields.Many2one(
        'pool.promotion', string='Promotion',
        required=True, ondelete='cascade', index=True,
    )
    product_id = fields.Many2one(
        'product.template', string='Produit',
        required=True, ondelete='cascade',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Devise',
        default=lambda self: self.env.company.currency_id,
    )
    sequence = fields.Integer(string='Sequence', default=10)

    # Pricing
    original_price = fields.Float(
        string='Prix initial',
        compute='_compute_original_price', store=True, readonly=False,
        digits='Product Price',
    )
    discount_type = fields.Selection([
        ('percent', 'Pourcentage (%)'),
        ('fixed', 'Montant fixe (€)'),
    ], string='Type de remise', default='percent', required=True)
    discount_value = fields.Float(string='Valeur remise', digits='Product Price')
    final_price = fields.Float(
        string='Prix apres remise',
        compute='_compute_final_price', store=True,
        digits='Product Price',
    )
    savings = fields.Float(
        string='Economie',
        compute='_compute_final_price', store=True,
        digits='Product Price',
    )
    discount_display = fields.Char(
        string='Remise',
        compute='_compute_final_price', store=True,
    )

    # Ribbon / Label
    ribbon_id = fields.Many2one(
        'product.ribbon', string='Etiquette',
        help='Etiquette a afficher sur le produit dans la boutique (ex: PROMO, -20%, Offre speciale)',
    )
    apply_ribbon = fields.Boolean(
        string='Appliquer etiquette', default=True,
        help='Appliquer automatiquement cette etiquette au produit quand la promo est active',
    )

    @api.depends('product_id', 'product_id.list_price')
    def _compute_original_price(self):
        for line in self:
            if line.product_id and not line.original_price:
                line.original_price = line.product_id.list_price

    @api.depends('original_price', 'discount_type', 'discount_value')
    def _compute_final_price(self):
        for line in self:
            if line.discount_type == 'percent' and line.discount_value:
                line.savings = round(line.original_price * line.discount_value / 100.0, 2)
                line.final_price = round(line.original_price - line.savings, 2)
                line.discount_display = '-%.0f%%' % line.discount_value
            elif line.discount_type == 'fixed' and line.discount_value:
                line.savings = line.discount_value
                line.final_price = round(line.original_price - line.discount_value, 2)
                line.discount_display = '-%.2f €' % line.discount_value
            else:
                line.savings = 0.0
                line.final_price = line.original_price
                line.discount_display = ''

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.original_price = self.product_id.list_price

    def action_apply_ribbon(self):
        """Apply ribbon to linked product."""
        for line in self:
            if line.ribbon_id and line.product_id:
                line.product_id.website_ribbon_id = line.ribbon_id.id

    def action_remove_ribbon(self):
        """Remove ribbon from linked product."""
        for line in self:
            if line.product_id:
                line.product_id.website_ribbon_id = False
