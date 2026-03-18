# -*- coding: utf-8 -*-
"""
pool_catalog_pdf.py
===================
Parseur PDF pour les catalogues FlippingBook (ex: Fluidra Benelux 2026).

Avantages vs OCR image :
- Texte extrait avec pdfplumber → 100% fiable, pas de flou ni d'erreur OCR
- Envoi du TEXTE à Claude (pas une image) → 10x moins de tokens, 10x moins cher
- Pages téléchargeables 1 par 1 depuis l'URL FlippingBook
- Resumable : checkpoint JSON pour reprendre en cas d'interruption

URL pattern SIBO/Fluidra :
  https://sibo.nl/catalogus/2026/fr-be/files/assets/common/downloads/page{NNNN}.pdf
  ?uni=d4b7c88f886254817cb42e30be3dbd40

GUID détecté depuis : window.FBPublication.Initial.GUID dans le HTML source.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import json
import re
import io
import logging
import requests

_logger = logging.getLogger(__name__)

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    _logger.warning("pdfplumber non installé — installer via : pip install pdfplumber")


class PoolCatalogPdfImport(models.Model):
    """
    Import de catalogue piscine depuis un FlippingBook PDF page par page.
    Chaque page PDF est téléchargée, son texte extrait, puis envoyé à Claude
    pour identifier les produits + prix.
    """
    _name = 'pool.catalog.pdf.import'
    _description = 'Import catalogue PDF FlippingBook'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Nom', required=True)
    supplier_id = fields.Many2one('pool.supplier', string='Fournisseur', required=True)

    # ── Configuration FlippingBook ──────────────────────────────────────────
    base_url = fields.Char(
        string='URL de base',
        help="Ex: https://sibo.nl/catalogus/2026/fr-be/files/assets/common/downloads",
        default='https://sibo.nl/catalogus/2026/fr-be/files/assets/common/downloads',
    )
    guid = fields.Char(
        string='GUID FlippingBook',
        help="Trouvé dans window.FBPublication.Initial.GUID du HTML source",
        default='d4b7c88f886254817cb42e30be3dbd40',
    )
    page_start = fields.Integer(string='Page de début', default=1)
    page_end   = fields.Integer(string='Page de fin',   default=582)
    page_current = fields.Integer(string='Page en cours', default=0, readonly=True)

    # ── État ────────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft',    'Brouillon'),
        ('running',  'En cours'),
        ('done',     'Terminé'),
        ('error',    'Erreur'),
    ], default='draft', tracking=True)

    # ── Résultats ───────────────────────────────────────────────────────────
    product_ids = fields.One2many(
        'pool.catalog.pdf.product',
        'import_id',
        string='Produits extraits',
    )
    product_count   = fields.Integer(compute='_compute_counts', store=True)
    imported_count  = fields.Integer(compute='_compute_counts', store=True)

    notes = fields.Text(string='Notes / Erreurs')

    @api.depends('product_ids', 'product_ids.state')
    def _compute_counts(self):
        for rec in self:
            rec.product_count  = len(rec.product_ids)
            rec.imported_count = len(rec.product_ids.filtered(lambda p: p.state == 'imported'))

    # ── Helpers URL ─────────────────────────────────────────────────────────
    def _page_url(self, page_num):
        return f"{self.base_url}/page{page_num:04d}.pdf?uni={self.guid}"

    # ── Extraction texte ────────────────────────────────────────────────────
    def _fetch_page_text(self, page_num):
        """
        Télécharge la page PDF et retourne le texte extrait.
        Retourne (texte, erreur).
        """
        if not PDFPLUMBER_AVAILABLE:
            return None, "pdfplumber non installé (pip install pdfplumber)"

        url = self._page_url(page_num)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
        }

        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 404:
                return None, f"404 – page {page_num} introuvable"
            r.raise_for_status()
        except requests.RequestException as e:
            return None, f"Erreur réseau : {e}"

        try:
            with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                texts = []
                for p in pdf.pages:
                    t = p.extract_text()
                    if t:
                        texts.append(t)
                return "\n".join(texts), None
        except Exception as e:
            return None, f"Erreur pdfplumber : {e}"

    # ── Extraction Claude (texte → JSON) ────────────────────────────────────
    def _extract_products_from_text(self, page_text, page_num):
        """
        Envoie le texte brut de la page à Claude pour en extraire les produits.
        Retourne une liste de dicts {name, ref, price, category, brand, description}.
        """
        api_key = self.env['ir.config_parameter'].sudo().get_param('pool.claude_api_key')
        if not api_key:
            raise UserError(_("Clé API Claude non configurée (pool.claude_api_key)"))

        prompt = f"""Voici le texte extrait d'une page d'un catalogue de produits de piscine (Fluidra Benelux 2026).

