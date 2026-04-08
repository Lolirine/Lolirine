# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)
POOL_STORE_WEBSITE_ID = 6

# IDs fournisseurs dropshipping (à ajuster si nécessaire)
SUPPLIER_NAMES = {
    'fluidra': ['Fluidra', 'SIBO', 'Fluidra/SIBO'],
    'scp':     ['SCP', 'SCP Bénélux', 'SCP Benelux'],
}

class PoolChecklistController(http.Controller):

    @http.route('/visite-chantier', type='http', auth='user', website=True, methods=['GET'], sitemap=False)
    def checklist_page(self, **kwargs):
        return request.render('lolirine_pool_checklist.page_checklist', {
            'website_id': POOL_STORE_WEBSITE_ID,
        })

    @http.route('/pool-checklist/products', type='json', auth='user', website=True, methods=['POST'], csrf=False)
    def search_products(self, query='', limit=12, supplier=None, **kwargs):
        """
        Recherche produits avec filtre fournisseur optionnel.
        supplier: None (tous) | 'fluidra' | 'scp'
        """
        if not query or not query.strip():
            return {'products': [], 'error': None}
        try:
            PT = request.env['product.template'].sudo()

            domain = [
                ('website_published', '=', True),
                '|', ('website_id', '=', POOL_STORE_WEBSITE_ID), ('website_id', '=', False),
                '|', ('name', 'ilike', query), ('description_sale', 'ilike', query),
            ]

            # Filtre fournisseur via seller_ids
            if supplier and supplier in SUPPLIER_NAMES:
                names = SUPPLIER_NAMES[supplier]
                supplier_domain = []
                for n in names:
                    supplier_domain += [('seller_ids.partner_id.name', 'ilike', n)]
                # OR entre les noms fournisseurs
                if len(names) > 1:
                    od = ['|'] * (len(names) - 1) + supplier_domain
                    domain += od
                else:
                    domain += supplier_domain

            products = PT.search_read(
                domain,
                fields=['id', 'name', 'default_code', 'list_price', 'categ_id',
                        'description_sale', 'website_url', 'seller_ids'],
                limit=int(limit),
                order='name asc',
            )

            result = []
            for p in products:
                # Récupérer les fournisseurs liés
                supplier_info = []
                if p.get('seller_ids'):
                    sellers = request.env['product.supplierinfo'].sudo().browse(p['seller_ids'])
                    for s in sellers:
                        sname = s.partner_id.name or ''
                        supplier_info.append({
                            'name': sname,
                            'ref': s.product_code or '',
                            'price': s.price or 0.0,
                            'type': 'fluidra' if any(k.lower() in sname.lower() for k in ['fluidra','sibo']) else
                                    'scp' if any(k.lower() in sname.lower() for k in ['scp']) else 'other'
                        })

                result.append({
                    'id':          p['id'],
                    'name':        p['name'],
                    'ref':         p.get('default_code') or '',
                    'price':       p.get('list_price', 0.0),
                    'category':    p['categ_id'][1] if p.get('categ_id') else '',
                    'image':       f"/web/image/product.template/{p['id']}/image_512",
                    'description': p.get('description_sale') or '',
                    'url':         p.get('website_url') or '',
                    'unit':        'pièce',
                    'suppliers':   supplier_info,
                })

            return {'products': result, 'error': None}

        except Exception as e:
            _logger.error('[pool_checklist] Erreur: %s', e)
            return {'products': [], 'error': str(e)}

    @http.route('/pool-checklist/ping', type='json', auth='user', website=True, methods=['POST'], csrf=False)
    def ping(self, **kwargs):
        return {'status': 'ok', 'user': request.env.user.name}
