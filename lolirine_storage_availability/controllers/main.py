# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request


class StorageBoxController(http.Controller):
    
    @http.route('/storage_box/get_data/<int:product_id>', type='jsonrpc', auth='public', website=True, cors='*')
    def get_storage_box_data(self, product_id, **kwargs):
        """Endpoint API pour récupérer les données d'un box de stockage"""
        product = request.env['product.template'].sudo().browse(product_id)
        
        if not product.exists() or not product.is_storage_box:
            return {'is_storage_box': False}
        
        config = request.env['ir.config_parameter'].sudo()
        show_badge = config.get_param('lolirine_storage.show_status_badge', 'False') == 'True'
        
        return {
            'is_storage_box': True,
            'storage_status': product.storage_status,
            'storage_status_display': product.storage_status_display,
            'show_badge': show_badge,
            'show_appointment_button': product.show_appointment_button,
            'show_general_inquiry_button': product.show_general_inquiry_button,
            'appointment_url': product.appointment_url or '/appointment',
            'general_inquiry_url': product.general_inquiry_url or '/contactus',
            'appointment_button_label': product.appointment_button_label or 'Contactez-nous',
            'general_inquiry_button_label': product.general_inquiry_button_label or 'Demande générale',
        }

    @http.route('/storage_box/get_data_by_slug/<path:slug>', type='http', auth='public', website=True, csrf=False)
    def get_storage_box_data_by_slug(self, slug, **kwargs):
        """Endpoint HTTP pour récupérer les données via le slug du produit"""
        # Extraire l'ID du slug (format: nom-produit-123)
        product_id = None
        try:
            # Le slug peut contenir des / donc on prend la dernière partie
            slug_part = slug.split('/')[-1] if '/' in slug else slug
            product_id = int(slug_part.split('-')[-1])
        except (ValueError, IndexError):
            pass
        
        # Si pas d'ID trouvé, retourner false
        if not product_id:
            return self._json_response({'is_storage_box': False})
        
        product = request.env['product.template'].sudo().browse(product_id)
        
        if not product.exists() or not product.is_storage_box:
            return self._json_response({'is_storage_box': False})
        
        config = request.env['ir.config_parameter'].sudo()
        show_badge = config.get_param('lolirine_storage.show_status_badge', 'False') == 'True'
        
        data = {
            'is_storage_box': True,
            'storage_status': product.storage_status,
            'storage_status_display': product.storage_status_display,
            'show_badge': show_badge,
            'show_appointment_button': product.show_appointment_button,
            'show_general_inquiry_button': product.show_general_inquiry_button,
            'appointment_url': product.appointment_url or '/appointment',
            'general_inquiry_url': product.general_inquiry_url or '/contactus',
            'appointment_button_label': product.appointment_button_label or 'Contactez-nous',
            'general_inquiry_button_label': product.general_inquiry_button_label or 'Demande générale',
        }
        
        return self._json_response(data)

    def _json_response(self, data):
        """Retourne une réponse JSON avec les bons headers"""
        response = request.make_response(
            json.dumps(data),
            headers=[
                ('Content-Type', 'application/json'),
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
                ('Access-Control-Allow-Headers', 'Content-Type'),
            ]
        )
        return response
