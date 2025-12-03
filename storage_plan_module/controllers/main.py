# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class StoragePlanController(http.Controller):
    
    @http.route('/storage/plan', type='http', auth='public', website=True)
    def storage_plan(self, **kwargs):
        """Page principale du plan interactif"""
        floors = request.env['storage.floor'].sudo().search([('active', '=', True)], order='sequence')
        
        floor_data = []
        for floor in floors:
            boxes = floor.box_ids.filtered(lambda b: b.active)
            box_list = []
            for box in boxes:
                box_list.append({
                    'id': box.id,
                    'name': box.name,
                    'surface': round(box.surface, 1),
                    'volume': round(box.volume, 1),
                    'status': box.status,
                    'status_color': box.get_status_color(),
                    'grid_row': box.grid_row,
                    'grid_col': box.grid_col,
                    'position_x': box.position_x,
                    'position_y': box.position_y,
                    'aisle': box.aisle or 'left',
                })
            
            floor_data.append({
                'id': floor.id,
                'name': floor.name,
                'code': floor.code,
                'boxes': box_list,
                'box_count': floor.box_count,
                'available_count': floor.available_box_count,
            })
        
        # Légende des statuts
        status_legend = [
            {'status': 'occupe', 'label': 'Occupé', 'color': '#FFB6C1'},
            {'status': 'disponible', 'label': 'Disponible', 'color': '#90EE90'},
            {'status': 'maintenance', 'label': 'Maintenance', 'color': '#FFFF99'},
            {'status': 'nettoyage', 'label': 'Nettoyage', 'color': '#87CEEB'},
            {'status': 'reserve', 'label': 'Réservé', 'color': '#FFE4B5'},
            {'status': 'bientot_dispo', 'label': 'Bientôt dispo.', 'color': '#E6E6FA'},
            {'status': 'inspection', 'label': 'En inspection', 'color': '#B0C4DE'},
            {'status': 'technique', 'label': 'Technique', 'color': '#D3D3D3'},
        ]
        
        return request.render('storage_plan_module.storage_plan_page', {
            'floors': floor_data,
            'status_legend': status_legend,
        })
    
    @http.route('/storage/box/<int:box_id>/details', type='json', auth='public')
    def box_details(self, box_id, **kwargs):
        """Récupère les détails d'un box"""
        box = request.env['storage.box'].sudo().browse(box_id)
        if not box.exists():
            return {'error': 'Box non trouvé'}
        
        return box.get_box_details()
    
    @http.route('/storage/box/<int:box_id>/reserve', type='json', auth='public')
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
    
    @http.route('/storage/box/<int:box_id>/appointment', type='json', auth='public')
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
    
    @http.route('/storage/boxes/search', type='json', auth='public')
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
