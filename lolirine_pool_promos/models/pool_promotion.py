from odoo import models, fields, api


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
        string='Texte remise',
        help='Ex: -20%, Offre speciale, 2+1 gratuit...',
    )
    banner_color = fields.Char(
        string='Couleur de fond',
        default='#0369a1',
        help='Couleur hex du bandeau, ex: #0369a1',
    )
    button_text = fields.Char(string='Texte du bouton', default='En profiter')
    button_url = fields.Char(string='Lien du bouton', default='/shop/promotions')
    product_ids = fields.Many2many(
        'product.template',
        'pool_promo_product_rel',
        'promo_id', 'product_id',
        string='Produits en promotion',
    )
    product_count = fields.Integer(
        string='Nb produits',
        compute='_compute_product_count',
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

    @api.depends('product_ids')
    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.product_ids)

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
        return {
            'type': 'ir.actions.act_window',
            'name': 'Produits en promotion',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.product_ids.ids)],
        }
