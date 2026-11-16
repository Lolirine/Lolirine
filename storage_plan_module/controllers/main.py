# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import io
import base64

from .plan_layout import (PLAN_LAYOUT, PLAN_VIEWBOX, STATUS_TO_PLAN, PLAN_DEFAULT,
                          PLAN_COLORS, PLAN_LABELS, PLAN_LEGEND_ORDER)

SITE_POOL_STORE = 6


def _rgba(hex_color, alpha):
    h = hex_color.lstrip('#')
    return 'rgba(%d, %d, %d, %s)' % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def sitemap_storage_plan(env, rule, qs):
    """Sitemap : le plan des boxes n'est liste que hors du site Pool Store."""
    if env['website'].get_current_website().id == SITE_POOL_STORE:
        return
    loc = '/storage/plan'
    if not qs or qs.lower() in loc:
        yield {'loc': loc}


class StoragePlanController(http.Controller):
    
    @http.route('/storage/plan', type='http', auth='public', website=True, sitemap=sitemap_storage_plan)
    def storage_plan(self, **kwargs):
        """Page principale du plan interactif"""
        # Récupérer tous les boxes actifs
        all_boxes = request.env['storage.box'].sudo().search([('active', '=', True)])
        
        # Créer un dictionnaire indexé par nom de box
        boxes_dict = {}
        boxes_list = []  # Pour le calculateur de volume
        for box in all_boxes:
            date_available_str = ''
            if box.date_available:
                date_available_str = box.date_available.strftime('%d/%m/%Y')
            
            box_data = {
                'id': box.id,
                'name': box.name,
                'surface': round(box.surface, 1),
                'volume': round(box.volume, 1),
                'status': box.status,
                'status_color': box.get_status_color(),
                'date_available': date_available_str,
                'floor': box.floor_id.name if box.floor_id else '',
                'price_monthly': box.price_monthly,
            }
            boxes_dict[box.name] = box_data
            
            # Ajouter à la liste pour le calculateur (boxes disponibles uniquement)
            if box.status == 'disponible':
                boxes_list.append(box_data)
        
        # Trier les boxes disponibles par volume
        boxes_list.sort(key=lambda x: x['volume'])
        
        # ---- Plan du hangar : même vue que www.lolirine.be (SVG par niveau) ----
        by_code = {b.name: b for b in all_boxes}

        def plan_status(box):
            # un box en usage personnel n'est pas à louer : affiché comme occupé
            if getattr(box, 'is_personal_use', False):
                return 'occupe'
            return STATUS_TO_PLAN.get(box.status, PLAN_DEFAULT)

        plan_floors = []
        for floor_title, shapes in PLAN_LAYOUT:
            floor_shapes = []
            for code, x, y, w, h, tech in shapes:
                shape = {
                    'code': code, 'x': x, 'y': y, 'w': w, 'h': h, 'tech': tech,
                    'tx': x + w - 2, 'ty': y + 10, 'vx': x + 1, 'vy': y + h - 1,
                }
                if not tech:
                    box = by_code.get(code)
                    if not box:
                        continue
                    st = plan_status(box)
                    tip = '%s — %s' % (code, PLAN_LABELS[st])
                    if st == 'bientot_libre' and box.date_available:
                        tip += ' (le %s)' % box.date_available.strftime('%d/%m/%Y')
                    tip += ' — %s m³ — %d €/mois' % (('%.1f' % box.volume).replace('.', ','), round(box.price_monthly))
                    shape.update({
                        'id': box.id, 'status': st, 'fill': PLAN_COLORS[st],
                        'vol': '%.1f' % box.volume, 'tip': tip,
                    })
                floor_shapes.append(shape)
            plan_floors.append({'title': floor_title, 'shapes': floor_shapes})

        # Liste « disponible maintenant ou prochainement »
        floor_of = {sh[0]: title for title, shapes in PLAN_LAYOUT for sh in shapes}
        plan_available = []
        for box in all_boxes.sorted(lambda b: (b.status != 'disponible', b.volume, b.name)):
            st = plan_status(box)
            if st not in ('libre', 'bientot_libre'):
                continue
            plan_available.append({
                'id': box.id,
                'code': box.name,
                'floor': floor_of.get(box.name) or (box.floor_id.name if box.floor_id else ''),
                'dims': '%s × %s × %s m' % tuple(('%.2f' % (v / 100.0)).replace('.', ',') for v in (box.depth, box.width, box.height)),
                'vol': ('%.1f' % box.volume).replace('.', ','),
                'price': ('%.2f' % box.price_monthly).replace('.', ','),
                'status': st,
                'dispo': ('Libre immédiatement' if st == 'libre'
                          else ('Libre le %s' % box.date_available.strftime('%d/%m/%Y') if box.date_available
                                else 'Libre prochainement')),
            })

        # Légende : mêmes couleurs que le plan
        status_legend = [{'label': PLAN_LABELS[k], 'color': _rgba(PLAN_COLORS[k], 0.4)} for k in PLAN_LEGEND_ORDER]
        status_legend.append({'label': 'Local technique', 'color': '#ffffff'})
        
        # Récupérer les catégories et meubles pour le calculateur
        FurnitureCategory = request.env['storage.furniture.category'].sudo()
        categories = FurnitureCategory.search([('active', '=', True)], order='sequence')
        
        furniture_data = []
        for cat in categories:
            cat_data = {
                'id': cat.id,
                'name': cat.name,
                'icon': cat.icon or 'fa-box',
                'furniture': []
            }
            for furniture in cat.furniture_ids.filtered(lambda f: f.active):
                cat_data['furniture'].append({
                    'id': furniture.id,
                    'name': furniture.name,
                    'width': furniture.width,
                    'depth': furniture.depth,
                    'height': furniture.height,
                    'volume': round(furniture.volume, 3),
                    'color': furniture.color_3d or '#3498db',
                })
            if cat_data['furniture']:  # Ne pas inclure les catégories vides
                furniture_data.append(cat_data)
        
        return request.render('storage_plan_module.storage_plan_page', {
            'boxes': boxes_dict,
            'boxes_list': boxes_list,
            'status_legend': status_legend,
            'plan_floors': plan_floors,
            'plan_available': plan_available,
            'plan_viewbox': '0 0 %d %d' % PLAN_VIEWBOX,
            'furniture_categories': furniture_data,
        })
    
    @http.route('/storage/boxes/export/xlsx', type='http', auth='user')
    def export_boxes_xlsx(self, **kwargs):
        """Exporte les boxes vers un fichier XLSX"""
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            return request.make_response(
                "Module openpyxl non installé. Veuillez l'installer avec: pip install openpyxl",
                headers=[('Content-Type', 'text/plain')]
            )
        
        # Créer le workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Boxes"
        
        # Styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # En-têtes
        headers = [
            'name', 'floor', 'floor_code', 'width', 'depth', 'height',
            'volume', 'surface', 'price_monthly', 'registration_fee',
            'deposit_months', 'status', 'date_available', 'aisle',
            'description', 'active'
        ]
        
        headers_labels = [
            'Nom du Box', 'Étage', 'Code Étage', 'Largeur (cm)', 'Profondeur (cm)', 'Hauteur (cm)',
            'Volume (m³)', 'Surface (m²)', 'Prix Mensuel (€)', 'Frais Dossier (€)',
            'Caution (mois)', 'Statut', 'Date Disponibilité', 'Allée',
            'Description', 'Actif'
        ]
        
        for col, (header, label) in enumerate(zip(headers, headers_labels), 1):
            cell = ws.cell(row=1, column=col, value=label)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border
        
        # Données
        Box = request.env['storage.box'].sudo()
        data = Box.get_export_data()
        
        for row_num, row_data in enumerate(data, 2):
            for col, header in enumerate(headers, 1):
                value = row_data.get(header, '')
                if header == 'active':
                    value = 'Oui' if value else 'Non'
                cell = ws.cell(row=row_num, column=col, value=value)
                cell.border = border
        
        # Ajuster les largeurs de colonnes
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15
        
        # Générer le fichier
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = "boxes_export.xlsx"
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
            ]
        )
    
    @http.route('/storage/box/<int:box_id>/details', type='jsonrpc', auth='public')
    def box_details(self, box_id, **kwargs):
        """Récupère les détails d'un box"""
        box = request.env['storage.box'].sudo().browse(box_id)
        if not box.exists():
            return {'error': 'Box non trouvé'}
        
        return box.get_box_details()
    
    @http.route('/storage/box/<int:box_id>/reserve', type='jsonrpc', auth='public')
    def reserve_box(self, box_id, customer_name, customer_email, customer_phone, 
                    reservation_type='reservation', notes='', **kwargs):
        """Crée une réservation pour un box"""
        box = request.env['storage.box'].sudo().browse(box_id)
        if not box.exists():
            return {'error': 'Box non trouvé'}
        
        if box.status != 'disponible':
            return {'error': 'Ce box n\'est pas disponible'}
        
        try:
            reservation = request.env['box.reservation'].sudo().create({
                'box_id': box_id,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
                'reservation_type': reservation_type,
                'notes': notes,
                'state': 'pending',
            })
            
            # Mettre à jour le statut du box
            box.status = 'reserve'
            
            return {
                'success': True,
                'reservation_id': reservation.id,
                'reservation_ref': reservation.name,
                'message': 'Réservation créée avec succès'
            }
        except Exception as e:
            return {'error': str(e)}
    
    @http.route('/storage/box/<int:box_id>/appointment', type='jsonrpc', auth='public')
    def book_appointment(self, box_id, customer_name, customer_email, customer_phone, 
                        appointment_date=None, notes='', **kwargs):
        """Crée une demande de rendez-vous pour un box"""
        box = request.env['storage.box'].sudo().browse(box_id)
        if not box.exists():
            return {'error': 'Box non trouvé'}
        
        try:
            reservation_vals = {
                'box_id': box_id,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
                'reservation_type': 'appointment',
                'notes': notes,
                'state': 'pending',
            }
            
            if appointment_date:
                reservation_vals['appointment_date'] = appointment_date
            
            reservation = request.env['box.reservation'].sudo().create(reservation_vals)
            
            return {
                'success': True,
                'reservation_id': reservation.id,
                'reservation_ref': reservation.name,
                'message': 'Demande de rendez-vous créée avec succès'
            }
        except Exception as e:
            return {'error': str(e)}
    
    @http.route('/storage/boxes/search', type='jsonrpc', auth='public')
    def search_boxes(self, status=None, min_volume=None, max_volume=None, 
                     min_price=None, max_price=None, floor_id=None, **kwargs):
        """Recherche des boxes selon des critères"""
        domain = [('active', '=', True)]
        
        if status:
            domain.append(('status', '=', status))
        if min_volume:
            domain.append(('volume', '>=', float(min_volume)))
        if max_volume:
            domain.append(('volume', '<=', float(max_volume)))
        if min_price:
            domain.append(('price_monthly', '>=', float(min_price)))
        if max_price:
            domain.append(('price_monthly', '<=', float(max_price)))
        if floor_id:
            domain.append(('floor_id', '=', int(floor_id)))
        
        boxes = request.env['storage.box'].sudo().search(domain)
        
        results = []
        for box in boxes:
            results.append(box.get_box_details())
        
        return {
            'success': True,
            'boxes': results,
            'count': len(results)
        }
