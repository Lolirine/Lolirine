from odoo import models, fields, api


class PoolImportLog(models.Model):
    _name = 'pool.import.log'
    _description = "Journal d'import Piscine"
    _order = 'create_date desc'

    name = fields.Char(string='Référence', required=True, default='/')
    supplier_id = fields.Many2one('pool.supplier', string='Fournisseur', required=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('processing', 'En cours'),
        ('done', 'Terminé'),
        ('error', 'Erreur'),
    ], string='État', default='draft')
    
    # Statistiques
    total_lines = fields.Integer(string='Lignes totales')
    products_created = fields.Integer(string='Produits créés')
    products_updated = fields.Integer(string='Produits mis à jour')
    products_skipped = fields.Integer(string='Produits ignorés')
    templates_created = fields.Integer(string='Templates créés')
    variants_created = fields.Integer(string='Variantes créées')
    errors_count = fields.Integer(string='Erreurs')
    
    # Données
    import_file = fields.Binary(string='Fichier importé')
    import_filename = fields.Char(string='Nom du fichier')
    import_type = fields.Selection([
        ('json', 'JSON (Export complet)'),
        ('csv_products', 'CSV Produits simples'),
        ('csv_templates', 'CSV Templates'),
    ], string="Type d'import")
    
    # Logs détaillés
    log_line_ids = fields.One2many('pool.import.log.line', 'log_id', string='Détails')
    error_message = fields.Text(string='Message d\'erreur')
    
    # Dates
    start_date = fields.Datetime(string='Début')
    end_date = fields.Datetime(string='Fin')
    duration = fields.Float(string='Durée (s)', compute='_compute_duration')
    
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for log in self:
            if log.start_date and log.end_date:
                delta = log.end_date - log.start_date
                log.duration = delta.total_seconds()
            else:
                log.duration = 0
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('pool.import.log') or '/'
        return super().create(vals_list)
    
    def action_view_created_products(self):
        self.ensure_one()
        product_ids = self.log_line_ids.filtered(
            lambda l: l.action == 'create' and l.product_id
        ).mapped('product_id').ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Produits créés',
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', product_ids)],
        }


class PoolImportLogLine(models.Model):
    _name = 'pool.import.log.line'
    _description = "Ligne de journal d'import"
    _order = 'sequence, id'

    log_id = fields.Many2one('pool.import.log', string='Import', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    
    supplier_ref = fields.Char(string='Réf. Fournisseur')
    product_name = fields.Char(string='Nom Produit')
    product_id = fields.Many2one('product.template', string='Produit Odoo')
    
    action = fields.Selection([
        ('create', 'Créé'),
        ('update', 'Mis à jour'),
        ('skip', 'Ignoré'),
        ('error', 'Erreur'),
    ], string='Action')
    
    message = fields.Text(string='Message')
    raw_data = fields.Text(string='Données brutes')
