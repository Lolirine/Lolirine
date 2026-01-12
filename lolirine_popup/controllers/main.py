# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json


class LolirinePopupController(http.Controller):

    @http.route('/lolirine-popup/track-view/<int:popup_id>', type='http', auth='public', 
                methods=['POST'], csrf=False)
    def track_view(self, popup_id, **kwargs):
        """Enregistre une vue du popup"""
        try:
            popup = request.env['lolirine.popup.config'].sudo().browse(popup_id)
            if popup.exists():
                popup.increment_view()
            return json.dumps({'success': True})
        except Exception:
            return json.dumps({'success': False})

    @http.route('/lolirine-popup/track-click/<int:popup_id>', type='http', auth='public', 
                methods=['POST'], csrf=False)
    def track_click(self, popup_id, **kwargs):
        """Enregistre un clic sur le bouton du popup"""
        try:
            popup = request.env['lolirine.popup.config'].sudo().browse(popup_id)
            if popup.exists():
                popup.increment_click()
            return json.dumps({'success': True})
        except Exception:
            return json.dumps({'success': False})
