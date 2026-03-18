# -*- coding: utf-8 -*-
"""
pool_catalog_pdf_parser.py
==========================
Parseur PDF pour le catalogue Fluidra Benelux (sibo.nl).

Remplace l'extraction OCR par image pour les catalogues FlippingBook
dont les pages PDF sont accessibles publiquement.

URL pattern :
  https://sibo.nl/catalogus/2026/fr-be/files/assets/common/downloads/page{NNNN}.pdf?uni={GUID}

Workflow :
  1. Télécharger chaque page PDF (requests)
  2. Extraire le texte brut (pdfplumber)
  3. Envoyer le texte à Claude API (text, pas image)  ← 50x moins cher
  4. Créer les enregistrements pool.catalog.extraction.product
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import json
import logging
import re
import time

import requests

_logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# CONSTANTES
# ──────────────────────────────────────────────────────────────
SIBO_BASE     = "https://sibo.nl/catalogus/2026/fr-be/files/assets/common/downloads"
SIBO_GUID     = "d4b7c88f886254817cb42e30be3dbd40"
TOTAL_PAGES   = 582
DELAY_SEC     = 0.5   # pause entre pages pour ne pas surcharger sibo.nl
HTTP_HEADERS  = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/pdf,*/*',
    'Referer': 'https://sibo.nl/catalogus/2026/fr-be/18/',
}

# Prompt Claude pour extraction structurée depuis texte
CLAUDE_TEXT_PROMPT = """Tu reçois le texte extrait d'une page du catalogue Fluidra Benelux 2026.

Extrais TOUS les produits avec leurs informations dans le JSON suivant.
Chaque ligne du tableau TYPE/RÉF./EURO correspond à un produit.

RÈGLES PRIX :
- Format européen : €1.199,00 → 1199.00  (le point est séparateur de milliers, la virgule est le décimal)
- €42,05 → 42.05
- Ne jamais mettre purchase_price à 0 si un prix est visible

RÈGLES RÉFÉRENCES :
- La référence (RÉF.) est le code alphanumérique après le nom (ex: WR000199, R0863500, AA808)
- Le "CODE" en haut de page (ex: 45/955) est le code catalogue, pas la référence produit

