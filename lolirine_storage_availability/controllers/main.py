# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleStorageBox(WebsiteSale):
    
    @http.route()
    def product(self, product, category='', search='', **kwargs):
        """Override de la page produit pour ajouter les données de box de stockage"""
        response = super().product(product, category=category, search=search, **kwargs)
        
        # Si le produit est un box de stockage, on injecte les données
        if hasattr(response, 'qcontext') and product.is_storage_box:
            config = request.env['ir.config_parameter'].sudo()
            show_badge = config.get_param('lolirine_storage.show_status_badge', 'False') == 'True'
            
            storage_data = {
                'is_storage_box': True,
                'storage_status': product.storage_status,
                'storage_status_display': product.storage_status_display,
                'show_badge': show_badge,
                'show_appointment_button': product.show_appointment_button,
                'show_general_inquiry_button': product.show_general_inquiry_button,
                'appointment_url': product.appointment_url,
                'general_inquiry_url': product.general_inquiry_url,
                'appointment_button_label': product.appointment_button_label,
                'general_inquiry_button_label': product.general_inquiry_button_label,
            }
            
            response.qcontext['storage_box_data'] = json.dumps(storage_data)
        
        return response
