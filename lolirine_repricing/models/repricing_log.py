from odoo import models, fields


class RepricingLog(models.Model):
    _name = 'lolirine.repricing.log'
    _description = 'Log de repricing Pool Store'
    _order = 'create_date desc'

    name = fields.Char(string='Session', required=True)
    create_date = fields.Datetime(string='Date', readonly=True)
    product_id = fields.Many2one('product.template', string='Produit', ondelete='set null')
    ref = fields.Char(string='Référence interne')
    prix_actuel = fields.Float(string='Prix avant', digits=(16, 2))
    cout = fields.Float(string='Coût', digits=(16, 2))
    floor_price = fields.Float(string='Plancher marge', digits=(16, 2))
    meilleur_concurrent = fields.Float(string='Meilleur concurrent', digits=(16, 2))
    marche_gagnant = fields.Char(string='Marché')
    nouveau_prix = fields.Float(string='Nouveau prix', digits=(16, 2))
    variation = fields.Float(string='Variation €', digits=(16, 2),
                             compute='_compute_variation', store=True)
    statut = fields.Selection([
        ('updated',        '✅ Mis à jour'),
        ('initialized',    '🆕 Initialisé (prix marché)'),
        ('floor',          '🔒 Plancher marge (concurrent bas)'),
        ('floor_fallback', '⚠️  Plancher marge (aucun concurrent)'),
        ('no_competitor',  '➡️  Inchangé (aucun concurrent)'),
        ('no_data',        '❓ Sans données'),
        ('skipped',        '⏭️  Ignoré'),
    ], string='Statut')
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
    )
    note = fields.Char(string='Note')

    def _compute_variation(self):
        for rec in self:
            if rec.nouveau_prix and rec.prix_actuel is not None:
                rec.variation = rec.nouveau_prix - rec.prix_actuel
            else:
                rec.variation = 0.0