RÈGLES NOM :
- Le nom du produit est ce qui précède la référence dans la ligne du tableau
- Nettoie les textes parasites (légendes d'images, numéros de page)

CATÉGORIES DISPONIBLES :
Robots électriques, Robots hydrauliques, Pompes de filtration, Filtres à sable,
Électrolyseurs au sel, Régulateurs pH, Projecteurs LED, Pompes à chaleur,
Raccords PVC, Tuyauterie PVC, Vannes, Accessoires piscine, Nettoyage manuel,
Couvertures à barres, Bâches à bulles, Volets roulants, Alarmes immersion,
Ampoules de remplacement, Boîtes de connexion, Skimmers, Bondes de fond,
Buses de refoulement, Liners, Membranes PVC, Échelles inox, Blocs polystyrène

Réponds UNIQUEMENT avec ce JSON (sans backticks, sans texte avant/après) :
{
  "page_title": "titre principal de la page",
  "brand": "marque détectée (Zodiac, AstralPool, CEPEX, AquaForte, etc.)",
  "category": "catégorie selon la liste",
  "products": [
    {
      "name": "nom nettoyé du produit",
      "reference": "référence fournisseur",
      "purchase_price": 0.00,
      "description_fr": "description courte si disponible"
    }
  ]
}

Si aucun produit avec prix n'est trouvé, retourne {"page_title": "...", "brand": "", "category": "", "products": []}

TEXTE DE LA PAGE :
"""


class PoolCatalogPdfParser(models.Model):
    """
    Wizard d'import PDF catalogue Fluidra Benelux.
    Accessible depuis Pool Import > Catalogue PDF Fluidra.
    """
    _name        = 'pool.catalog.pdf.parser'
    _description = 'Import PDF Catalogue Fluidra Benelux'
    _order       = 'create_date desc'

    name = fields.Char(
        string='Session',
        default=lambda self: f"Import PDF {fields.Datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )
    supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur',
        required=True,
    )
    catalog_base_url = fields.Char(
        string='URL base catalogue',
        default=SIBO_BASE,
        help="Base URL sans le nom de fichier ni le ?uni=...",
    )
    catalog_guid = fields.Char(
        string='GUID catalogue',
        default=SIBO_GUID,
        help="Paramètre uni= dans l'URL de téléchargement",
    )
    page_from = fields.Integer(string='Page début', default=1)
    page_to   = fields.Integer(string='Page fin',   default=10,
                               help="Mettre 582 pour tout le catalogue")
    dry_run   = fields.Boolean(
        string='Simulation (ne pas créer les produits)',
        default=True,
    )

    # Résultats
    state = fields.Selection([
        ('draft',   'Configuration'),
        ('running', 'En cours'),
        ('done',    'Terminé'),
        ('error',   'Erreur'),
    ], default='draft')

    pages_processed = fields.Integer(string='Pages traitées',  readonly=True)
    products_found  = fields.Integer(string='Produits trouvés', readonly=True)
    products_created= fields.Integer(string='Produits créés',   readonly=True)
    error_message   = fields.Text(string='Erreur', readonly=True)
    result_log      = fields.Text(string='Log détaillé', readonly=True)

    # ──────────────────────────────────────────────
    # ACTION PRINCIPALE
    # ──────────────────────────────────────────────
    def action_run(self):
        self.ensure_one()

        api_key = self.env['ir.config_parameter'].sudo().get_param('pool.claude_api_key')
        if not api_key:
            raise UserError(_("Clé API Claude non configurée (pool.claude_api_key)"))

        self.write({'state': 'running', 'result_log': ''})
        log_lines = []
        total_products = 0
        total_created  = 0

        try:
            for page_num in range(self.page_from, self.page_to + 1):

                url = (f"{self.catalog_base_url}/page{page_num:04d}.pdf"
                       f"?uni={self.catalog_guid}")

                log_lines.append(f"\n--- Page {page_num} ---")

                # 1. Télécharger le PDF
                try:
                    pdf_content = self._download_pdf(url)
                except Exception as e:
                    log_lines.append(f"  ⚠️  Téléchargement échoué : {e}")
                    continue

                # 2. Extraire le texte
                page_text = self._extract_text(pdf_content)
                if not page_text or len(page_text.strip()) < 50:
                    log_lines.append("  ⏭️  Page vide ou non textuelle, ignorée")
                    continue

                # 3. Vérification rapide : y a-t-il des prix ?
                if not re.search(r'€[\d.,]+', page_text):
                    log_lines.append("  ⏭️  Pas de prix détecté, ignorée")
                    continue

                # 4. Extraction structurée via Claude
                data = self._extract_with_claude(page_text, api_key)
                if not data or not data.get('products'):
                    log_lines.append("  ⏭️  Aucun produit extrait par Claude")
                    continue

                products = data['products']
                total_products += len(products)
                log_lines.append(f"  ✅ {len(products)} produit(s) | "
                                 f"{data.get('brand','')} | {data.get('category','')}")

                for p in products:
                    log_lines.append(
                        f"     {p.get('name','?')[:45]:<45} | "
                        f"{p.get('reference',''):<12} | "
                        f"{p.get('purchase_price',0):.2f}€"
                    )

                # 5. Créer/mettre à jour les produits Odoo
                if not self.dry_run:
                    created = self._import_products(data, page_num)
                    total_created += created

                self.write({
                    'pages_processed': page_num - self.page_from + 1,
                    'products_found':  total_products,
                    'products_created': total_created,
                    'result_log': '\n'.join(log_lines),
                })
                self.env.cr.commit()

                time.sleep(DELAY_SEC)

            self.write({
                'state':           'done',
                'products_found':  total_products,
                'products_created': total_created,
                'result_log':      '\n'.join(log_lines),
            })

        except Exception as e:
            _logger.exception("Erreur import PDF catalogue")
            self.write({
                'state':         'error',
                'error_message': str(e),
                'result_log':    '\n'.join(log_lines),
            })

        return {
            'type':      'ir.actions.act_window',
            'res_model': 'pool.catalog.pdf.parser',
            'res_id':    self.id,
            'view_mode': 'form',
            'target':    'current',
        }

    # ──────────────────────────────────────────────
    # TÉLÉCHARGEMENT PDF
    # ──────────────────────────────────────────────
    def _download_pdf(self, url: str) -> bytes:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=20)
        r.raise_for_status()
        if 'pdf' not in r.headers.get('Content-Type', '').lower():
            raise ValueError(f"Réponse non-PDF: {r.headers.get('Content-Type')}")
        return r.content

    # ──────────────────────────────────────────────
    # EXTRACTION TEXTE PDFPLUMBER
    # ──────────────────────────────────────────────
    @staticmethod
    def _extract_text(pdf_bytes: bytes) -> str:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                texts = []
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        texts.append(t)
                return '\n'.join(texts)
        except ImportError:
            raise UserError(_(
                "Le module Python 'pdfplumber' n'est pas installé.\n"
                "Exécute : pip install pdfplumber --break-system-packages"
            ))
        except Exception as e:
            _logger.warning(f"pdfplumber extraction error: {e}")
            return ''

    # ──────────────────────────────────────────────
    # EXTRACTION CLAUDE (TEXTE → JSON)
    # ──────────────────────────────────────────────
    def _extract_with_claude(self, page_text: str, api_key: str) -> dict:
        try:
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'Content-Type':      'application/json',
                    'x-api-key':         api_key,
                    'anthropic-version': '2023-06-01',
                },
                json={
                    'model':      'claude-haiku-4-5-20251001',  # Haiku = 5x moins cher
                    'max_tokens': 2048,
                    'messages': [{
                        'role':    'user',
                        'content': CLAUDE_TEXT_PROMPT + page_text[:4000],
                    }],
                },
                timeout=30,
            )
            response.raise_for_status()
            content = response.json()['content'][0]['text']

            # Nettoyer et parser le JSON
            content = content.strip()
            if content.startswith('```'):
                content = re.sub(r'^```\w*\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
            content = content.strip()

            return json.loads(content)

        except json.JSONDecodeError as e:
            _logger.warning(f"JSON parse error depuis Claude: {e}")
            return {}
        except Exception as e:
            _logger.warning(f"Claude API error: {e}")
            return {}

    # ──────────────────────────────────────────────
    # IMPORT PRODUITS ODOO
    # ──────────────────────────────────────────────
    def _import_products(self, data: dict, page_num: int) -> int:
        """
        Crée ou met à jour les enregistrements pool.catalog.extraction.product.
        Retourne le nombre de produits créés/mis à jour.
        """
        ProductExtract = self.env['pool.catalog.extraction.product']
        created = 0

        for p in data.get('products', []):
            ref           = (p.get('reference') or '').strip()
            name          = (p.get('name') or '').strip()
            purchase_price = float(p.get('purchase_price') or 0)

            if not name or purchase_price == 0:
                continue

            # Chercher si un produit Odoo existe déjà avec cette ref
            existing_product = False
            if ref:
                existing_product = self.env['product.template'].search([
                    '|',
                    ('default_code', '=', f"POOL-{ref}"),
                    ('x_pool_supplier_ref', '=', ref),
                ], limit=1)

            if existing_product and purchase_price > 0:
                # Mettre à jour le coût (standard_price)
                existing_product.write({'standard_price': purchase_price})
                _logger.info(f"Coût mis à jour: {existing_product.name} → {purchase_price}€")
                created += 1
                continue

            # Sinon créer une extraction pour import manuel
            # Chercher une extraction existante pour cette session
            extraction = self.env['pool.catalog.extraction'].search([
                ('name', 'like', f"PDF Page {page_num}"),
                ('supplier_id', '=', self.supplier_id.id),
            ], limit=1)

            if not extraction:
                extraction = self.env['pool.catalog.extraction'].create({
                    'supplier_id':   self.supplier_id.id,
                    'catalog_brand': data.get('brand', ''),
                    'image':         base64.b64encode(b'PDF import'),
                    'state':         'extracted',
                })
                # Renommer
                extraction.write({'name': f"PDF Page {page_num} - {data.get('page_title','')[:40]}"})

            # Créer le produit extrait
            ProductExtract.create({
                'extraction_id':  extraction.id,
                'name':           name,
                'reference':      ref,
                'brand':          data.get('brand', ''),
                'category':       data.get('category', ''),
                'description_fr': p.get('description_fr', ''),
                'purchase_price': purchase_price,
                'state':          'draft',
            })
            created += 1

        return created

    # ──────────────────────────────────────────────
    # ACTION UTILITAIRE : tester une page unique
    # ──────────────────────────────────────────────
    def action_test_page(self):
        """Teste l'extraction sur la page page_from uniquement."""
        self.ensure_one()
        page_to_orig = self.page_to
        self.page_to = self.page_from
        self.dry_run = True
        self.action_run()
        self.page_to = page_to_orig