TEXTE DE LA PAGE {page_num} :
---
{page_text[:6000]}
---

Extrais TOUS les produits avec leur prix de la colonne "EURO".
Règles :
- Chaque ligne du tableau TYPE | RÉF. | EURO correspond à un produit
- Le prix est toujours dans la colonne EURO (format €1.199,00 ou €42,05)
- Convertis les prix en float : €1.199,00 → 1199.0, €42,05 → 42.05
- Ignore les lignes sans prix (titres, descriptions, specs techniques)
- Le nom du produit peut être précédé de texte parasite (légendes de photos) — prends uniquement le vrai nom du produit
- La catégorie est le grand titre en haut de page (ex: ROBOTS DE PISCINE, POMPES, FILTRATION...)
- La marque est détectée depuis le texte (ex: ZODIAC, ASTRALPOOL, CEPEX, AQUAFORTE...)

Réponds UNIQUEMENT avec un JSON valide, sans markdown :
{{
  "page": {page_num},
  "category": "catégorie principale de la page",
  "brand": "marque principale si identifiable",
  "products": [
    {{
      "name": "nom complet du produit",
      "ref": "référence fournisseur (ex: WR000199)",
      "price": 1199.0,
      "description": "description courte si présente dans le texte"
    }}
  ]
}}

Si aucun produit avec prix n'est trouvé, retourne {{"page": {page_num}, "products": []}}"""

        try:
            r = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                },
                json={
                    'model': 'claude-haiku-4-5-20251001',  # Haiku = rapide + économique pour extraction structurée
                    'max_tokens': 4096,
                    'messages': [{'role': 'user', 'content': prompt}],
                },
                timeout=30,
            )
            r.raise_for_status()
            raw = r.json().get('content', [{}])[0].get('text', '{}')

            # Nettoyer les éventuels backticks
            raw = raw.strip()
            if raw.startswith('```'):
                raw = re.sub(r'^```(?:json)?\n?', '', raw)
                raw = re.sub(r'\n?```$', '', raw)

            return json.loads(raw)

        except json.JSONDecodeError as e:
            _logger.warning(f"JSON invalide page {page_num}: {e}")
            return {'page': page_num, 'products': []}
        except Exception as e:
            _logger.error(f"Erreur Claude page {page_num}: {e}")
            return {'page': page_num, 'products': []}

    # ── Action : traiter une page ────────────────────────────────────────────
    def action_process_page(self):
        """Traite la page courante (page_current) et incrémente."""
        self.ensure_one()
        page = self.page_current or self.page_start
        self._process_single_page(page)
        self.page_current = page + 1
        if self.page_current > self.page_end:
            self.state = 'done'

    def _process_single_page(self, page_num):
        self.ensure_one()
        _logger.info(f"PDF import — page {page_num}")

        text, err = self._fetch_page_text(page_num)
        if err:
            _logger.warning(f"Page {page_num}: {err}")
            return

        if not text or len(text.strip()) < 50:
            _logger.info(f"Page {page_num}: texte vide ou trop court, ignorée")
            return

        data = self._extract_products_from_text(text, page_num)
        products = data.get('products', [])
        category = data.get('category', '')
        brand    = data.get('brand', '')

        for p in products:
            if not p.get('ref') or not p.get('price'):
                continue
            # Vérifier si déjà extrait
            existing = self.product_ids.filtered(lambda x: x.ref == p['ref'])
            if existing:
                continue

            self.env['pool.catalog.pdf.product'].create({
                'import_id':   self.id,
                'supplier_id': self.supplier_id.id,
                'page_num':    page_num,
                'name':        p.get('name', ''),
                'ref':         p['ref'],
                'price':       float(p.get('price', 0)),
                'category':    category or p.get('category', ''),
                'brand':       brand or p.get('brand', ''),
                'description': p.get('description', ''),
            })

        _logger.info(f"Page {page_num}: {len(products)} produits extraits")

    # ── Action : lancer l'import complet (limité à 50 pages par appel) ───────
    def action_run_import(self):
        """
        Lance l'import de 50 pages à partir de page_current.
        À appeler plusieurs fois pour traiter tout le catalogue.
        """
        self.ensure_one()
        self.state = 'running'

        start = self.page_current or self.page_start
        end   = min(start + 49, self.page_end)

        errors = []
        for page_num in range(start, end + 1):
            try:
                self._process_single_page(page_num)
                self.page_current = page_num + 1
                # Commit intermédiaire toutes les 10 pages
                if page_num % 10 == 0:
                    self.env.cr.commit()
            except Exception as e:
                errors.append(f"Page {page_num}: {str(e)[:100]}")
                _logger.error(f"Erreur page {page_num}: {e}")

        if self.page_current > self.page_end:
            self.state = 'done'
        else:
            self.state = 'draft'  # Prêt pour le prochain batch

        if errors:
            self.notes = "\n".join(errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import PDF'),
                'message': _(
                    '%d produits extraits | Pages %d→%d | %d erreur(s)'
                ) % (len(self.product_ids), start, end, len(errors)),
                'type': 'success' if not errors else 'warning',
                'sticky': bool(errors),
            }
        }

    # ── Action : upload PDF manuel ───────────────────────────────────────────
    def action_process_uploaded_pdf(self, pdf_base64, page_hint=None):
        """
        Traite un PDF uploadé manuellement (ex: page téléchargée depuis Safari).
        Utilisable depuis le wizard ou le JS du module existant.
        """
        self.ensure_one()
        if not PDFPLUMBER_AVAILABLE:
            raise UserError(_("pdfplumber non installé. Exécuter : pip install pdfplumber"))

        try:
            pdf_bytes = base64.b64decode(pdf_base64)
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                texts = []
                for p in pdf.pages:
                    t = p.extract_text()
                    if t:
                        texts.append(t)
            full_text = "\n".join(texts)
        except Exception as e:
            raise UserError(_("Erreur lecture PDF : %s") % str(e))

        if not full_text.strip():
            raise UserError(_("Aucun texte extractible dans ce PDF."))

        page_num = page_hint or (self.page_current or 1)
        data = self._extract_products_from_text(full_text, page_num)
        products = data.get('products', [])
        category = data.get('category', '')
        brand    = data.get('brand', '')

        created = 0
        for p in products:
            if not p.get('ref') or not p.get('price'):
                continue
            self.env['pool.catalog.pdf.product'].create({
                'import_id':   self.id,
                'supplier_id': self.supplier_id.id,
                'page_num':    page_num,
                'name':        p.get('name', ''),
                'ref':         p['ref'],
                'price':       float(p.get('price', 0)),
                'category':    category,
                'brand':       brand,
                'description': p.get('description', ''),
            })
            created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('PDF traité'),
                'message': _('%d produits extraits depuis le PDF') % created,
                'type': 'success',
                'sticky': False,
            }
        }

    # ── Action : importer dans Odoo ─────────────────────────────────────────
    def action_import_to_odoo(self):
        """Importe tous les produits extraits dans les fiches Odoo."""
        self.ensure_one()
        to_import = self.product_ids.filtered(lambda p: p.state == 'to_import')
        if not to_import:
            raise UserError(_("Aucun produit à importer."))

        imported = errors = 0
        for prod in to_import:
            try:
                prod.action_import()
                imported += 1
            except Exception as e:
                prod.write({'state': 'error', 'error_message': str(e)[:200]})
                errors += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Odoo'),
                'message': _('%d importés, %d erreurs') % (imported, errors),
                'type': 'success' if not errors else 'warning',
                'sticky': bool(errors),
            }
        }

    # ── Action : update coûts uniquement ────────────────────────────────────
    def action_update_costs_only(self):
        """
        Met à jour UNIQUEMENT le coût (standard_price) des produits existants
        sans créer de nouveaux produits. Utile pour les 489 produits sans prix.
        """
        self.ensure_one()
        updated = not_found = 0

        for prod in self.product_ids.filtered(lambda p: p.price > 0):
            # Chercher le produit Odoo par référence fournisseur
            template = self.env['product.template'].search([
                '|',
                ('default_code', '=', f"POOL-{prod.ref}"),
                ('x_pool_supplier_ref', '=', prod.ref),
            ], limit=1)

            if template:
                template.write({'standard_price': prod.price})
                prod.write({'state': 'imported'})
                updated += 1
            else:
                not_found += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mise à jour coûts'),
                'message': _('%d coûts mis à jour, %d références non trouvées') % (updated, not_found),
                'type': 'success',
                'sticky': True,
            }
        }


