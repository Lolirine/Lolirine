from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PoolPromotion(models.Model):
    _name = 'pool.promotion'
    _description = 'Promotion Pool Store'
    _order = 'sequence, date_start desc, id desc'

    name = fields.Char(string='Titre', required=True)
    subtitle = fields.Char(string='Sous-titre')
    description = fields.Html(string='Description', sanitize_style=True)
    date_start = fields.Date(string='Date de debut', required=True, default=fields.Date.today)
    date_end = fields.Date(string='Date de fin', required=True)
    active = fields.Boolean(string='Actif', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    discount_text = fields.Char(
        string='Texte remise global',
        help='Ex: -20%, Offre speciale, 2+1 gratuit...',
    )
    banner_color = fields.Char(
        string='Couleur de fond',
        default='#0369a1',
        help='Couleur hex du bandeau',
    )
    button_text = fields.Char(string='Texte du bouton', default='En profiter')
    button_url = fields.Char(string='Lien du bouton', default='/shop/promotions')

    # Lines (replaces old many2many)
    line_ids = fields.One2many(
        'pool.promotion.line', 'promotion_id',
        string='Produits en promotion',
    )
    product_count = fields.Integer(
        string='Nb produits',
        compute='_compute_product_count',
    )

    # Ribbon default
    default_ribbon_id = fields.Many2one(
        'product.ribbon', string='Etiquette par defaut',
        help='Etiquette appliquee par defaut aux nouveaux produits ajoutes',
    )

    website_id = fields.Many2one(
        'website', string='Site web',
        default=lambda self: self.env['website'].search([('name', 'ilike', 'Pool')], limit=1),
        help='Laisser vide pour afficher sur tous les sites',
    )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'En cours'),
        ('expired', 'Expiree'),
    ], string='Statut', compute='_compute_state', store=True)

    @api.depends('line_ids')
    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.line_ids)

    @api.depends('date_start', 'date_end', 'active')
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.active:
                rec.state = 'draft'
            elif rec.date_start and rec.date_end:
                if rec.date_start <= today <= rec.date_end:
                    rec.state = 'active'
                elif today > rec.date_end:
                    rec.state = 'expired'
                else:
                    rec.state = 'draft'
            else:
                rec.state = 'draft'

    def action_view_products(self):
        self.ensure_one()
        product_ids = self.line_ids.mapped('product_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Produits en promotion',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', product_ids)],
        }

    def action_apply_ribbons(self):
        """Apply ribbons to all products in this promotion."""
        count = 0
        for rec in self:
            for line in rec.line_ids.filtered(lambda l: l.apply_ribbon and l.product_id):
                ribbon = line.ribbon_id or rec.default_ribbon_id
                if ribbon:
                    line.product_id.website_ribbon_id = ribbon.id
                    count += 1
        return True

    def action_remove_ribbons(self):
        """Remove ribbons from all products in this promotion."""
        for rec in self:
            for line in rec.line_ids:
                if line.product_id:
                    line.product_id.website_ribbon_id = False
        return True

    @api.model
    def _cron_manage_ribbons(self):
        """Cron: auto-apply ribbons on active promos, remove from expired."""
        today = fields.Date.today()
        # Apply ribbons for promos becoming active today
        starting = self.search([
            ('active', '=', True),
            ('date_start', '=', today),
        ])
        for promo in starting:
            promo.action_apply_ribbons()
            _logger.info('Ribbons applied for promo: %s', promo.name)

        # Remove ribbons for promos that ended yesterday
        from datetime import timedelta
        yesterday = today - timedelta(days=1)
        ended = self.search([
            ('active', '=', True),
            ('date_end', '=', yesterday),
        ])
        for promo in ended:
            promo.action_remove_ribbons()
            _logger.info('Ribbons removed for expired promo: %s', promo.name)
