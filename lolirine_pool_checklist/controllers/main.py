# -*- coding: utf-8 -*-
"""
lolirine_pool_checklist — Contrôleurs

Routes :
  GET  /visite-chantier               → Page fiche de visite (React)
  POST /pool-checklist/products       → Recherche catalogue Pool Store
  POST /pool-checklist/ai-suggest     → Proxy Anthropic (clé serveur)
  POST /pool-checklist/search-partner → Autocomplétion partenaires Odoo
  POST /pool-checklist/create-quote   → Création devis sale.order
"""

import json
import logging
import urllib.request
import urllib.error

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

POOL_WEBSITE_ID = 6


class PoolChecklistController(http.Controller):

    @http.route('/visite-chantier', type='http', auth='user',
                website=True, methods=['GET'], sitemap=False)
    def checklist_page(self, **kwargs):
        return request.render('lolirine_pool_checklist.page_checklist', {
            'page_title': 'Fiche de visite chantier — Lolirine Pool Store',
        })

    @http.route('/pool-checklist/products', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def search_products(self, query='', limit=15, **kwargs):
        if not query or len(query.strip()) < 2:
            return {'products': []}
        q = query.strip()
        domain = [
            ('sale_ok', '=', True), ('active', '=', True),
            '|', ('name', 'ilike', q), ('default_code', 'ilike', q),
        ]
        templates = request.env['product.template'].sudo().search(
            domain, limit=int(limit), order='name asc')
        result = []
        for p in templates:
            sup_info = p.seller_ids[:1]
            supplier = {}
            if sup_info:
                s = sup_info[0]
                supplier = {'name': s.partner_id.name or '', 'ref': s.product_code or '', 'price': float(s.price or 0)}
            result.append({
                'id': p.id, 'name': p.name, 'ref': p.default_code or '',
                'category': p.categ_id.name if p.categ_id else '',
                'unit': p.uom_id.name if p.uom_id else 'pcs',
                'price': float(p.list_price or 0),
                'suppliers': [supplier] if supplier else [],
            })
        return {'products': result}

    @http.route('/pool-checklist/ai-suggest', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def ai_suggest(self, item_text='', section_label='', **kwargs):
        if not item_text:
            return {'products': [], 'error': 'item_text manquant'}
        ICP = request.env['ir.config_parameter'].sudo()
        api_key = (ICP.get_param('anthropic.api_key') or
                   ICP.get_param('pool.claude_api_key') or
                   ICP.get_param('lolirine_contract.anthropic_api_key') or '')
        if not api_key:
            return {'products': [], 'error': 'Cle API non configuree'}
        system = ('Expert equipements piscine (marche belge). JSON uniquement sans markdown : '
                  '{"products":[{"name":"","ref":"","category":"","unit":"piece|kg|L|m|lot","note":"","supplier":"Fluidra|SCP|HTH|Zodiac|Hayward"}]} '
                  'Max 7 produits.')
        payload = json.dumps({
            'model': 'claude-haiku-4-5-20251001', 'max_tokens': 800,
            'system': system,
            'messages': [{'role': 'user', 'content': f'Section: {section_label}\nPoint: "{item_text}"\nProduits a prevoir?'}],
        }).encode('utf-8')
        req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=payload,
            headers={'Content-Type':'application/json','x-api-key':api_key,'anthropic-version':'2023-06-01'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            _logger.error('[pool_checklist] Anthropic HTTP %s', e.code)
            return {'products': [], 'error': f'Anthropic HTTP {e.code}'}
        except Exception as e:
            return {'products': [], 'error': str(e)}
        raw = body.get('content', [{}])[0].get('text', '{}')
        try:
            prods = json.loads(raw).get('products', [])
        except Exception:
            return {'products': [], 'error': 'JSON invalide'}
        result = []
        for p in prods[:7]:
            if not p.get('name'): continue
            s = p.get('supplier', '')
            result.append({'name': p.get('name',''), 'ref': p.get('ref',''),
                'category': p.get('category',''), 'unit': p.get('unit','piece'),
                'note': p.get('note',''), 'price': 0,
                'suppliers': [{'name': s, 'ref': p.get('ref',''), 'price': 0}] if s else []})
        return {'products': result}

    @http.route('/pool-checklist/search-partner', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def search_partner(self, query='', limit=8, **kwargs):
        if not query or len(query.strip()) < 2:
            return {'partners': []}
        partners = request.env['res.partner'].sudo().search([
            ('name', 'ilike', query.strip()), ('active', '=', True), ('type', '=', 'contact'),
        ], limit=int(limit), order='name asc')
        return {'partners': [{'id': p.id, 'name': p.name, 'city': p.city or ''} for p in partners]}

    @http.route('/pool-checklist/create-quote', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def create_quote(self, partner_id=None, partner_name='', ref_dossier='',
                     note='', payment_term='', lines=None, **kwargs):
        env = request.env
        if not lines:
            return {'error': 'Aucune ligne fournie'}
        Partner = env['res.partner'].sudo()
        partner = None
        if partner_id:
            try:
                p = Partner.browse(int(partner_id))
                if p.exists(): partner = p
            except Exception: pass
        if not partner and partner_name:
            found = Partner.search([('name','ilike',partner_name.strip()),('type','=','contact')], limit=1)
            partner = found or None
        if not partner:
            partner = Partner.create({'name': partner_name or 'Client checklist piscine', 'customer_rank': 1})
        order_vals = {'partner_id': partner.id, 'origin': ref_dossier or 'Fiche visite chantier',
                      'note': note or '', 'company_id': request.env.company.id}
        if ref_dossier:
            order_vals['client_order_ref'] = ref_dossier
        order = env['sale.order'].sudo().create(order_vals)
        Product = env['product.product'].sudo()
        SOLine  = env['sale.order.line'].sudo()
        seq = 10
        for ld in (lines or []):
            product = None
            pid = ld.get('product_id')
            if pid:
                try:
                    p = Product.browse(int(pid))
                    if p.exists(): product = p
                except Exception: pass
            if not product:
                code = (ld.get('default_code') or '').strip()
                name = (ld.get('name') or '').strip()
                if code:
                    product = Product.search([('default_code','=',code)], limit=1) or None
                if not product and name:
                    product = Product.search([('name','=',name),('sale_ok','=',True)], limit=1) or None
            qty = float(ld.get('product_uom_qty',1) or 1)
            price = float(ld.get('price_unit',0) or 0)
            disc = float(ld.get('discount',0) or 0)
            desc = ld.get('name','')
            lv = {'order_id': order.id, 'sequence': seq, 'product_uom_qty': qty}
            if product:
                lv['product_id'] = product.id
                lv['name'] = desc or product.display_name
                if price > 0: lv['price_unit'] = price
                if disc > 0:  lv['discount'] = disc
            else:
                lv['display_type'] = 'line_note'
                lv['name'] = desc or 'Article non reference'
            try: SOLine.create(lv)
            except Exception as e: _logger.warning('[pool_checklist] Ligne ignoree: %s', e)
            seq += 10
        base = request.env['ir.config_parameter'].sudo().get_param('web.base.url','')
        return {'order_id': order.id, 'name': order.name, 'partner_name': partner.name,
                'url': f'{base.rstrip("/")}/odoo/sales/{order.id}'}
