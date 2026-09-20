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
  POST /pool-checklist/create-event         → Création rendez-vous calendar.event

RÉVISION CATALOGUE — ce qui a changé et pourquoi
------------------------------------------------
L'ancienne recherche renvoyait au maximum `limit` produits (20 par défaut)
et annonçait `total = len(result)`. Sur un catalogue de ~8 700 articles,
l'interface affichait donc 20 lignes en se présentant comme exhaustive :
c'est ce qui donnait l'impression d'un catalogue incomplet. Trois
corrections :

  1. `total` vient maintenant d'un `search_count` sur le domaine complet,
     et `offset` permet de paginer. L'interface peut afficher
     « 20 sur 143 » et charger la suite.
  2. Le tri par défaut était alphabétique : chercher « pompe » renvoyait
     les 20 premiers résultats dans l'ordre de l'alphabet, pas les plus
     pertinents. Un score de pertinence est calculé (référence exacte,
     puis début de libellé, puis mot entier, puis sous-chaîne).
  3. Le domaine texte couvre en plus `barcode`, la référence et le
     libellé fournisseur, et les références des variantes.

S'y ajoutent les données de marge (`cost`, `cost_source`, `margin`,
`margin_pct`), réservées aux utilisateurs internes disposant du droit
de vente — voir _can_see_cost().
"""

import json
import logging
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta

import pytz

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

POOL_WEBSITE_ID = 6

# Au-delà de ce nombre de correspondances, le classement par pertinence est
# abandonné au profit du tri alphabétique : scorer 3 000 produits à chaque
# frappe coûterait plus cher que le gain de confort.
RELEVANCE_MAX_CANDIDATES = 800

# Groupe requis pour recevoir les prix d'achat et les marges.
# /visite-chantier est une route website : un portail connecté peut
# l'atteindre. Les coûts ne doivent jamais partir vers son navigateur.
COST_GROUP = 'sales_team.group_sale_salesman'


class PoolChecklistController(http.Controller):

    # ═══════════════════════════════════════════════════════════════════
    #  Aides internes
    # ═══════════════════════════════════════════════════════════════════

    def _can_see_cost(self):
        """Prix d'achat et marges : utilisateur interne + droit de vente."""
        user = request.env.user
        if user.share:            # portail / public
            return False
        try:
            return user.has_group(COST_GROUP)
        except Exception:
            return False

    def _best_seller(self, template, qty=1.0):
        """
        Meilleure ligne fournisseur pour la quantité demandée.

        On privilégie une ligne dont le `min_qty` est atteint ; à défaut,
        celle dont le `min_qty` est le plus bas. Entre deux lignes
        éligibles, le prix le plus bas gagne.
        """
        sellers = template.seller_ids
        if not sellers:
            return None
        eligible = sellers.filtered(lambda s: (s.min_qty or 0) <= qty)
        pool = eligible or sellers
        return sorted(
            pool,
            key=lambda s: ((s.min_qty or 0) if not eligible else 0,
                           s.price or 0.0,
                           s.sequence or 0)
        )[0]

    def _seller_price_company_currency(self, seller):
        """Prix fournisseur converti dans la devise société si nécessaire."""
        price = float(seller.price or 0.0)
        company = request.env.company
        cur = seller.currency_id
        if not cur or not company.currency_id or cur == company.currency_id:
            return price
        try:
            return cur._convert(price, company.currency_id, company,
                                datetime.today().date())
        except Exception:
            return price

    def _score(self, name, code, seller_codes, q):
        """
        Score de pertinence, du plus fort au plus faible.
        Volontairement simple et lisible : une référence exacte passe
        toujours devant un libellé qui contient le terme par hasard.
        """
        name = (name or '').lower()
        code = (code or '').lower()
        codes = [c.lower() for c in seller_codes if c]

        if code == q or q in codes:
            return 100
        if code.startswith(q) or any(c.startswith(q) for c in codes):
            return 90
        if name.startswith(q):
            return 80
        if re.search(r'\b' + re.escape(q), name):
            return 60
        if q in name:
            return 40
        if q in code or any(q in c for c in codes):
            return 30
        return 10

    # ═══════════════════════════════════════════════════════════════════
    #  Page principale
    # ═══════════════════════════════════════════════════════════════════

    @http.route('/visite-chantier', type='http', auth='user',
                website=True, methods=['GET'], sitemap=False)
    def checklist_page(self, **kwargs):
        return request.render('lolirine_pool_checklist.page_checklist', {
            'page_title': 'Fiche de visite chantier — Lolirine Pool Store',
        })

    # ═══════════════════════════════════════════════════════════════════
    #  Recherche produits catalogue
    # ═══════════════════════════════════════════════════════════════════

    @http.route('/pool-checklist/products', type='jsonrpc', auth='user',
                website=True, methods=['POST'], csrf=False)
    def search_products(self, query='', limit=30, offset=0, category_id=None,
                        supplier_id=None, sort='relevance',
                        published_only=False, qty=1.0, **kwargs):
        """
        Recherche multi-critères dans le catalogue.

        query          : texte libre (libellé, réf. interne, code-barres,
                         réf. et libellé fournisseur, description, catégorie)
        category_id    : product.public.category OU product.category (détecté)
        supplier_id    : res.partner id
        sort           : 'relevance' | 'name' | 'price_asc' | 'price_desc'
                         | 'margin_desc'
        published_only : True = uniquement les articles publiés sur le site
        offset / limit : pagination ; `total` est le nombre RÉEL de résultats
        qty            : quantité envisagée, pour choisir le bon palier
                         fournisseur dans le calcul de marge
        """
        env = request.env
        Tmpl = env['product.template'].sudo()

        try:
            limit = max(1, min(200, int(limit)))
        except (TypeError, ValueError):
            limit = 30
        try:
            offset = max(0, int(offset))
        except (TypeError, ValueError):
            offset = 0
        try:
            qty = max(0.0, float(qty))
        except (TypeError, ValueError):
            qty = 1.0

        domain = [('sale_ok', '=', True), ('active', '=', True)]

        if published_only:
            domain += [('is_published', '=', True),
                       ('website_id', 'in', [False, POOL_WEBSITE_ID])]

        q = (query or '').strip()
        if q and len(q) >= 2:
            domain += [
                '|', '|', '|', '|', '|', '|',
                ('name', 'ilike', q),
                ('default_code', 'ilike', q),
                ('barcode', 'ilike', q),
                ('description_sale', 'ilike', q),
                ('categ_id.name', 'ilike', q),
                ('seller_ids.product_code', 'ilike', q),
                ('seller_ids.product_name', 'ilike', q),
            ]

        if category_id:
            try:
                cid = int(category_id)
                pub_cat = env['product.public.category'].sudo().browse(cid)
                if pub_cat.exists():
                    domain.append(('public_categ_ids', 'child_of', cid))
                else:
                    domain.append(('categ_id', 'child_of', cid))
            except (ValueError, TypeError):
                pass

        if supplier_id:
            try:
                domain.append(('seller_ids.partner_id', '=', int(supplier_id)))
            except (ValueError, TypeError):
                pass

        # ── Total réel, indépendant de la page affichée ────────────────
        total = Tmpl.search_count(domain)

        show_cost = self._can_see_cost()

        # ── Sélection de la page ───────────────────────────────────────
        order_map = {
            'name':       'name asc',
            'price_asc':  'list_price asc, name asc',
            'price_desc': 'list_price desc, name asc',
        }

        ranked = False
        if sort == 'relevance' and q and len(q) >= 2:
            if total <= RELEVANCE_MAX_CANDIDATES:
                candidates = Tmpl.search(domain, order='name asc')
                ql = q.lower()
                scored = sorted(
                    candidates,
                    key=lambda p: (
                        -self._score(p.name, p.default_code,
                                     p.seller_ids.mapped('product_code'), ql),
                        (p.name or '').lower(),
                    )
                )
                templates = Tmpl.browse([p.id for p in scored[offset:offset + limit]])
                ranked = True
            else:
                # Trop de correspondances pour un classement utile :
                # on retombe sur l'alphabétique et on le SIGNALE au front,
                # pour que l'utilisateur sache qu'il doit affiner.
                templates = Tmpl.search(domain, limit=limit, offset=offset,
                                        order='name asc')
        elif sort == 'margin_desc' and show_cost:
            # La marge n'est pas un champ stocké : on ne peut pas trier en
            # SQL. On classe la page courante, pas le catalogue entier —
            # un tri global exigerait de charger tous les résultats.
            templates = Tmpl.search(domain, limit=limit, offset=offset,
                                    order='name asc')
        else:
            templates = Tmpl.search(domain, limit=limit, offset=offset,
                                    order=order_map.get(sort, 'name asc'))

        # ── Sérialisation ──────────────────────────────────────────────
        result = []
        for p in templates:
            sellers = []
            for s in p.seller_ids:
                sellers.append({
                    'id':       s.partner_id.id,
                    'name':     s.partner_id.name or '',
                    'ref':      s.product_code or '',
                    'label':    s.product_name or '',
                    'min_qty':  float(s.min_qty or 0),
                    'delay':    int(s.delay or 0),
                    'price':    (self._seller_price_company_currency(s)
                                 if show_cost else 0.0),
                })

            list_price = float(p.list_price or 0.0)
            item = {
                'id':          p.id,
                'name':        p.name,
                'ref':         p.default_code or '',
                'barcode':     p.barcode or '',
                'category':    p.categ_id.name if p.categ_id else '',
                'categ_id':    p.categ_id.id if p.categ_id else None,
                'public_categs': [{'id': c.id, 'name': c.name}
                                  for c in p.public_categ_ids],
                'unit':        p.uom_id.name if p.uom_id else 'pcs',
                'price':       list_price,
                'published':   bool(p.is_published),
                'suppliers':   sellers,
                'description': (p.description_sale or '')[:120],
                'image_url':   (f'/web/image/product.template/{p.id}/image_128'
                                if p.image_128 else None),
            }

            # ── Coût et marge ──────────────────────────────────────────
            if show_cost:
                best = self._best_seller(p, qty)
                cost, source = 0.0, 'none'
                if best and (best.price or 0):
                    cost = self._seller_price_company_currency(best)
                    source = 'supplier'
                elif p.standard_price:
                    cost = float(p.standard_price)
                    source = 'standard'

                item['cost'] = cost
                # Lire cette étiquette au moment de décider une remise :
                # une marge calculée sur un coût faux est pire que pas de
                # marge du tout.
                item['cost_source'] = source
                item['cost_supplier'] = best.partner_id.name if best else ''
                item['standard_price'] = float(p.standard_price or 0.0)
                if cost > 0:
                    item['margin'] = list_price - cost
                    item['margin_pct'] = round(
                        (list_price - cost) / list_price * 100, 1
                    ) if list_price else 0.0
                    item['markup_pct'] = round(
                        (list_price - cost) / cost * 100, 1
                    )
                else:
                    item['margin'] = None
                    item['margin_pct'] = None
                    item['markup_pct'] = None

            result.append(item)

        if sort == 'margin_desc' and show_cost:
            result.sort(key=lambda r: (r.get('margin_pct') is None,
                                       -(r.get('margin_pct') or 0)))

        return {
            'products':   result,
            'total':      total,
            'offset':     offset,
            'limit':      limit,
            'has_more':   offset + len(result) < total,
            'ranked':     ranked,
            'show_cost':  show_cost,
            # True = trop de résultats pour classer par pertinence,
            # le front peut inviter à préciser la recherche.
            'truncated_ranking': bool(
                q and sort == 'relevance' and total > RELEVANCE_MAX_CANDIDATES
            ),
        }

    # ═══════════════════════════════════════════════════════════════════
    #  Catégories du catalogue (mégamenus)
    # ═══════════════════════════════════════════════════════════════════

    @http.route('/pool-checklist/categories', type='jsonrpc', auth='user',
                website=True, methods=['POST'], csrf=False)
    def get_categories(self, parent_id=None, full=False, **kwargs):
        """
        full=False (défaut) : enfants directs de parent_id — comportement
                              historique, compatible avec l'ancien front.
        full=True           : ARBRE COMPLET des catégories e-commerce en un
                              seul appel, avec chemin et profondeur. C'est
                              ce que doit utiliser un sélecteur
                              arborescent : 216 catégories tiennent
                              largement dans une réponse.

        Les compteurs sont calculés en une requête SQL sur la table de
        liaison, puis remontés aux parents. L'ancienne version faisait un
        search_count par catégorie.
        """
        env = request.env
        Cat = env['product.public.category'].sudo()

        cats = Cat.search([], order='sequence asc, name asc')
        if not cats:
            return self._categories_internal_fallback(parent_id)

        # ── Compteurs directs, en une requête ──────────────────────────
        field = env['product.template']._fields['public_categ_ids']
        rel, col_cat, col_tmpl = field.relation, field.column2, field.column1
        # column1 = colonne du modèle courant (product.template),
        # column2 = colonne du comodèle (product.public.category).
        env.cr.execute(f"""
            SELECT rel.{col_cat} AS cat_id, COUNT(DISTINCT pt.id)
            FROM {rel} rel
            JOIN product_template pt ON pt.id = rel.{col_tmpl}
            WHERE pt.active = TRUE AND pt.sale_ok = TRUE
            GROUP BY rel.{col_cat}
        """)
        direct = dict(env.cr.fetchall())

        # ── Remontée aux ancêtres via parent_path ──────────────────────
        total_count = {c.id: 0 for c in cats}
        by_id = {c.id: c for c in cats}
        for cat in cats:
            n = direct.get(cat.id, 0)
            if not n:
                continue
            path = (cat.parent_path or '').strip('/')
            for part in path.split('/'):
                if not part:
                    continue
                aid = int(part)
                if aid in total_count:
                    total_count[aid] += n

        child_count = {}
        for c in cats:
            if c.parent_id:
                child_count[c.parent_id.id] = child_count.get(c.parent_id.id, 0) + 1

        def serialize(cat):
            depth = len((cat.parent_path or '').strip('/').split('/')) - 1
            return {
                'id':            cat.id,
                'name':          cat.name,
                'parent_id':     cat.parent_id.id if cat.parent_id else None,
                'parent_name':   cat.parent_id.name if cat.parent_id else None,
                'depth':         max(0, depth),
                'path':          ' › '.join(
                    by_id[int(p)].name
                    for p in (cat.parent_path or '').strip('/').split('/')
                    if p and int(p) in by_id
                ),
                'product_count': total_count.get(cat.id, 0),
                'direct_count':  direct.get(cat.id, 0),
                'child_count':   child_count.get(cat.id, 0),
                'has_children':  child_count.get(cat.id, 0) > 0,
            }

        if full:
            return {
                'categories': [serialize(c) for c in cats],
                'full': True,
                'total': len(cats),
            }

        if parent_id:
            try:
                pid = int(parent_id)
            except (ValueError, TypeError):
                pid = False
            selection = cats.filtered(lambda c: c.parent_id.id == pid)
        else:
            selection = cats.filtered(lambda c: not c.parent_id)

        out = [serialize(c) for c in selection]
        if not parent_id:
            out = [c for c in out if c['product_count'] > 0]
        return {'categories': out, 'full': False}

    def _categories_internal_fallback(self, parent_id=None):
        """Repli sur les catégories internes si aucune catégorie e-commerce."""
        env = request.env
        int_domain = []
        if parent_id:
            try:
                int_domain.append(('parent_id', '=', int(parent_id)))
            except (ValueError, TypeError):
                int_domain.append(('parent_id', '=', False))
        else:
            int_domain.append(('parent_id', '=', False))

        result = []
        for cat in env['product.category'].sudo().search(int_domain, order='name asc'):
            count = env['product.template'].sudo().search_count([
                ('sale_ok', '=', True),
                ('active', '=', True),
                ('categ_id', 'child_of', cat.id),
            ])
            if count == 0:
                continue
            result.append({
                'id':            cat.id,
                'name':          cat.name,
                'parent_id':     cat.parent_id.id if cat.parent_id else None,
                'parent_name':   cat.parent_id.name if cat.parent_id else None,
                'depth':         0,
                'path':          '',
                'product_count': count,
                'direct_count':  count,
                'child_count':   0,
                'has_children':  False,
                'internal':      True,
            })
        return {'categories': result, 'full': False, 'internal': True}

    # ═══════════════════════════════════════════════════════════════════
    #  Fournisseurs actifs
    # ═══════════════════════════════════════════════════════════════════

    @http.route('/pool-checklist/suppliers', type='jsonrpc', auth='user',
                website=True, methods=['POST'], csrf=False)
    def get_suppliers(self, limit=50, **kwargs):
        """Fournisseurs ayant des produits actifs, du plus fourni au moins."""
        env = request.env
        try:
            limit = max(1, min(200, int(limit)))
        except (TypeError, ValueError):
            limit = 50
        env.cr.execute("""
            SELECT rp.id, rp.name, COUNT(DISTINCT pt.id) AS product_count
            FROM product_supplierinfo psi
            JOIN res_partner rp ON rp.id = psi.partner_id
            JOIN product_template pt ON pt.id = psi.product_tmpl_id
            WHERE pt.sale_ok = TRUE AND pt.active = TRUE
            GROUP BY rp.id, rp.name
            HAVING COUNT(DISTINCT pt.id) > 0
            ORDER BY COUNT(DISTINCT pt.id) DESC
            LIMIT %s
        """, (limit,))
        rows = env.cr.fetchall()
        return {'suppliers': [
            {'id': r[0], 'name': r[1], 'product_count': r[2]}
            for r in rows
        ]}

    # ═══════════════════════════════════════════════════════════════════
    #  Proxy IA Anthropic
    # ═══════════════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════════════
    #  Autocomplétion partenaires
    # ═══════════════════════════════════════════════════════════════════

    @http.route('/pool-checklist/search-partner', type='jsonrpc', auth='user',
                website=True, methods=['POST'], csrf=False)
    def search_partner(self, query='', limit=8, **kwargs):
        if not query or len(query.strip()) < 2:
            return {'partners': []}
        q = query.strip()
        partners = request.env['res.partner'].sudo().search([
            '|', '|',
            ('name', 'ilike', q),
            ('email', 'ilike', q),
            ('phone', 'ilike', q),
            ('active', '=', True),
            ('type', '=', 'contact'),
        ], limit=int(limit), order='name asc')
        return {'partners': [
            {'id': p.id, 'name': p.name, 'city': p.city or '',
             'street': p.street or '', 'zip': p.zip or '',
             'email': p.email or '', 'phone': p.phone or ''}
            for p in partners
        ]}

    # ═══════════════════════════════════════════════════════════════════
    #  Création devis
    # ═══════════════════════════════════════════════════════════════════

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

        # Marge du devis, pour retour immédiat à l'écran.
        margin_total = None
        if self._can_see_cost():
            try:
                revenue = sum(l.price_subtotal for l in order.order_line)
                cost = 0.0
                for l in order.order_line:
                    if not l.product_id:
                        continue
                    c = l.product_id.standard_price or 0.0
                    best = self._best_seller(l.product_id.product_tmpl_id,
                                             l.product_uom_qty or 1.0)
                    if best and (best.price or 0):
                        c = self._seller_price_company_currency(best)
                    cost += c * (l.product_uom_qty or 0.0)
                margin_total = {
                    'revenue': revenue,
                    'cost': cost,
                    'margin': revenue - cost,
                    'margin_pct': round((revenue - cost) / revenue * 100, 1)
                                  if revenue else 0.0,
                }
            except Exception as e:
                _logger.warning('[pool_checklist] Marge devis non calculee: %s', e)

        return {
            'order_id':     order.id,
            'name':         order.name,
            'partner_name': partner.name,
            'margin':       margin_total,
            'url':          f'{base.rstrip("/")}/odoo/sales/{order.id}',
        }

    # ═══════════════════════════════════════════════════════════════════
    #  Création rendez-vous calendrier
    # ═══════════════════════════════════════════════════════════════════

    @http.route('/pool-checklist/create-event', type='jsonrpc', auth='user',
                website=True, methods=['POST'], csrf=False)
    def create_event(self, partner_id=None, partner_name='', title='',
                     start_local='', duration=2.0, location='',
                     description='', reminder_minutes=None, fiche_id=None,
                     intervention_type='', **kwargs):
        """
        Crée un calendar.event natif Odoo pour une visite chantier.

        start_local : 'YYYY-MM-DD HH:MM' exprimé dans le fuseau de
                      l'utilisateur — converti en UTC pour le stockage.
        duration    : durée en heures (float).
        """
        env = request.env
        user = env.user

        if not start_local:
            return {'error': 'Date et heure manquantes'}

        # ── Conversion fuseau utilisateur -> UTC ───────────────────────
        try:
            naive = datetime.strptime(start_local.strip()[:16], '%Y-%m-%d %H:%M')
        except ValueError:
            return {'error': "Format de date invalide (attendu AAAA-MM-JJ HH:MM)"}

        tz_name = user.tz or 'Europe/Brussels'
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.timezone('Europe/Brussels')

        start_utc = tz.localize(naive).astimezone(pytz.utc).replace(tzinfo=None)
        try:
            hours = float(duration) or 2.0
        except (TypeError, ValueError):
            hours = 2.0
        hours = max(0.25, min(12.0, hours))
        stop_utc = start_utc + timedelta(hours=hours)

        # ── Partenaire ─────────────────────────────────────────────────
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
            partner = Partner.search(
                [('name', 'ilike', partner_name.strip()), ('type', '=', 'contact')],
                limit=1) or None

        attendees = [user.partner_id.id]
        if partner and partner.id not in attendees:
            attendees.append(partner.id)

        # ── Lien de retour vers la fiche ───────────────────────────────
        base = env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        body = description or ''
        if fiche_id:
            link = f'{base.rstrip("/")}/visite-chantier?fiche_id={fiche_id}'
            body += (
                f'\n\nFiche de visite : {link}'
                '\n(la fiche est stockée dans le navigateur qui l\'a créée)'
            )

        vals = {
            'name': title or 'Visite chantier',
            'start': start_utc,
            'stop': stop_utc,
            'duration': hours,
            'allday': False,
            'location': location or '',
            'description': body.strip(),
            'user_id': user.id,
            'partner_ids': [(6, 0, attendees)],
        }

        # ── Rappel ─────────────────────────────────────────────────────
        if reminder_minutes:
            try:
                mins = int(reminder_minutes)
            except (TypeError, ValueError):
                mins = 0
            if mins > 0:
                Alarm = env['calendar.alarm'].sudo()
                alarm = Alarm.search([
                    ('alarm_type', '=', 'notification'),
                    ('duration_minutes', '=', mins),
                ], limit=1)
                if not alarm:
                    unit, qty = ('minutes', mins)
                    if mins % 1440 == 0:
                        unit, qty = ('days', mins // 1440)
                    elif mins % 60 == 0:
                        unit, qty = ('hours', mins // 60)
                    alarm = Alarm.create({
                        'name': f'{qty} {unit} avant',
                        'alarm_type': 'notification',
                        'interval': unit,
                        'duration': qty,
                    })
                vals['alarm_ids'] = [(6, 0, [alarm.id])]

        try:
            event = env['calendar.event'].sudo().create(vals)
        except Exception as e:
            _logger.exception('[pool_checklist] Creation evenement echouee')
            return {'error': str(e)}

        return {
            'event_id': event.id,
            'name': event.name,
            'start_local': naive.strftime('%d/%m/%Y à %H:%M'),
            'duration': hours,
            'partner_name': partner.name if partner else '',
            'url': f'{base.rstrip("/")}/odoo/calendar/{event.id}',
        }
