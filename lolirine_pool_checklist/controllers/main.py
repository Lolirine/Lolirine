# -*- coding: utf-8 -*-
"""
Contrôleurs pour la fiche de visite piscine.

Routes :
  GET  /visite-chantier                  → Page principale (checklist React)
  POST /pool-checklist/products          → Recherche produits catalogue website_id=6
  POST /pool-checklist/ai-suggest        → Proxy IA Anthropic (clé serveur)
  POST /pool-checklist/search-partner    → Recherche partenaires Odoo
"""

import json
import logging
import urllib.request
import urllib.error

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

POOL_STORE_WEBSITE_ID = 6


class PoolChecklistController(http.Controller):

    # ── Page principale ───────────────────────────────────────────────────

    @http.route(
        '/visite-chantier',
        type='http',
        auth='user',
        website=True,
        methods=['GET'],
        sitemap=False,
    )
    def checklist_page(self, **kwargs):
        return request.render(
            'lolirine_pool_checklist.page_checklist',
            {
                'website_id': POOL_STORE_WEBSITE_ID,
                'page_title': 'Fiche de visite chantier — Lolirine Pool Store',
            }
        )

    # ── Recherche produits ─────────────────────────────────────────────────

    @http.route(
        '/pool-checklist/products',
        type='json',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=False,
    )
    def search_products(self, query='', limit=12, **kwargs):
        if not query or len(query.strip()) < 2:
            return {'products': []}

        env = request.env
        domain = [
            ('website_published', '=', True),
            ('website_id', 'in', [False, POOL_STORE_WEBSITE_ID]),
            ('sale_ok', '=', True),
            '|',
            ('name', 'ilike', query),
            ('default_code', 'ilike', query),
        ]

        products = env['product.template'].sudo().search(domain, limit=int(limit), order='name asc')

        result = []
        for p in products:
            # Prix public HT
            price = p.list_price or 0.0
            # Fournisseur principal
            sup_info = p.seller_ids[:1] if p.seller_ids else env['product.supplierinfo']
            supplier = {}
            if sup_info:
                s = sup_info[0]
                supplier = {
                    'name': s.partner_id.name or '',
                    'ref': s.product_code or '',
                    'price': float(s.price or 0),
                }

            result.append({
                'id': p.id,
                'name': p.name,
                'ref': p.default_code or '',
                'category': p.categ_id.name if p.categ_id else '',
                'unit': p.uom_id.name if p.uom_id else 'pcs',
                'price': price,
                'suppliers': [supplier] if supplier else [],
                'url': '/web#id=%d&model=product.template' % p.id,
            })

        return {'products': result}

    # ── Proxy IA Anthropic ─────────────────────────────────────────────────

    @http.route(
        '/pool-checklist/ai-suggest',
        type='json',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=False,
    )
    def ai_suggest(self, item_text='', section_label='', **kwargs):
        """
        Appelle l'API Anthropic côté serveur pour suggérer des produits
        en fonction d'un point de checklist.
        La clé API est lue depuis ir.config_parameter → anthropic.api_key
        (ou pool.claude_api_key en fallback).
        """
        if not item_text:
            return {'products': [], 'error': 'item_text manquant'}

        # Récupérer la clé API
        ICP = request.env['ir.config_parameter'].sudo()
        api_key = (
            ICP.get_param('anthropic.api_key') or
            ICP.get_param('pool.claude_api_key') or
            ICP.get_param('lolirine_contract.anthropic_api_key') or
            ''
        )
        if not api_key:
            _logger.warning('[pool_checklist] Clé API Anthropic non configurée (ir.config_parameter)')
            return {'products': [], 'error': 'Clé API non configurée'}

        system_prompt = (
            "Tu es un expert en équipements de piscine et spa (marché belge/européen). "
            "Tu travailles pour Lolirine Pool Store. "
            "Réponds UNIQUEMENT en JSON valide, sans markdown, sans texte autour. "
            'Format : {"products":[{"name":"Nom produit","ref":"REF","category":"Catégorie",'
            '"unit":"pièce|kg|L|m|m²|lot","note":"Remarque courte","supplier":"Fluidra|SCP|HTH|BWT|Hayward|Pentair|Zodiac|Astralpool"}]} '
            "Maximum 7 produits. "
            "Donne des produits réels et concrets avec références si possible."
        )

        user_message = (
            f"Section checklist : {section_label}\n"
            f"Point de contrôle : \"{item_text}\"\n"
            "Quels produits/matériaux concrets faut-il prévoir pour ce point ?"
        )

        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 800,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            _logger.error('[pool_checklist] Anthropic HTTP %s: %s', e.code, err_body[:300])
            return {'products': [], 'error': f'Anthropic HTTP {e.code}'}
        except Exception as e:
            _logger.error('[pool_checklist] Anthropic error: %s', e)
            return {'products': [], 'error': str(e)}

        raw_text = body.get('content', [{}])[0].get('text', '{}')
        try:
            parsed = json.loads(raw_text)
            products = parsed.get('products', [])
        except json.JSONDecodeError:
            _logger.warning('[pool_checklist] JSON invalide de l\'IA: %s', raw_text[:200])
            return {'products': [], 'error': 'Réponse IA non parseable'}

        # Normaliser les produits
        result = []
        for p in products[:7]:
            if not p.get('name'):
                continue
            sup_name = p.get('supplier', '')
            result.append({
                'name': p.get('name', ''),
                'ref': p.get('ref', ''),
                'category': p.get('category', ''),
                'unit': p.get('unit', 'pièce'),
                'note': p.get('note', ''),
                'price': 0,
                'suppliers': [{'name': sup_name, 'ref': p.get('ref', ''), 'price': 0}] if sup_name else [],
            })

        return {'products': result}

    # ── Création devis ─────────────────────────────────────────────────────

    @http.route(
        '/pool-checklist/create-quote',
        type='json',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=False,
    )
    def create_quote(self, partner_id=None, partner_name='', ref_dossier='',
                     note='', lines=None, **kwargs):
        """
        Crée un devis (sale.order) Odoo depuis la fiche de visite.
        - Si partner_id fourni et valide → utilisé directement
        - Sinon → recherche par nom ou création d'un contact temporaire
        - Les lignes sans product_id sont créées comme lignes texte (type='note' ou product virtuel)
        """
        env = request.env
        SaleOrder = env['sale.order'].sudo()
        SaleOrderLine = env['sale.order.line'].sudo()
        Partner = env['res.partner'].sudo()
        Product = env['product.product'].sudo()

        if not lines:
            return {'error': 'Aucune ligne fournie'}

        # ── Résolution partenaire ──
        partner = None
        if partner_id:
            try:
                partner = Partner.browse(int(partner_id))
                if not partner.exists():
                    partner = None
            except Exception:
                partner = None

        if not partner and partner_name:
            found = Partner.search([('name', 'ilike', partner_name.strip()), ('type', '=', 'contact')], limit=1)
            partner = found or None

        if not partner:
            # Créer un contact temporaire
            partner = Partner.create({
                'name': partner_name or 'Client checklist piscine',
                'customer_rank': 1,
            })

        # ── Création du devis ──
        order_vals = {
            'partner_id': partner.id,
            'origin': ref_dossier or 'Fiche visite chantier',
            'note': note or '',
            'company_id': request.env.company.id,
        }
        # Référence dossier dans le champ client_order_ref si disponible
        if ref_dossier:
            order_vals['client_order_ref'] = ref_dossier

        order = SaleOrder.create(order_vals)

        # ── Lignes de commande ──
        sequence = 10
        for line_data in (lines or []):
            product_id = line_data.get('product_id')
            product = None
            if product_id:
                try:
                    product = Product.browse(int(product_id))
                    if not product.exists():
                        product = None
                except Exception:
                    product = None

            # Si pas de produit Odoo → chercher par référence ou nom
            if not product:
                default_code = line_data.get('default_code', '').strip()
                name = line_data.get('name', '').strip()
                if default_code:
                    product = Product.search([('default_code', '=', default_code)], limit=1) or None
                if not product and name:
                    product = Product.search([('name', '=', name), ('sale_ok', '=', True)], limit=1) or None

            qty = float(line_data.get('product_uom_qty', 1) or 1)
            price = float(line_data.get('price_unit', 0) or 0)
            desc = line_data.get('name', '')

            line_vals = {
                'order_id': order.id,
                'sequence': sequence,
                'product_uom_qty': qty,
            }

            if product:
                line_vals['product_id'] = product.id
                line_vals['name'] = desc or product.display_name
                if price > 0:
                    line_vals['price_unit'] = price
            else:
                # Ligne texte / section — utiliser un produit de service générique ou type note
                # On crée une ligne description
                line_vals['display_type'] = 'line_note'
                line_vals['name'] = desc or 'Produit non référencé'

            try:
                SaleOrderLine.create(line_vals)
            except Exception as e:
                _logger.warning('[pool_checklist] Ligne devis ignorée (%s): %s', desc, e)

            sequence += 10

        # ── URL du devis ──
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        quote_url = '%s/odoo/sales/%d' % (base_url.rstrip('/'), order.id)

        return {
            'order_id': order.id,
            'name': order.name,
            'partner_name': partner.name,
            'url': quote_url,
        }



    @http.route(
        '/pool-checklist/search-partner',
        type='json',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=False,
    )
    def search_partner(self, query='', limit=8, **kwargs):
        if not query or len(query.strip()) < 2:
            return {'partners': []}

        partners = request.env['res.partner'].sudo().search([
            ('name', 'ilike', query),
            ('active', '=', True),
            ('type', '=', 'contact'),
        ], limit=int(limit), order='name asc')

        result = [{
            'id': p.id,
            'name': p.name,
            'city': p.city or '',
            'zip': p.zip or '',
        } for p in partners]

        return {'partners': result}
