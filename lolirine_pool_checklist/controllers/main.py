# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)
POOL_STORE_WEBSITE_ID = 6
POOL_STORE_ACTION_ID  = 4402   # action pool.store.quote (confirmé via shell)

SUPPLIER_NAMES = {
    'fluidra': ['Fluidra', 'SIBO', 'Fluidra/SIBO'],
    'scp':     ['SCP', 'SCP Bénélux', 'SCP Benelux'],
}

class PoolChecklistController(http.Controller):

    # ── Page principale ───────────────────────────────────────────────────
    @http.route('/visite-chantier', type='http', auth='public', website=True,
                methods=['GET'], sitemap=False)
    def checklist_page(self, **kwargs):
        user      = request.env.user
        is_logged = not user._is_public()
        google_key = request.env['ir.config_parameter'].sudo().get_param(
            'google_address_autocomplete.google_places_api_key', default='')
        return request.render('lolirine_pool_checklist.page_checklist', {
            'website_id':   POOL_STORE_WEBSITE_ID,
            'is_logged_in': is_logged,
            'user_name':    user.name if is_logged else '',
            'lpc_user_id':  user.id   if is_logged else 0,
            'google_key':   google_key,
        })

    # ── Recherche produits ────────────────────────────────────────────────
    @http.route('/pool-checklist/products', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def search_products(self, query='', limit=24, supplier=None, **kwargs):
        if not query or not query.strip():
            return {'products': [], 'error': None}
        try:
            PT     = request.env['product.template'].sudo()
            domain = [
                ('website_id', '=', POOL_STORE_WEBSITE_ID),
                '|', ('name', 'ilike', query),
                     ('description_sale', 'ilike', query),
            ]
            if supplier and supplier in SUPPLIER_NAMES:
                names = SUPPLIER_NAMES[supplier]
                sd    = [('seller_ids.partner_id.name', 'ilike', n) for n in names]
                od    = (['|'] * (len(sd) - 1)) + sd if len(sd) > 1 else sd
                domain += od
            products = PT.search_read(domain,
                fields=['id','name','default_code','list_price','categ_id',
                        'description_sale','website_url','seller_ids'],
                limit=int(limit), order='name asc')
            return {'products': self._format_products(products), 'error': None}
        except Exception as e:
            _logger.error('[pool_checklist] search: %s', e)
            return {'products': [], 'error': str(e)}

    # ── Catégories Pool Store ─────────────────────────────────────────────
    @http.route('/pool-checklist/categories', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def get_categories(self, **kwargs):
        try:
            PT = request.env['product.template'].sudo()
            # Tous les produits du Pool Store (website_id=6), publiés ou non
            domain = [('website_id', '=', POOL_STORE_WEBSITE_ID)]
            products = PT.search(domain, limit=3000)
            _logger.info('[pool_checklist] categories: %d products found', len(products))
            cats = {}
            for p in products:
                # Utiliser les catégories publiques eCommerce (public_categ_ids)
                # plutôt que les catégories internes (categ_id)
                pub_cats = []
                try:
                    pub_cats = p.public_categ_ids
                except Exception:
                    pass
                if pub_cats:
                    for c in pub_cats:
                        if c.id not in cats:
                            cats[c.id] = {
                                'id':    c.id,
                                'name':  c.name,
                                'full':  getattr(c, 'complete_name', None) or c.name,
                                'count': 0,
                            }
                        cats[c.id]['count'] += 1
                else:
                    # Fallback sur categ_id interne si pas de catégorie publique
                    c = p.categ_id
                    if c and c.id:
                        if c.id not in cats:
                            cats[c.id] = {
                                'id':    c.id,
                                'name':  c.name,
                                'full':  getattr(c, 'complete_name', None) or c.name,
                                'count': 0,
                            }
                        cats[c.id]['count'] += 1
            result = sorted(cats.values(), key=lambda x: (-x['count'], x['name']))
            _logger.info('[pool_checklist] categories: %d categories', len(result))
            return {'categories': result}
        except Exception as e:
            _logger.error('[pool_checklist] categories: %s', e)
            return {'categories': [], 'error': str(e)}

    # ── Produits par catégorie ────────────────────────────────────────────
    @http.route('/pool-checklist/products-by-category', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def products_by_category(self, category_id=None, query='', limit=60, **kwargs):
        try:
            PT     = request.env['product.template'].sudo()
            # Tous les produits du Pool Store (website_id=6)
            domain = [('website_id', '=', POOL_STORE_WEBSITE_ID)]
            if category_id:
                try:
                    domain.append(('public_categ_ids', 'in', [int(category_id)]))
                except Exception:
                    domain.append(('categ_id', '=', int(category_id)))
            if query:
                domain += ['|', ('name','ilike',query), ('default_code','ilike',query)]
            products = PT.search_read(domain,
                fields=['id','name','default_code','list_price','categ_id',
                        'description_sale','website_url','seller_ids'],
                limit=int(limit), order='name asc')
            # Tri : fournisseurs connus en tête
            raw     = self._format_products(products)
            known   = [p for p in raw if any(s['type'] in ('fluidra','scp') for s in p.get('suppliers',[]))]
            other   = [p for p in raw if p not in known]
            return {'products': known + other}
        except Exception as e:
            _logger.error('[pool_checklist] products-by-category: %s', e)
            return {'products': [], 'error': str(e)}

    def _format_products(self, products):
        """Formate une liste de product.template pour le frontend."""
        result = []
        for p in products:
            supplier_info = []
            if p.get('seller_ids'):
                sellers = request.env['product.supplierinfo'].sudo().browse(p['seller_ids'])
                for s in sellers:
                    sname = s.partner_id.name or ''
                    supplier_info.append({
                        'name':  sname,
                        'ref':   s.product_code or '',
                        'price': s.price or 0.0,
                        'type':  'fluidra' if any(k.lower() in sname.lower() for k in ['fluidra','sibo'])
                                 else 'scp' if any(k.lower() in sname.lower() for k in ['scp'])
                                 else 'other'
                    })
            result.append({
                'id':        p['id'],
                'name':      p['name'],
                'ref':       p.get('default_code') or '',
                'price':     p.get('list_price', 0.0),
                'category':  p['categ_id'][1] if p.get('categ_id') else '',
                'image':     f"/web/image/product.template/{p['id']}/image_512",
                'unit':      'pièce',
                'suppliers': supplier_info,
            })
        return result

    # ── Recherche partenaires ─────────────────────────────────────────────
    @http.route('/pool-checklist/partners', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def search_partners(self, query='', limit=8, **kwargs):
        if not query or len(query) < 2:
            return {'partners': []}
        try:
            partners = request.env['res.partner'].sudo().search_read(
                [('name', 'ilike', query), ('active', '=', True)],
                fields=['id','name','street','city','zip','country_id',
                        'phone','mobile','email','vat','company_name','is_company'],
                limit=int(limit), order='name asc')
            result = []
            for p in partners:
                result.append({**{k:v for k,v in p.items() if k!='country_id'},
                    'country': p['country_id'][1] if p.get('country_id') else '',
                    'vat':          p.get('vat') or '',
                    'company_name': p.get('company_name') or '',
                    'is_company':   p.get('is_company') or False,
                })
            return {'partners': result}
        except Exception as e:
            _logger.error('[pool_checklist] partners: %s', e)
            return {'partners': []}

    # ── Sauvegarder une fiche ─────────────────────────────────────────────
    @http.route('/pool-checklist/save', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def save_report(self, data=None, **kwargs):
        if not data:
            return {'error': 'No data'}
        try:
            Report = request.env['pool.checklist.report'].sudo()
            vals   = {
                'client_name':       data.get('nom', ''),
                'address':           data.get('adresse', ''),
                'tel':               data.get('tel', ''),
                'date':              data.get('date') or False,
                'ref_dossier':       data.get('ref', ''),
                'intervention_type': data.get('intervention', 'entretien'),
                'plan_type':         data.get('plan') or False,
                'technician_id':     request.env.user.id,
                'checklist_data':    json.dumps(data.get('checklist', {})),
                'linked_products_data': json.dumps(data.get('products', [])),
                'notes':             data.get('notes', ''),
                'state':             'draft',
            }
            if data.get('partner_id'):
                vals['partner_id'] = int(data['partner_id'])
            for sig_field in ('signature_technicien', 'signature_client'):
                sig = data.get(sig_field)
                if sig and sig.startswith('data:image'):
                    vals[sig_field] = sig.split(',', 1)[1]
            report_id = data.get('report_id')
            if report_id:
                report = Report.browse(int(report_id))
                if report.exists():
                    report.write(vals)
                else:
                    report = Report.create(vals)
            else:
                report = Report.create(vals)
            return {'success': True, 'report_id': report.id, 'name': report.name}
        except Exception as e:
            _logger.error('[pool_checklist] save: %s', e)
            return {'error': str(e)}

    # ── Charger une fiche ─────────────────────────────────────────────────
    @http.route('/pool-checklist/load/<int:report_id>', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def load_report(self, report_id, **kwargs):
        try:
            report = request.env['pool.checklist.report'].sudo().browse(report_id)
            if not report.exists():
                return {'error': 'Not found'}
            return {'success': True, 'data': {
                'report_id':    report.id,
                'name':         report.name,
                'partner_id':   report.partner_id.id if report.partner_id else None,
                'nom':          report.partner_id.name if report.partner_id else report.client_name,
                'adresse':      report.address or '',
                'tel':          report.tel or '',
                'date':         str(report.date) if report.date else '',
                'ref':          report.ref_dossier or '',
                'technicien':   report.technician_id.name if report.technician_id else '',
                'intervention': report.intervention_type or '',
                'plan':         report.plan_type or '',
                'checklist':    json.loads(report.checklist_data or '{}'),
                'products':     json.loads(report.linked_products_data or '[]'),
                'notes':        report.notes or '',
                'state':        report.state,
            }}
        except Exception as e:
            _logger.error('[pool_checklist] load: %s', e)
            return {'error': str(e)}

    # ── Liste des fiches ──────────────────────────────────────────────────
    @http.route('/pool-checklist/list', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def list_reports(self, limit=20, **kwargs):
        try:
            reports = request.env['pool.checklist.report'].sudo().search_read(
                [('technician_id', '=', request.env.user.id)],
                fields=['id','name','display_name','date','intervention_type',
                        'state','completion_pct','items_action','partner_id',
                        'client_name','estimate_total'],
                limit=int(limit), order='date desc, id desc')
            for r in reports:
                r['partner_name'] = r['partner_id'][1] if r.get('partner_id') else r.get('client_name','')
            return {'reports': reports}
        except Exception as e:
            _logger.error('[pool_checklist] list: %s', e)
            return {'reports': [], 'error': str(e)}

    # ── Créer un devis Pool Store ─────────────────────────────────────────
    @http.route('/pool-checklist/create-quote', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def create_quote(self, report_id=None, products=None, extra_lines=None,
                     client=None, notes=None, **kwargs):
        try:
            products    = products    or []
            extra_lines = extra_lines or []
            client      = client      or {}

            # ── Partenaire ─────────────────────────────────────────────
            partner = None
            pid = client.get('partner_id')
            if pid:
                partner = request.env['res.partner'].sudo().browse(int(pid))
                if not partner.exists():
                    partner = None
            if not partner:
                nom = (client.get('nom') or '').strip()
                if nom:
                    partner = request.env['res.partner'].sudo().search(
                        [('name','=',nom)], limit=1)
                if not partner and nom:
                    partner = request.env['res.partner'].sudo().create({
                        'name':         nom,
                        'street':       client.get('rue',''),
                        'zip':          client.get('cp',''),
                        'city':         client.get('ville',''),
                        'phone':        client.get('tel',''),
                        'vat':          client.get('tva','') or False,
                        'is_company':   client.get('type','') == 'professionnel',
                    })
            if not partner:
                partner = request.env['res.partner'].sudo().search(
                    [('user_ids','=',request.env.user.id)], limit=1)

            # ── Séquence LPS-DEVIS ──────────────────────────────────────
            seq_val = request.env['ir.sequence'].sudo().next_by_code('pool.store.quote')
            if not seq_val:
                from datetime import datetime
                yr  = datetime.now().year
                cnt = request.env['pool.store.quote'].sudo().search_count([]) + 1
                seq_val = f"LPS-DEVIS/{yr}/{str(cnt).zfill(4)}"
            _logger.info('[pool_checklist] quote sequence: %s', seq_val)

            # ── Créer le devis pool.store.quote ────────────────────────
            quote_vals = {
                'name':           seq_val,
                'partner_id':     partner.id,
                'partner_type':   client.get('type', 'particulier'),
                'address_site':   ' '.join(filter(None,[
                    client.get('rue',''), client.get('cp',''), client.get('ville','')
                ])).strip(),
                'notes_internal': notes or '',
                'user_id':        request.env.user.id,
            }
            if report_id:
                checklist = request.env['pool.checklist.report'].sudo().browse(int(report_id))
                if checklist.exists():
                    quote_vals['checklist_id']      = checklist.id
                    quote_vals['intervention_type'] = checklist.intervention_type or False

            quote = request.env['pool.store.quote'].sudo().create(quote_vals)
            _logger.info('[pool_checklist] quote created: %s id=%s', quote.name, quote.id)

            # ── Lignes produits ─────────────────────────────────────────
            seq = 10
            for p in products:
                pt_id   = p.get('id', 0)
                product = None
                if pt_id:
                    pt = request.env['product.template'].sudo().browse(int(pt_id))
                    if pt.exists():
                        product = pt.product_variant_id
                suppliers = p.get('suppliers', [])
                main_s    = next((s for s in suppliers if s.get('type') in ('fluidra','scp')),
                                  suppliers[0] if suppliers else {})
                request.env['pool.store.quote.line'].sudo().create({
                    'quote_id':       quote.id,
                    'sequence':       seq,
                    'line_type':      'product',
                    'product_id':     product.id if product else False,
                    'name':           p.get('name',''),
                    'ref':            p.get('ref',''),
                    'supplier_ref':   main_s.get('ref',''),
                    'supplier_price': main_s.get('price',0) or 0,
                    'qty':            p.get('qty', 1),
                    'unit':           p.get('unit','pièce'),
                    'unit_price':     p.get('price', 0) or 0,
                })
                seq += 10

            # ── Lignes extras (MO, évacuation, déplacement) ─────────────
            type_map = {
                'MO-HORAIRE':'labor', 'MO-FORFAIT':'labor',
                'EVAC-FORFAIT':'disposal', 'EVAC-CLIENT':'disposal',
                'DEPL':'travel'
            }
            for el in extra_lines:
                if not el.get('name'):
                    continue
                request.env['pool.store.quote.line'].sudo().create({
                    'quote_id':   quote.id,
                    'sequence':   seq,
                    'line_type':  type_map.get(el.get('ref',''), 'labor'),
                    'name':       el.get('name',''),
                    'ref':        el.get('ref',''),
                    'qty':        el.get('qty', 1),
                    'unit_price': el.get('price', 0) or 0,
                })
                seq += 10

            # ── Lier la fiche ───────────────────────────────────────────
            if report_id:
                request.env['pool.checklist.report'].sudo().browse(int(report_id)).write(
                    {'state': 'done'})

            return {
                'success':    True,
                'quote_id':   quote.id,
                'quote_name': quote.name,
            }
        except Exception as e:
            _logger.error('[pool_checklist] create-quote error: %s', e, exc_info=True)
            return {'error': str(e)}

    # ── URL backend du devis ──────────────────────────────────────────────
    @http.route('/pool-checklist/quote-url', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def get_quote_url(self, quote_id=None, **kwargs):
        action = request.env['ir.actions.act_window'].sudo().search(
            [('res_model', '=', 'pool.store.quote')], limit=1)
        action_id = action.id if action else POOL_STORE_ACTION_ID
        if quote_id:
            return {'url': f'/odoo/action-{action_id}/{quote_id}'}
        return {'url': f'/odoo/action-{action_id}'}

    # ── Ping ─────────────────────────────────────────────────────────────
    @http.route('/pool-checklist/ping', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def ping(self, **kwargs):
        return {'status': 'ok', 'user': request.env.user.name}
