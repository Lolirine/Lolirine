# -*- coding: utf-8 -*-
"""
pool_catalog_pdf.py
===================
Parseur PDF pour les catalogues FlippingBook (ex: Fluidra Benelux 2026)
et FlipDocs (ex: SCP France 2026).

Avantages vs OCR image :
- Texte extrait avec pdfplumber -> 100% fiable, pas de flou ni d'erreur OCR
- Envoi du TEXTE a Claude (pas une image) -> 10x moins de tokens, 10x moins cher
- Pages telechargeables 1 par 1 depuis l'URL FlippingBook (Fluidra)
- PDF complet uploadable manuellement (SCP FlipDocs)
- Resumable : reprend a la page courante en cas d'interruption
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
    _logger.warning("pdfplumber non installe -- installer via : pip install pdfplumber")


class PoolCatalogPdfImport(models.Model):
    """
    Import de catalogue piscine depuis un FlippingBook PDF page par page,
    ou depuis un PDF complet uploade manuellement (FlipDocs).
    """
    _name = 'pool.catalog.pdf.import'
    _description = 'Import catalogue PDF FlippingBook'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Nom', required=True)
    supplier_id = fields.Many2one('pool.supplier', string='Fournisseur', required=True)

    # -- Configuration FlippingBook (Fluidra/SIBO) ---------------------------
    base_url = fields.Char(
        string='URL de base',
        help="Ex: https://sibo.nl/catalogus/2026/fr-be/files/assets/common/downloads",
        default='https://sibo.nl/catalogus/2026/fr-be/files/assets/common/downloads',
    )
    guid = fields.Char(
        string='GUID FlippingBook',
        help="Trouve dans window.FBPublication.Initial.GUID du HTML source",
        default='d4b7c88f886254817cb42e30be3dbd40',
    )
    page_start = fields.Integer(string='Page de debut', default=1)
    page_end   = fields.Integer(string='Page de fin',   default=582)
    page_current = fields.Integer(string='Page en cours', default=0, readonly=True)

    # -- PDF uploade manuellement (ex: SCP FlipDocs) -------------------------
    source_pdf = fields.Binary(
        string='PDF du catalogue',
        attachment=True,
        help="Uploader le PDF complet du catalogue (ex: telecharge depuis FlipDocs)",
    )
    source_pdf_filename = fields.Char(string='Nom du fichier PDF')
    pages_per_chunk = fields.Integer(
        string='Pages par lot Claude',
        default=5,
        help="Nombre de pages PDF envoyees a Claude en une seule requete (5 recommande)",
    )

    # -- Etat ----------------------------------------------------------------
    state = fields.Selection([
        ('draft',    'Brouillon'),
        ('running',  'En cours'),
        ('done',     'Termine'),
        ('error',    'Erreur'),
    ], default='draft', tracking=True)

    # -- Resultats -----------------------------------------------------------
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

    # -- Helpers URL ---------------------------------------------------------
    def _page_url(self, page_num):
        return f"{self.base_url}/page{page_num:04d}.pdf?uni={self.guid}"

    # -- Extraction texte (FlippingBook) -------------------------------------
    def _fetch_page_text(self, page_num):
        """
        Telecharge la page PDF depuis l'URL FlippingBook et retourne le texte extrait.
        Retourne (texte, erreur).
        """
        if not PDFPLUMBER_AVAILABLE:
            return None, "pdfplumber non installe (pip install pdfplumber)"

        url = self._page_url(page_num)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
        }

        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 404:
                return None, f"404 - page {page_num} introuvable"
            r.raise_for_status()
        except requests.RequestException as e:
            return None, f"Erreur reseau : {e}"

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

    # -- Extraction Claude (texte -> JSON) -----------------------------------
    def _extract_products_from_text(self, page_text, page_num):
        """
        Envoie le texte brut de la page a Claude pour en extraire les produits.
        Retourne un dict {page, category, brand, products: [{name, ref, price, description}]}.
        """
        api_key = self.env['ir.config_parameter'].sudo().get_param('pool.claude_api_key')
        if not api_key:
            raise UserError(_("Cle API Claude non configuree (pool.claude_api_key)"))

        prompt = f"""Voici le texte extrait d'une ou plusieurs pages d'un catalogue de produits de piscine.

TEXTE (a partir de la page {page_num}) :
---
{page_text[:6000]}
---

Extrais TOUS les produits avec leur prix.
Regles :
- Chaque ligne du tableau REF | DESIGNATION | PRIX correspond a un produit
- Le prix peut etre dans une colonne EURO, €HT, ou similaire
- Format prix : €1.199,00 -> 1199.0 | €42,05 -> 42.05 | 4 250,00 -> 4250.0
- Ignore les lignes sans prix numerique (titres, descriptions, mentions NC)
- Le nom du produit peut etre precede de texte parasite (legendes photos) -- prends uniquement le vrai nom
- La categorie est le grand titre de section (ex: PISCINES HORS SOL, ROBOTS DE PISCINE, POMPES...)
- La marque est detectee depuis le texte (ex: ZODIAC, ASTRALPOOL, ABATEC, GARDEN LEISURE...)

