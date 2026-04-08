# -*- coding: utf-8 -*-
import json
import logging
import base64
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)
POOL_STORE_WEBSITE_ID = 6

SUPPLIER_NAMES = {
    'fluidra': ['Fluidra', 'SIBO', 'Fluidra/SIBO'],
    'scp':     ['SCP', 'SCP Bénélux', 'SCP Benelux'],
}

class PoolChecklistController(http.Controller):

    # ── Page principale ───────────────────────────────────────────────────
    @http.route('/visite-chantier', type='http', auth='public', website=True,
                methods=['GET'], sitemap=False)
    def checklist_page(self, **kwargs):
        user = request.env.user
        is_logged = not user._is_public()
        # Récupérer la clé Google Maps depuis les paramètres système
        google_key = request.env['ir.config_parameter'].sudo().get_param(
            'google.api_key', default='')
        return request.render('lolirine_pool_checklist.page_checklist', {
            'website_id':  POOL_STORE_WEBSITE_ID,
            'is_logged_in': is_logged,
            'user_name':   user.name if is_logged else '',
            'lpc_user_id':  user.id if is_logged else 0,
            'google_key':  google_key,
        })

    # ── Recherche produits ────────────────────────────────────────────────
    @http.route('/pool-checklist/products', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def search_products(self, query='', limit=24, supplier=None, **kwargs):
        if not query or not query.strip():
            return {'products': [], 'error': None}
        try:
            PT = request.env['product.template'].sudo()
            domain = [
                ('website_published', '=', True),
                '|', ('website_id', '=', POOL_STORE_WEBSITE_ID),
                     ('website_id', '=', False),
                '|', ('name', 'ilike', query),
                     ('description_sale', 'ilike', query),
            ]
            if supplier and supplier in SUPPLIER_NAMES:
                names = SUPPLIER_NAMES[supplier]
                sd = []
                for n in names:
                    sd.append(('seller_ids.partner_id.name', 'ilike', n))
                if len(sd) > 1:
                    od = ['|'] * (len(sd) - 1) + sd
                    domain += od
                else:
                    domain += sd

            products = PT.search_read(domain,
                fields=['id','name','default_code','list_price','categ_id',
                        'description_sale','website_url','seller_ids'],
                limit=int(limit), order='name asc')

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
                    'url':       p.get('website_url') or '',
                    'unit':      'pièce',
                    'suppliers': supplier_info,
                })
            return {'products': result, 'error': None}
        except Exception as e:
            _logger.error('[pool_checklist] search: %s', e)
            return {'products': [], 'error': str(e)}

    # ── Recherche partenaires (autocomplétion) ────────────────────────────
    @http.route('/pool-checklist/partners', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def search_partners(self, query='', limit=8, **kwargs):
        if not query or len(query) < 2:
            return {'partners': []}
        try:
            partners = request.env['res.partner'].sudo().search_read(
                [('name', 'ilike', query), ('active', '=', True)],
                fields=['id','name','street','city','zip','country_id',
                        'phone','mobile','email'],
                limit=int(limit), order='name asc'
            )
            return {'partners': [dict(p, country=p['country_id'][1] if p.get('country_id') else '') for p in partners]}
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
            vals = {
                'client_name':       data.get('nom', ''),
                'address':           data.get('adresse', ''),
                'tel':               data.get('tel', ''),
                'date':              data.get('date') or False,
                'ref_dossier':       data.get('ref', ''),
                'intervention_type': data.get('intervention', 'entretien'),
                'plan_type':         data.get('plan', False) or False,
                'technician_id':     request.env.user.id,
                'checklist_data':    json.dumps(data.get('checklist', {})),
                'linked_products_data': json.dumps(data.get('products', [])),
                'notes':             data.get('notes', ''),
                'state':             'draft',
            }
            # Lier au partenaire si trouvé
            partner_id = data.get('partner_id')
            if partner_id:
                vals['partner_id'] = int(partner_id)

            # Signature technicien
            sig_tech = data.get('signature_technicien')
            if sig_tech and sig_tech.startswith('data:image'):
                img_data = sig_tech.split(',', 1)[1]
                vals['signature_technicien'] = img_data

            # Signature client
            sig_client = data.get('signature_client')
            if sig_client and sig_client.startswith('data:image'):
                img_data = sig_client.split(',', 1)[1]
                vals['signature_client'] = img_data

            # Mise à jour ou création
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
            return {
                'success': True,
                'data': {
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
                }
            }
        except Exception as e:
            _logger.error('[pool_checklist] load: %s', e)
            return {'error': str(e)}

    # ── Liste des fiches du technicien connecté ───────────────────────────
    @http.route('/pool-checklist/list', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def list_reports(self, limit=20, **kwargs):
        try:
            reports = request.env['pool.checklist.report'].sudo().search_read(
                [('technician_id', '=', request.env.user.id)],
                fields=['id','name','display_name','date','intervention_type',
                        'state','completion_pct','items_action','partner_id',
                        'client_name','estimate_total'],
                limit=int(limit), order='date desc, id desc'
            )
            for r in reports:
                r['partner_name'] = r['partner_id'][1] if r.get('partner_id') else r.get('client_name','')
            return {'reports': reports}
        except Exception as e:
            _logger.error('[pool_checklist] list: %s', e)
            return {'reports': [], 'error': str(e)}

    # ── Créer un devis depuis les produits liés ───────────────────────────
    @http.route('/pool-checklist/create-quote', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def create_quote(self, report_id=None, products=None, client=None, **kwargs):
        try:
            products = products or []
            # Trouver ou créer le partenaire
            partner = None
            if client and client.get('partner_id'):
                partner = request.env['res.partner'].sudo().browse(int(client['partner_id']))
            elif client and client.get('nom'):
                partner = request.env['res.partner'].sudo().search(
                    [('name', 'ilike', client['nom'])], limit=1)
                if not partner:
                    partner = request.env['res.partner'].sudo().create({
                        'name': client['nom'],
                        'street': client.get('adresse', ''),
                        'phone': client.get('tel', ''),
                    })
            if not partner:
                partner = request.env['res.partner'].sudo().browse(
                    request.env['ir.model.data'].sudo()._xmlid_to_res_id('base.partner_admin'))

            order = request.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'origin':     f"Fiche visite chantier piscine",
                'note':       f"Devis créé depuis la fiche de visite chantier piscine.",
            })

            for p in products:
                try:
                    pt = request.env['product.template'].sudo().browse(int(p.get('id', 0)))
                    if not pt.exists():
                        continue
                    variant = pt.product_variant_id
                    if not variant:
                        continue
                    request.env['sale.order.line'].sudo().create({
                        'order_id':       order.id,
                        'product_id':     variant.id,
                        'product_uom_qty':p.get('qty', 1),
                        'price_unit':     p.get('price', 0) or variant.lst_price,
                        'name':           p.get('name', variant.name),
                    })
                except Exception as pe:
                    _logger.warning('[pool_checklist] product line error: %s', pe)

            # Lier la fiche si fournie
            if report_id:
                request.env['pool.checklist.report'].sudo().browse(int(report_id)).write({
                    'sale_order_id': order.id, 'state': 'done'
                })

            return {
                'success': True,
                'order_id': order.id,
                'order_name': order.name,
                'url': f'/odoo/sales/{order.id}',
            }
        except Exception as e:
            _logger.error('[pool_checklist] create-quote: %s', e)
            return {'error': str(e)}

    # ── Ping ─────────────────────────────────────────────────────────────
    @http.route('/pool-checklist/ping', type='json', auth='user',
                website=True, methods=['POST'], csrf=False)
    def ping(self, **kwargs):
        return {'status': 'ok', 'user': request.env.user.name}