class PoolCatalogPdfProduct(models.Model):
    """Produit extrait depuis un PDF de catalogue FlippingBook."""
    _name = 'pool.catalog.pdf.product'
    _description = 'Produit extrait PDF catalogue'
    _order = 'page_num, name'

    import_id   = fields.Many2one('pool.catalog.pdf.import', ondelete='cascade', required=True)
    supplier_id = fields.Many2one('pool.supplier', string='Fournisseur')
    page_num    = fields.Integer(string='Page PDF')

    name        = fields.Char(string='Nom produit')
    ref         = fields.Char(string='Référence', index=True)
    price       = fields.Float(string='Prix catalogue HT', digits=(16, 2))
    category    = fields.Char(string='Catégorie')
    brand       = fields.Char(string='Marque')
    description = fields.Text(string='Description')

    # Prix net après remise fournisseur
    price_net   = fields.Float(
        string='Prix achat NET',
        compute='_compute_price_net',
        store=False,
    )

    state = fields.Selection([
        ('to_import', 'À importer'),
        ('imported',  'Importé'),
        ('skipped',   'Ignoré'),
        ('error',     'Erreur'),
    ], default='to_import')

    product_id    = fields.Many2one('product.template', string='Produit Odoo', ondelete='set null')
    error_message = fields.Char(string='Erreur')

    @api.depends('price', 'supplier_id', 'category')
    def _compute_price_net(self):
        for rec in self:
            supplier = rec.supplier_id
            if (supplier and hasattr(supplier, 'discount_ids')
                    and supplier.discount_ids and rec.price > 0):
                info = supplier.calculate_prices(
                    catalog_price=rec.price,
                    category_name=rec.category,
                )
                rec.price_net = info['purchase_price']
            else:
                rec.price_net = rec.price

    def action_import(self):
        """Importe ce produit dans Odoo (met à jour le coût si existant, crée sinon)."""
        self.ensure_one()
        ProductTemplate = self.env['product.template']

        # Chercher produit existant
        template = ProductTemplate.search([
            '|',
            ('default_code', '=', f"POOL-{self.ref}"),
            ('x_pool_supplier_ref', '=', self.ref),
        ], limit=1)

        price_net = self.price_net or self.price

        if template:
            # Mettre à jour le coût
            template.write({'standard_price': price_net})
            _logger.info(f"Coût mis à jour: {template.name} → {price_net}€")
        else:
            # Créer un nouveau produit minimal
            vals = {
                'name':          self.name or f"Produit {self.ref}",
                'default_code':  f"POOL-{self.ref}",
                'standard_price': price_net,
                'list_price':    0,
                'sale_ok':       True,
                'purchase_ok':   True,
            }
            if 'x_pool_supplier_ref' in ProductTemplate._fields:
                vals['x_pool_supplier_ref'] = self.ref
            if 'x_pool_brand' in ProductTemplate._fields:
                vals['x_pool_brand'] = self.brand or ''
            if 'x_pool_category' in ProductTemplate._fields:
                vals['x_pool_category'] = self.category or ''
            if self.supplier_id and 'x_pool_supplier_id' in ProductTemplate._fields:
                vals['x_pool_supplier_id'] = self.supplier_id.id
            if 'website_id' in ProductTemplate._fields:
                vals['website_id'] = 6  # Pool Store

            template = ProductTemplate.create(vals)
            _logger.info(f"Produit créé: {template.name} (coût: {price_net}€)")

        self.write({'state': 'imported', 'product_id': template.id})
        return True

    def action_skip(self):
        self.write({'state': 'skipped'})

    def action_reset(self):
        self.write({'state': 'to_import', 'error_message': False})