Reponds UNIQUEMENT avec un JSON valide, sans markdown :
{{
  "page": {page_num},
  "category": "categorie principale",
  "brand": "marque principale si identifiable",
  "products": [
    {{
      "name": "nom complet du produit",
      "ref": "reference fournisseur (ex: ABT-750-0030 ou WR000199)",
      "price": 4250.0,
      "description": "description courte si presente"
    }}
  ]
}}

Si aucun produit avec prix numerique n'est trouve, retourne {{"page": {page_num}, "products": []}}"""

        try:
            r = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                },
                json={
                    'model': 'claude-haiku-4-5-20251001',
                    'max_tokens': 4096,
                    'messages': [{'role': 'user', 'content': prompt}],
                },
                timeout=30,
            )
            r.raise_for_status()
            raw = r.json().get('content', [{}])[0].get('text', '{}')

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

    # -- Action : traiter une seule page (FlippingBook) ----------------------
    def _process_single_page(self, page_num):
        self.ensure_one()
        _logger.info(f"PDF import -- page {page_num}")

        text, err = self._fetch_page_text(page_num)
        if err:
            _logger.warning(f"Page {page_num}: {err}")
            return

        if not text or len(text.strip()) < 50:
            _logger.info(f"Page {page_num}: texte vide ou trop court, ignoree")
            return

        data = self._extract_products_from_text(text, page_num)
        self._save_products(data, page_num)

    def _save_products(self, data, page_num):
        """Sauvegarde les produits extraits par Claude."""
        products = data.get('products', [])
        category = data.get('category', '')
        brand    = data.get('brand', '')

        for p in products:
            if not p.get('ref') or not p.get('price'):
                continue
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

    # -- Action : Importer 50 pages (FlippingBook) ---------------------------
    def action_run_import(self):
        """
        Lance l'import de 50 pages a partir de page_current.
        A appeler plusieurs fois pour traiter tout le catalogue.
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
                if page_num % 10 == 0:
                    self.env.cr.commit()
            except Exception as e:
                errors.append(f"Page {page_num}: {str(e)[:100]}")
                _logger.error(f"Erreur page {page_num}: {e}")

        if self.page_current > self.page_end:
            self.state = 'done'
        else:
            self.state = 'draft'

        if errors:
            self.notes = "\n".join(errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import PDF'),
                'message': _(
                    '%d produits extraits | Pages %d->%d | %d erreur(s)'
                ) % (len(self.product_ids), start, end, len(errors)),
                'type': 'success' if not errors else 'warning',
                'sticky': bool(errors),
            }
        }

    # -- Action : Traiter PDF uploade (SCP FlipDocs) -------------------------
    def action_run_pdf_upload(self):
        """
        Traite le PDF uploade manuellement page par page.
        Envoie des chunks de pages_per_chunk pages a Claude.
        A appeler plusieurs fois pour traiter tout le PDF.
        """
        self.ensure_one()

        if not PDFPLUMBER_AVAILABLE:
            raise UserError(_("pdfplumber non installe. Executer : pip install pdfplumber"))

        if not self.source_pdf:
            raise UserError(_("Veuillez d'abord uploader un fichier PDF."))

        try:
            pdf_bytes = base64.b64decode(self.source_pdf)
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                total_pages = len(pdf.pages)
        except Exception as e:
            raise UserError(_("Impossible de lire le PDF : %s") % str(e))

        start = self.page_current or 0
        chunk = self.pages_per_chunk or 5
        end = min(start + 49, total_pages)

        self.state = 'running'
        errors = []

        try:
            pdf_bytes = base64.b64decode(self.source_pdf)
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for chunk_start in range(start, end, chunk):
                    chunk_end = min(chunk_start + chunk, end)
                    chunk_text = []

                    for page_idx in range(chunk_start, chunk_end):
                        if page_idx >= len(pdf.pages):
                            break
                        t = pdf.pages[page_idx].extract_text()
                        if t:
                            chunk_text.append(f"--- PAGE {page_idx + 1} ---\n{t}")

                    if not chunk_text:
                        self.page_current = chunk_end
                        continue

                    full_text = "\n\n".join(chunk_text)

                    try:
                        data = self._extract_products_from_text(full_text, chunk_start + 1)
                        self._save_products(data, chunk_start + 1)
                        self.page_current = chunk_end
                        if chunk_end % 20 == 0:
                            self.env.cr.commit()
                    except Exception as e:
                        errors.append(f"Pages {chunk_start+1}-{chunk_end}: {str(e)[:100]}")
                        _logger.error(f"Erreur chunk {chunk_start}-{chunk_end}: {e}")

        except Exception as e:
            self.state = 'error'
            raise UserError(_("Erreur lecture PDF : %s") % str(e))

        if self.page_current >= total_pages:
            self.state = 'done'
        else:
            self.state = 'draft'

        if errors:
            self.notes = (self.notes or '') + "\n" + "\n".join(errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import PDF uploade'),
                'message': _(
                    '%d produits extraits | Pages %d->%d | %d erreur(s)'
                ) % (len(self.product_ids), start + 1, end, len(errors)),
                'type': 'success' if not errors else 'warning',
                'sticky': bool(errors),
            }
        }

    # -- Action : upload PDF manuel (methode legacy) -------------------------
    def action_process_uploaded_pdf(self, pdf_base64, page_hint=None):
        """Traite un PDF uploade via le wizard JS (compatibilite)."""
        self.ensure_one()
        if not PDFPLUMBER_AVAILABLE:
            raise UserError(_("pdfplumber non installe. Executer : pip install pdfplumber"))

        try:
            pdf_bytes = base64.b64decode(pdf_base64)
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                texts = [p.extract_text() for p in pdf.pages if p.extract_text()]
            full_text = "\n".join(texts)
        except Exception as e:
            raise UserError(_("Erreur lecture PDF : %s") % str(e))

        if not full_text.strip():
            raise UserError(_("Aucun texte extractible dans ce PDF."))

        page_num = page_hint or (self.page_current or 1)
        data = self._extract_products_from_text(full_text, page_num)
        self._save_products(data, page_num)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('PDF traite'),
                'message': _('%d produits extraits depuis le PDF') % len(data.get('products', [])),
                'type': 'success',
                'sticky': False,
            }
        }

    # -- Action : importer dans Odoo -----------------------------------------
    def action_import_to_odoo(self):
        """Importe tous les produits extraits dans les fiches Odoo."""
        self.ensure_one()
        to_import = self.product_ids.filtered(lambda p: p.state == 'to_import')
        if not to_import:
            raise UserError(_("Aucun produit a importer."))

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
                'message': _('%d importes, %d erreurs') % (imported, errors),
                'type': 'success' if not errors else 'warning',
                'sticky': bool(errors),
            }
        }

    # -- Action : update couts uniquement ------------------------------------
    def action_update_costs_only(self):
        """
        Met a jour UNIQUEMENT le cout (standard_price) des produits existants.
        Utile pour les produits sans prix dans la base.
        """
        self.ensure_one()
        updated = not_found = 0

        for prod in self.product_ids.filtered(lambda p: p.price > 0):
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
                'title': _('Mise a jour couts'),
                'message': _('%d couts mis a jour, %d references non trouvees') % (updated, not_found),
                'type': 'success',
                'sticky': True,
            }
        }


class PoolCatalogPdfProduct(models.Model):
    """Produit extrait depuis un PDF de catalogue FlippingBook ou FlipDocs."""
    _name = 'pool.catalog.pdf.product'
    _description = 'Produit extrait PDF catalogue'
    _order = 'page_num, name'

    import_id   = fields.Many2one('pool.catalog.pdf.import', ondelete='cascade', required=True)
    supplier_id = fields.Many2one('pool.supplier', string='Fournisseur')
    page_num    = fields.Integer(string='Page PDF')

    name        = fields.Char(string='Nom produit')
    ref         = fields.Char(string='Reference', index=True)
    price       = fields.Float(string='Prix catalogue HT', digits=(16, 2))
    category    = fields.Char(string='Categorie')
    brand       = fields.Char(string='Marque')
    description = fields.Text(string='Description')

    price_net = fields.Float(
        string='Prix achat NET',
        compute='_compute_price_net',
        store=False,
    )

    state = fields.Selection([
        ('to_import', 'A importer'),
        ('imported',  'Importe'),
        ('skipped',   'Ignore'),
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
                try:
                    info = supplier.calculate_prices(
                        catalog_price=rec.price,
                        category_name=rec.category,
                    )
                    rec.price_net = info['purchase_price']
                except Exception:
                    rec.price_net = rec.price
            else:
                rec.price_net = rec.price

    def action_import(self):
        """Importe ce produit dans Odoo (met a jour le cout si existant, cree sinon)."""
        self.ensure_one()
        ProductTemplate = self.env['product.template']

        template = ProductTemplate.search([
            '|',
            ('default_code', '=', f"POOL-{self.ref}"),
            ('x_pool_supplier_ref', '=', self.ref),
        ], limit=1)

        price_net = self.price_net or self.price

        if template:
            template.write({'standard_price': price_net})
            _logger.info(f"Cout mis a jour: {template.name} -> {price_net}EUR")
        else:
            # Prix de vente : marge fournisseur, jamais 0
            if self.supplier_id:
                selling = self.supplier_id.calculate_sale_price(price_net)
            else:
                selling = round(price_net * 1.30, 2)
            vals = {
                'name':           self.name or f"Produit {self.ref}",
                'default_code':   f"POOL-{self.ref}",
                'standard_price': price_net,
                'list_price':     round(selling, 2),
                'sale_ok':        True,
                'purchase_ok':    True,
            }
            if 'is_pool_product' in ProductTemplate._fields:
                vals['is_pool_product'] = True
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
            _logger.info(f"Produit cree: {template.name} (cout: {price_net}EUR)")

        self.write({'state': 'imported', 'product_id': template.id})
        return True

    def action_skip(self):
        self.write({'state': 'skipped'})

    def action_reset(self):
        self.write({'state': 'to_import', 'error_message': False})
