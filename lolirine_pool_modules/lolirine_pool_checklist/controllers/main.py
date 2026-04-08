# -*- coding: utf-8 -*-
"""
Contrôleurs pour la fiche de visite piscine.

Routes :
  GET  /visite-chantier          → Page principale (checklist React)
  POST /pool-checklist/products  → Recherche produits catalogue website_id=6
"""

import json
import logging

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# ID du site Pool Store (website_id = 6 — à ajuster si nécessaire)
POOL_STORE_WEBSITE_ID = 6


class PoolChecklistController(http.Controller):

    # ── Page principale ───────────────────────────────────────────────────

    @http.route(
        '/visite-chantier',
        type='http',
        auth='user',           # Accès réservé aux utilisateurs connectés
        website=True,
        methods=['GET'],
        sitemap=False,         # Ne pas indexer dans le sitemap public
    )
    def checklist_page(self, **kwargs):
        """
        Sert la page de la fiche de visite chantier.
        Accessible uniquement aux utilisateurs internes connectés.
        """
        return request.render(
            'lolirine_pool_checklist.page_checklist',
            {
                'website_id': POOL_STORE_WEBSITE_ID,
                'page_title': 'Fiche de visite chantier — Lolirine Pool Store',
            }
        )

    # ── API recherche produits ─────────────────────────────────────────────

    @http.route(
        '/pool-checklist/products',
        type='json',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=False,
    )
    def search_products(self, query='', limit=12, **kwargs):
        """
        Recherche des produits publiés du Pool Store (website_id=6).

        Paramètres JSON :
          query  (str)  : terme de recherche
          limit  (int)  : nombre max de résultats (défaut 12)

        Retourne une liste de dicts :
          id, name, default_code, list_price, categ_name,
          image_url, description_sale
        """
        if not query or not query.strip():
            return {'products': [], 'error': None}

        try:
            ProductTemplate = request.env['product.template'].sudo()

            domain = [
                ('website_published', '=', True),
                '|',
                ('website_id', '=', POOL_STORE_WEBSITE_ID),
                ('website_id', '=', False),
                '|',
                ('name', 'ilike', query),
                ('description_sale', 'ilike', query),
            ]

            products = ProductTemplate.search_read(
                domain,
                fields=[
                    'id', 'name', 'default_code', 'list_price',
                    'categ_id', 'description_sale', 'website_url',
                ],
                limit=int(limit),
                order='name asc',
            )

            result = []
            for p in products:
                # URL image via le contrôleur web standard
                image_url = f"/web/image/product.template/{p['id']}/image_128"
                result.append({
                    'id':          p['id'],
                    'name':        p['name'],
                    'ref':         p.get('default_code') or '',
                    'price':       p.get('list_price', 0.0),
                    'category':    p['categ_id'][1] if p.get('categ_id') else '',
                    'image':       image_url,
                    'description': p.get('description_sale') or '',
                    'url':         p.get('website_url') or '',
                    'unit':        'pièce',
                })

            _logger.debug(
                '[pool_checklist] Recherche "%s" → %d résultats', query, len(result)
            )
            return {'products': result, 'error': None}

        except Exception as e:
            _logger.error('[pool_checklist] Erreur recherche produits: %s', e)
            return {'products': [], 'error': str(e)}

    # ── Sanity check ──────────────────────────────────────────────────────

    @http.route(
        '/pool-checklist/ping',
        type='json',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=False,
    )
    def ping(self, **kwargs):
        """Endpoint de test pour vérifier la connectivité depuis le front."""
        return {
            'status': 'ok',
            'user': request.env.user.name,
            'website_id': POOL_STORE_WEBSITE_ID,
        }
