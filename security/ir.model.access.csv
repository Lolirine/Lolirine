# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class StorageApiController(http.Controller):

    def _get_user_from_request(self):
        """Helper pour authentifier l'utilisateur via la clé d'API dans le header."""
        api_key = request.httprequest.headers.get('Authorization')
        if api_key:
            # On attend un header de type "Bearer VOTRE_CLE"
            if api_key.startswith('Bearer '):
                api_key = api_key.split(' ')[1]
            user = request.env['res.users'].sudo()._get_user_from_api_key(api_key)
            if user:
                return user
        return None

    def _json_response(self, data=None, status=200):
        """Helper pour créer une réponse JSON standard."""
        return Response(
            json.dumps(data),
            status=status,
            mimetype='application/json'
        )

    @http.route('/api/storage/boxes', type='http', auth='public', methods=['GET'], csrf=False)
    def get_all_boxes(self, **kw):
        user = self._get_user_from_request()
        if not user:
            return self._json_response({'error': 'Unauthorized', 'message': 'Clé d\'API invalide ou manquante.'}, status=401)
        
        try:
            domain = []
            if kw.get('state'):
                domain.append(('state', '=', kw.get('state')))

            boxes = request.env['storage.box'].sudo().search(domain)
            box_data = []
            for box in boxes:
                box_data.append({
                    'id': box.id,
                    'name': box.name,
                    'state': box.state,
                    'color': box.color,
                    'product_id': box.product_id.id,
                    'product_name': box.product_id.display_name or None,
                    'product_barcode': box.product_id.barcode or None,
                    'product_qty': box.product_qty,
                })
            return self._json_response(box_data)
        except Exception as e:
            _logger.error(f"Erreur API (get_all_boxes): {e}")
            return self._json_response({'error': 'Internal Server Error', 'message': str(e)}, status=500)

    @http.route('/api/storage/box/<int:box_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_box_details(self, box_id, **kw):
        user = self._get_user_from_request()
        if not user:
            return self._json_response({'error': 'Unauthorized'}, status=401)

        box = request.env['storage.box'].sudo().browse(box_id)
        if not box.exists():
            return self._json_response({'error': 'Not Found', 'message': 'Boîte non trouvée.'}, status=404)
        
        return self._json_response({
            'id': box.id,
            'name': box.name,
            'state': box.state,
            'color': box.color,
            'product_id': box.product_id.id,
            'product_name': box.product_id.display_name or None,
            'product_barcode': box.product_id.barcode or None,
            'product_qty': box.product_qty,
        })

    @http.route('/api/storage/box/<int:box_id>', type='http', auth='public', methods=['PUT'], csrf=False)
    def update_box_state(self, box_id, **kw):
        user = self._get_user_from_request()
        if not user:
            return self._json_response({'error': 'Unauthorized'}, status=401)

        box = request.env['storage.box'].sudo().browse(box_id)
        if not box.exists():
            return self._json_response({'error': 'Not Found', 'message': 'Boîte non trouvée.'}, status=404)
        
        try:
            data = json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            return self._json_response({'error': 'Bad Request', 'message': 'Format JSON invalide.'}, status=400)

        values_to_update = {}
        if 'state' in data:
            # On vérifie que la valeur est valide pour le champ Selection
            valid_states = [key for key, val in box._fields['state'].selection]
            if data['state'] in valid_states:
                values_to_update['state'] = data['state']
            else:
                 return self._json_response({'error': 'Bad Request', 'message': f"État invalide. Valeurs possibles: {valid_states}"}, status=400)

        # Si l'état passe à 'disponible', on vide le produit
        if data.get('state') == 'available':
            values_to_update['product_id'] = False
            values_to_update['product_qty'] = 0
        else:
            if 'product_barcode' in data and data['product_barcode']:
                product = request.env['product.product'].sudo().search([('barcode', '=', data['product_barcode'])], limit=1)
                if not product:
                    return self._json_response({'error': 'Not Found', 'message': f"Produit avec le code-barres '{data['product_barcode']}' non trouvé."}, status=404)
                values_to_update['product_id'] = product.id
            elif 'product_id' in data:
                values_to_update['product_id'] = data.get('product_id')
            
            if 'product_qty' in data:
                values_to_update['product_qty'] = data.get('product_qty')

        if 'color' in data:
            values_to_update['color'] = data.get('color')

        if values_to_update:
            box.write(values_to_update)
            return self._json_response({'success': True, 'message': f'Boîte {box.name} mise à jour.'})
        else:
            return self._json_response({'message': 'Aucune donnée à mettre à jour.'})
