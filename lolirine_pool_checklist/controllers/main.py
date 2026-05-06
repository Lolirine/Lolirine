# -*- coding: utf-8 -*-
"""
lolirine_pool_checklist — Contrôleurs

Routes :
  GET  /visite-chantier                     → Page fiche de visite (React)
  POST /pool-checklist/products             → Recherche catalogue (texte + catégorie + fournisseur)
  POST /pool-checklist/categories           → Arbre catégories Pool Store
  POST /pool-checklist/suppliers            → Liste fournisseurs actifs Pool Store
  POST /pool-checklist/ai-suggest           → Proxy Anthropic (clé serveur)
  POST /pool-checklist/search-partner       → Autocomplétion partenaires Odoo
  POST /pool-checklist/create-quote         → Création devis sale.order
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

    # ─── Page principale ───────────────────────────────────────────────
    @http.route('/visite-chantier', type='http', auth='user',
                website=True, methods=['GET'], sitemap=False)
    def checklist_page(self, **kwargs):
        return request.render('lolirine_pool_checklist.page_checklist', {
            'page_title': 'Fiche de visite chantier — Lolirine Pool Store',
        })

    # ─── Recherche produits catalogue ──────────────────────────────────
    @http.route('/pool-checklist/products', type='jsonrpc', auth='user',
                website=True, methods=['POST'], csrf=False)
    def search_products(self, query='', limit=20, category_id=None,
                        supplier_id=None, sort='name', **kwargs):
        """
        Recherche multi-critères dans le catalogue Pool Store.
        - query       : texte libre (nom, référence, description)
        - category_id : filtrer par catégorie interne (product.category) ou publique
        - supplier_id : filtrer par fournisseur (res.partner id)
        - sort        : 'name' | 'price_asc' | 'price_desc' | 'relevance'
        """
        env = request.env
        domain = [('sale_ok', '=', True), ('active', '=', True)]

        if query and len(query.strip()) >= 2:
            q = query.strip()
            domain += [
                '|', '|', '|', '|',
                ('name', 'ilike', q),
                ('default_code', 'ilike', q),
                ('description_sale', 'ilike', q),
                ('categ_id.name', 'ilike', q),
                ('seller_ids.product_code', 'ilike', q),
            ]

        if category_id:
            try:
                cid = int(category_id)
                # Chercher d'abord dans les catégories publiques (e-commerce)
                pub_cat = env['product.public.category'].sudo().browse(cid)
                if pub_cat.exists():
                    domain.append(('public_categ_ids', 'child_of', cid))
                else:
                    # Catégorie interne
                    domain.append(('categ_id', 'child_of', cid))
            except (ValueError, TypeError):
                pass

        if supplier_id:
            try:
                domain.append(('seller_ids.partner_id', '=', int(supplier_id)))
            except (ValueError, TypeError):
                pass

        order_map = {
            'name': 'name asc',
            'price_asc': 'list_price asc, name asc',
            'price_desc': 'list_price desc, name asc',
            'relevance': 'name asc',
        }
        order = order_map.get(sort, 'name asc')

        templates = env['product.template'].sudo().search(
            domain, limit=int(limit), order=order
        )

        result = []
        for p in templates:
            sup_info = p.seller_ids[:1]
            supplier = {}
            if sup_info:
                s = sup_info[0]
                supplier = {
                    'id':    s.partner_id.id,
                    'name':  s.partner_id.name or '',
                    'ref':   s.product_code or '',
                    'price': float(s.price or 0),
                }
            result.append({
                'id':        p.id,
                'name':      p.name,
                'ref':       p.default_code or '',
                'category':  p.categ_id.name if p.categ_id else '',
                'categ_id':  p.categ_id.id if p.categ_id else None,
                'unit':      p.uom_id.name if p.uom_id else 'pcs',
                'price':     float(p.list_price or 0),
                'suppliers': [supplier] if supplier else [],
                'description': (p.description_sale or '')[:120],
                'image_url': f'/web/image/product.template/{p.id}/image_128' if p.image_128 else None,
            })

        return {'products': result, 'total': len(result)}

    # ─── Catégories du catalogue Pool Store ────────────────────────────
    @http.route('/pool-checklist/categories', type='jsonrpc', auth='user',
                website=True, methods=['POST'], csrf=False)
    def get_categories(self, parent_id=None, **kwargs):
        """
        Retourne les catégories publiques du Pool Store avec le nombre de produits.
        Si parent_id est fourni, retourne les enfants de cette catégorie.
        """
        env = request.env

        # Catégories publiques (e-commerce) du site Pool Store
        pub_domain = [('website_id', 'in', [False, POOL_WEBSITE_ID])]
        if parent_id:
            try:
                pub_domain.append(('parent_id', '=', int(parent_id)))
            except (ValueError, TypeError):
                pub_domain.append(('parent_id', '=', False))
        else:
            pub_domain.append(('parent_id', '=', False))

        categories = env['product.public.category'].sudo().search(
            pub_domain, order='sequence asc, name asc'
        )

        result = []
        for cat in categories:
            # Compter les produits publiés dans cette catégorie (et sous-catégories)
            count = env['product.template'].sudo().search_count([
                ('sale_ok', '=', True),
                ('active', '=', True),
                ('public_categ_ids', 'child_of', cat.id),
            ])
            if count == 0 and not parent_id:
                continue  # Masquer les catégories racines vides

            # Nombre de sous-catégories
            child_count = env['product.public.category'].sudo().search_count([
                ('parent_id', '=', cat.id),
            ])

            result.append({
                'id':          cat.id,
                'name':        cat.name,
                'parent_id':   cat.parent_id.id if cat.parent_id else None,
                'parent_name': cat.parent_id.name if cat.parent_id else None,
                'product_count': count,
                'child_count':   child_count,
                'has_children':  child_count > 0,
            })

        # Fallback : catégories internes si aucune catégorie publique trouvée
        if not result:
            int_domain = []
            if parent_id:
                try:
                    int_domain.append(('parent_id', '=', int(parent_id)))
                except (ValueError, TypeError):
                    int_domain.append(('parent_id', '=', False))
            else:
                int_domain.append(('parent_id', '=', False))

            int_cats = env['product.category'].sudo().search(
                int_domain, order='name asc'
            )
            for cat in int_cats:
                count = env['product.template'].sudo().search_count([
                    ('sale_ok', '=', True),
                    ('active', '=', True),
                    ('categ_id', 'child_of', cat.id),
                ])
                if count == 0:
                    continue
                result.append({
                    'id':          cat.id,
                    'name':        cat.name,
                    'parent_id':   cat.parent_id.id if cat.parent_id else None,
                    'parent_name': cat.parent_id.name if cat.parent_id else None,
                    'product_count': count,
                    'child_count': 0,
                    'has_children': False,
                    'internal': True,
                })

        return {'categories': result}

    # ─── Fournisseurs actifs Pool Store ────────────────────────────────
    @http.route('/pool-checklist/suppliers', type='jsonrpc', auth='user',
                website=True, methods=['POST'], csrf=False)
    def get_suppliers(self, **kwargs):
        """
        Liste les fournisseurs qui ont des produits actifs dans le catalogue.
        """
        env = request.env
        env.cr.execute("""
            SELECT DISTINCT rp.id, rp.name, COUNT(DISTINCT pt.id) AS product_count
            FROM product_supplierinfo psi
            JOIN res_partner rp ON rp.id = psi.partner_id
            JOIN product_template pt ON pt.id = psi.product_tmpl_id
            WHERE pt.sale_ok = TRUE AND pt.active = TRUE
            GROUP BY rp.id, rp.name
            HAVING COUNT(DISTINCT pt.id) > 0
            ORDER BY COUNT(DISTINCT pt.id) DESC
            LIMIT 20
        """)
        rows = env.cr.fetchall()
        return {'suppliers': [
            {'id': r[0], 'name': r[1], 'product_count': r[2]}
            for r in rows
        ]}

    # ─── Proxy IA Anthropic ────────────────────────────────────────────
    @http.route('/pool-checklist/ai-suggest', type='jsonrpc', auth='user',
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

        system = (
            'Expert equipements piscine (marche belge/europeen). '
            'JSON uniquement sans markdown : '
            '{"products":[{"name":"","ref":"","category":"","unit":"piece|kg|L|m|lot",'
            '"note":"","supplier":"Fluidra|SCP|HTH|Zodiac|Hayward|Astralpool|Pentair"}]} '
            'Max 8 produits concrets avec references si possible.'
        )
        payload = json.dumps({
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 900,
            'system': system,
            'messages': [{'role': 'user', 'content':
                f'Section: {section_label}\nPoint de controle: "{item_text}"\n'
                'Produits / materiaux concrets a prevoir pour ce point ?'}],
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages', data=payload,
            headers={'Content-Type': 'application/json', 'x-api-key': api_key,
                     'anthropic-version': '2023-06-01'}, method='POST')
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
        for p in prods[:8]:
            if not p.get('name'):
                continue
            s = p.get('supplier', '')
            result.append({
                'name': p.get('name', ''), 'ref': p.get('ref', ''),
                'category': p.get('category', ''), 'unit': p.get('unit', 'piece'),
                'note': p.get('note', ''), 'price': 0,
                'suppliers': [{'name': s, 'ref': p.get('ref', ''), 'price': 0}] if s else [],
            })
        return {'products': result}

    # ─── Autocomplétion partenaires ────────────────────────────────────
    @http.route('/pool-checklist/search-partner', type='jsonrpc', auth='user',
                website=True, methods=['POST'], csrf=False)
    def search_partner(self, query='', limit=8, **kwargs):
        if not query or len(query.strip()) < 2:
            return {'partners': []}
        partners = request.env['res.partner'].sudo().search([
            ('name', 'ilike', query.strip()),
            ('active', '=', True),
            ('type', '=', 'contact'),
        ], limit=int(limit), order='name asc')
        return {'partners': [
            {'id': p.id, 'name': p.name, 'city': p.city or ''}
            for p in partners
        ]}

    # ─── Création devis ────────────────────────────────────────────────
    @http.route('/pool-checklist/create-quote', type='jsonrpc', auth='user',
                website=True, methods=['POST'], csrf=False)
    def create_quote(self, partner_id=None, partner_name='', ref_dossier='',
                     note='', payment_term='', lines=None, fiche_id=None, **kwargs):
        env = request.env
        if not lines:
            return {'error': 'Aucune ligne fournie'}
        Partner = env['res.partner'].sudo()
        partner = None
        if partner_id:
            try:
                p = Partner.browse(int(partner_id))
                if p.exists():
                    partner = p
            except Exception:
                pass
        if not partner and partner_name:
            found = Partner.search(
                [('name', 'ilike', partner_name.strip()), ('type', '=', 'contact')],
                limit=1)
            partner = found or None
        if not partner:
            partner = Partner.create({
                'name': partner_name or 'Client checklist piscine',
                'customer_rank': 1,
            })
        # Récupérer la séquence PSC directement ici pour garantir l'attribution
        psc_name = env['ir.sequence'].sudo().next_by_code('lolirine.pool.sale.order') or '/'

        # Trouver le modèle "Devis Piscine"
        pool_template = env['sale.order.template'].sudo().search(
            ['|', ('name', 'ilike', 'piscine'), ('name', 'ilike', 'pool')],
            limit=1
        )

        order_vals = {
            'partner_id': partner.id,
            'name': psc_name,
            'is_pool_quote': True,
            'origin': ref_dossier or 'Fiche visite chantier',
            'note': note or '',
            'company_id': request.env.company.id,
        }
        if pool_template:
            order_vals['sale_order_template_id'] = pool_template.id
        if fiche_id:
            order_vals['pool_fiche_id'] = fiche_id
        if ref_dossier:
            order_vals['client_order_ref'] = ref_dossier
            order_vals['pool_ref_dossier'] = ref_dossier
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
                    if p.exists():
                        product = p
                except Exception:
                    pass
            if not product:
                code = (ld.get('default_code') or '').strip()
                name = (ld.get('name') or '').strip()
                if code:
                    product = Product.search([('default_code', '=', code)], limit=1) or None
                if not product and name:
                    product = Product.search(
                        [('name', '=', name), ('sale_ok', '=', True)], limit=1) or None
            qty   = float(ld.get('product_uom_qty', 1) or 1)
            price = float(ld.get('price_unit', 0) or 0)
            disc  = float(ld.get('discount', 0) or 0)
            desc  = ld.get('name', '')
            lv = {'order_id': order.id, 'sequence': seq, 'product_uom_qty': qty}
            if product:
                lv['product_id'] = product.id
                lv['name'] = desc or product.display_name
                if price > 0:
                    lv['price_unit'] = price
                if disc > 0:
                    lv['discount'] = disc
            else:
                lv['display_type'] = 'line_note'
                lv['name'] = desc or 'Article non reference'
            try:
                SOLine.create(lv)
            except Exception as e:
                _logger.warning('[pool_checklist] Ligne ignoree: %s', e)
            seq += 10
        base = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        return {
            'order_id':     order.id,
            'name':         order.name,
            'partner_name': partner.name,
            'url':          f'{base.rstrip("/")}/odoo/sales/{order.id}',
        }
