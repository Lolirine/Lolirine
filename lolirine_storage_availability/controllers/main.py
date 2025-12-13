# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request


class StorageBoxController(http.Controller):
    
    @http.route('/storage_box/get_data/<int:product_id>', type='json', auth='public', website=True)
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

    @http.route('/storage_box/get_data_by_slug/<string:slug>', type='http', auth='public', website=True)
    def get_storage_box_data_by_slug(self, slug, **kwargs):
        """Endpoint HTTP pour récupérer les données via le slug du produit"""
        # Extraire l'ID du slug (format: nom-produit-123)
        try:
            product_id = int(slug.split('-')[-1])
        except (ValueError, IndexError):
            return request.make_response(
                json.dumps({'is_storage_box': False}),
                headers=[('Content-Type', 'application/json')]
            )
        
        product = request.env['product.template'].sudo().browse(product_id)
        
        if not product.exists() or not product.is_storage_box:
            return request.make_response(
                json.dumps({'is_storage_box': False}),
                headers=[('Content-Type', 'application/json')]
            )
        
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
        
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')]
        )
