# -*- coding: utf-8 -*-
import base64
import csv
import io
import json
import logging
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PoolImportWizard(models.TransientModel):
    """Assistant d'import de produits piscine"""
    _name = 'pool.import.wizard'
    _description = 'Assistant import produits piscine'

    supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur',
        required=True
    )
    
    import_method = fields.Selection([
        ('csv', 'Import CSV/Excel'),
        ('api', 'API REST'),
        ('ocr', 'OCR (catalogue PDF)'),
        ('manual', 'Saisie manuelle'),
    ], string='Méthode d\'import', required=True, default='csv')
    
    # === CSV Import ===
    csv_file = fields.Binary(string='Fichier CSV/Excel')
    csv_filename = fields.Char(string='Nom du fichier')
    csv_delimiter = fields.Selection([
        (',', 'Virgule (,)'),
        (';', 'Point-virgule (;)'),
        ('\t', 'Tabulation'),
        ('|', 'Pipe (|)'),
    ], string='Délimiteur', default=';')
    csv_encoding = fields.Selection([
        ('utf-8', 'UTF-8'),
        ('latin-1', 'Latin-1 (ISO-8859-1)'),
        ('cp1252', 'Windows-1252'),
    ], string='Encodage', default='utf-8')
    csv_skip_header = fields.Boolean(string='Ignorer la première ligne', default=True)
    
    # === API Import ===
    api_endpoint = fields.Char(
        string='Endpoint API',
        related='supplier_id.api_endpoint',
        readonly=False
    )
    api_params = fields.Text(
        string='Paramètres API (JSON)',
        default='{}'
    )
    
    # === OCR Import ===
    pdf_file = fields.Binary(string='Fichier PDF')
    pdf_filename = fields.Char(string='Nom du fichier PDF')
    ocr_pages = fields.Char(
        string='Pages à scanner',
        default='all',
        help="'all' ou plage (ex: 1-10, 15, 20-25)"
    )
    
    # === Options communes ===
    update_existing = fields.Boolean(
        string='Mettre à jour les produits existants',
        default=True
    )
    create_category = fields.Boolean(
        string='Créer les catégories manquantes',
        default=True
    )
    import_images = fields.Boolean(
        string='Importer les images',
        default=True
    )
    test_mode = fields.Boolean(
        string='Mode test (sans créer)',
        default=False,
        help="Analyser le fichier sans créer de produits"
    )
    
    # === Preview ===
    preview_html = fields.Html(
        string='Aperçu',
        compute='_compute_preview',
        sanitize=False
    )
    
    # Mapping dynamique
    mapping_ids = fields.One2many(
        'pool.import.wizard.mapping',
        'wizard_id',
        string='Mapping des colonnes'
    )
    
    detected_columns = fields.Text(string='Colonnes détectées')
    
    @api.depends('csv_file', 'csv_delimiter', 'csv_encoding', 'csv_skip_header')
    def _compute_preview(self):
        for wizard in self:
            if not wizard.csv_file:
                wizard.preview_html = '<p class="text-muted">Chargez un fichier pour voir l\'aperçu</p>'
                continue
            
            try:
                wizard.preview_html = wizard._generate_csv_preview()
            except Exception as e:
                wizard.preview_html = f'<p class="text-danger">Erreur: {e}</p>'
    
    def _generate_csv_preview(self):
        """Générer un aperçu HTML du CSV"""
        content = base64.b64decode(self.csv_file)
        try:
            text = content.decode(self.csv_encoding)
        except UnicodeDecodeError:
            text = content.decode('latin-1')
        
        reader = csv.reader(io.StringIO(text), delimiter=self.csv_delimiter or ';')
        rows = list(reader)[:6]  # Max 5 lignes + header
        
        if not rows:
            return '<p class="text-warning">Fichier vide</p>'
        
        # Détecter les colonnes
        headers = rows[0] if rows else []
        self.detected_columns = json.dumps(headers)
        
        # Créer le mapping automatique si vide
        if not self.mapping_ids and headers:
            self._auto_create_mapping(headers)
        
        # Générer HTML
        html = ['<table class="table table-sm table-bordered">']
        
        for i, row in enumerate(rows):
            if i == 0:
                html.append('<thead class="table-dark"><tr>')
                for cell in row:
                    html.append(f'<th>{cell}</th>')
                html.append('</tr></thead><tbody>')
            else:
                html.append('<tr>')
                for cell in row:
                    html.append(f'<td>{cell[:50]}{"..." if len(cell) > 50 else ""}</td>')
                html.append('</tr>')
        
        html.append('</tbody></table>')
        html.append(f'<p class="text-muted">Affichage des {len(rows)-1} premières lignes</p>')
        
        return ''.join(html)
    
    def _auto_create_mapping(self, headers):
        """Créer automatiquement le mapping basé sur les noms de colonnes"""
        # Mapping intelligent basé sur les noms courants
        auto_mapping = {
            # Référence
            'ref': 'supplier_code', 'reference': 'supplier_code', 'sku': 'supplier_code',
            'code': 'supplier_code', 'ref_fournisseur': 'supplier_code',
            'product_code': 'supplier_code', 'article': 'supplier_code',
            # Nom
            'name': 'name', 'nom': 'name', 'designation': 'name',
            'description': 'name', 'libelle': 'name', 'product_name': 'name',
            'titre': 'name', 'title': 'name',
            # Prix
            'price': 'standard_price', 'prix': 'standard_price', 'cost': 'standard_price',
            'prix_achat': 'standard_price', 'purchase_price': 'standard_price',
            'prix_vente': 'list_price', 'sale_price': 'list_price', 'pvp': 'list_price',
            # EAN
            'ean': 'barcode', 'ean13': 'barcode', 'barcode': 'barcode',
            'gtin': 'barcode', 'code_barre': 'barcode',
            # Catégorie
            'category': 'categ_id', 'categorie': 'categ_id', 'famille': 'categ_id',
            # Image
            'image': 'image_url', 'image_url': 'image_url', 'photo': 'image_url',
            'picture': 'image_url',
            # Marque
            'brand': 'brand', 'marque': 'brand', 'manufacturer': 'brand',
            # Poids
            'weight': 'weight', 'poids': 'weight',
        }
        
        mapping_vals = []
        for i, header in enumerate(headers):
            header_lower = header.lower().strip().replace(' ', '_')
            target = auto_mapping.get(header_lower, 'ignore')
            
            mapping_vals.append({
                'wizard_id': self.id,
                'sequence': i,
                'source_column': header,
                'target_field': target,
            })
        
        self.mapping_ids = [(0, 0, vals) for vals in mapping_vals]
    
    def action_detect_columns(self):
        """Détecter et afficher les colonnes du fichier"""
        self.ensure_one()
        if not self.csv_file:
            raise UserError(_("Veuillez d'abord charger un fichier."))
        
        # Force recalcul de l'aperçu
        self._compute_preview()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Colonnes détectées'),
                'message': _('Le mapping a été créé automatiquement. Vérifiez et ajustez si nécessaire.'),
                'type': 'success',
            }
        }
    
    def action_test_import(self):
        """Tester l'import sans créer de produits"""
        self.ensure_one()
        self.test_mode = True
        return self.action_import()
    
    def action_import(self):
        """Lancer l'import"""
        self.ensure_one()
        
        if self.import_method == 'csv':
            return self._import_csv()
        elif self.import_method == 'api':
            return self._import_api()
        elif self.import_method == 'ocr':
            return self._import_ocr()
        else:
            raise UserError(_("Méthode d'import non supportée."))
    
    def _import_csv(self):
        """Import depuis fichier CSV"""
        if not self.csv_file:
            raise UserError(_("Veuillez charger un fichier CSV."))
        
        # Créer le log d'import
        import_log = self.env['pool.import.log'].create({
            'supplier_id': self.supplier_id.id,
            'import_method': 'csv',
            'import_file': self.csv_file,
            'import_filename': self.csv_filename,
            'update_existing': self.update_existing,
            'create_category': self.create_category,
            'import_images': self.import_images,
            'start_date': datetime.now(),
            'state': 'processing',
        })
        
        try:
            # Décoder le fichier
            content = base64.b64decode(self.csv_file)
            try:
                text = content.decode(self.csv_encoding)
            except UnicodeDecodeError:
                text = content.decode('latin-1')
            
            # Parser CSV
            reader = csv.DictReader(
                io.StringIO(text),
                delimiter=self.csv_delimiter or ';'
            )
            
            rows = list(reader)
            import_log.total_lines = len(rows)
            import_log._add_log(f"Fichier chargé: {len(rows)} lignes")
            
            # Construire le mapping
            mapping = {m.source_column: m.target_field 
                      for m in self.mapping_ids 
                      if m.target_field != 'ignore'}
            
            # Créer les lignes d'import
            for i, row in enumerate(rows):
                line_data = self._map_csv_row(row, mapping)
                
                if self.test_mode:
                    import_log._add_log(f"Ligne {i+1}: {line_data.get('product_name', 'N/A')}")
                    continue
                
                self.env['pool.product.import'].create({
                    'import_log_id': import_log.id,
                    'supplier_id': self.supplier_id.id,
                    'raw_data': json.dumps(row),
                    **line_data
                })
            
            if not self.test_mode:
                # Traiter les lignes
                for line in import_log.line_ids:
                    line.action_process()
            
            # Finaliser
            import_log.write({
                'end_date': datetime.now(),
                'state': 'done' if not self.test_mode else 'draft',
            })
            import_log._update_counts()
            import_log._add_log(f"Import terminé: {import_log.created_count} créés, "
                               f"{import_log.updated_count} mis à jour, "
                               f"{import_log.error_count} erreurs")
            
            # Mettre à jour date dernier import
            self.supplier_id.last_import_date = datetime.now()
            
        except Exception as e:
            import_log.write({
                'state': 'error',
                'end_date': datetime.now(),
            })
            import_log._add_log(f"Erreur: {str(e)}", 'error')
            raise
        
        # Ouvrir le log
        return {
            'type': 'ir.actions.act_window',
            'name': f'Import {import_log.name}',
            'res_model': 'pool.import.log',
            'res_id': import_log.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _map_csv_row(self, row, mapping):
        """Mapper une ligne CSV vers les champs d'import"""
        data = {}
        
        field_to_import = {
            'supplier_code': 'supplier_code',
            'name': 'product_name',
            'description': 'product_description',
            'barcode': 'ean_code',
            'standard_price': 'cost_price',
            'list_price': 'sale_price',
            'categ_id': 'category_name',
            'brand': 'brand',
            'image_url': 'image_url',
            'weight': 'weight',
        }
        
        for source, target in mapping.items():
            if source in row and target in field_to_import:
                value = row[source]
                import_field = field_to_import[target]
                
                # Conversion de type si nécessaire
                if import_field in ('cost_price', 'sale_price', 'weight'):
                    try:
                        # Gérer les formats FR (virgule décimale)
                        value = value.replace(',', '.').replace(' ', '')
                        value = float(value) if value else 0.0
                    except ValueError:
                        value = 0.0
                
                data[import_field] = value
        
        return data
    
    def _import_api(self):
        """Import via API (à implémenter selon fournisseur)"""
        raise UserError(_(
            "L'import API pour %s n'est pas encore implémenté.\n"
            "Contactez le développeur pour l'intégration."
        ) % self.supplier_id.name)
    
    def _import_ocr(self):
        """Import via OCR de PDF (à implémenter)"""
        raise UserError(_(
            "L'import OCR n'est pas encore implémenté.\n"
            "Utilisez l'import CSV pour le moment."
        ))


class PoolImportWizardMapping(models.TransientModel):
    """Mapping des colonnes pour l'import"""
    _name = 'pool.import.wizard.mapping'
    _description = 'Mapping colonnes import'
    _order = 'sequence'

    wizard_id = fields.Many2one(
        'pool.import.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)
    
    source_column = fields.Char(string='Colonne source', required=True)
    
    target_field = fields.Selection([
        ('supplier_code', 'Réf. fournisseur'),
        ('name', 'Nom du produit'),
        ('description', 'Description'),
        ('barcode', 'Code EAN'),
        ('standard_price', 'Prix d\'achat'),
        ('list_price', 'Prix de vente'),
        ('categ_id', 'Catégorie'),
        ('brand', 'Marque'),
        ('image_url', 'URL image'),
        ('weight', 'Poids'),
        ('ignore', '-- Ignorer --'),
    ], string='Champ cible', default='ignore', required=True)
    
    sample_value = fields.Char(string='Exemple', readonly=True)
