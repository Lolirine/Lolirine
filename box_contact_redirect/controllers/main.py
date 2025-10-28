# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class BoxContactController(http.Controller):
    
    @http.route(['/contactus'], type='http', auth="public", website=True, sitemap=False)
    def contact_form_box(self, box_name=None, box_id=None, **kwargs):
        """
        Gère l'affichage du formulaire de contact avec les informations du box
        """
        values = {}
        
        if box_name:
            values['box_name'] = box_name
        if box_id:
            values['box_id'] = box_id
            # Récupérer plus d'informations sur le produit si nécessaire
            product = request.env['product.template'].sudo().browse(int(box_id))
            if product.exists():
                values['product'] = product
                # Pré-remplir le message avec les infos du box
                default_message = f"Bonjour,\n\nJe suis intéressé(e) par le box : {box_name}\n\nMerci de me recontacter.\n"
                values['default_description'] = default_message
        
        # Utiliser le template de contact standard d'Odoo
        return request.render("website.contactus", values)
