# -*- coding: utf-8 -*-

import logging
import requests
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ACT365API(models.AbstractModel):
    """Service API pour communiquer avec ACT365"""
    _name = 'act365.api'
    _description = 'ACT365 API Service'

    @api.model
    def _get_api_config(self):
        """Récupère la configuration API depuis les paramètres"""
        ICP = self.env['ir.config_parameter'].sudo()
        api_url = ICP.get_param('act365.api_url', default='https://api.act365.eu')
        api_key = ICP.get_param('act365.api_key', default='')
        
        if not api_key:
            raise UserError(_(
                "Clé API ACT365 non configurée.\n"
                "Veuillez la configurer dans Paramètres > Intégrations > ACT365"
            ))
        
        return {
            'api_url': api_url.rstrip('/'),
            'api_key': api_key,
        }

    @api.model
    def _get_headers(self):
        """Génère les headers pour les requêtes API"""
        config = self._get_api_config()
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f"Bearer {config['api_key']}",
            'X-API-Key': config['api_key'],
        }

    @api.model
    def _make_request(self, method, endpoint, data=None, params=None):
        """Effectue une requête vers l'API ACT365"""
        config = self._get_api_config()
        url = f"{config['api_url']}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        _logger.info(f"ACT365 API Request: {method} {url}")
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, headers=headers, json=data, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise UserError(_("Méthode HTTP non supportée: %s") % method)
            
            _logger.info(f"ACT365 API Response: {response.status_code}")
            
            # Vérifier le code de statut
            if response.status_code >= 400:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_data.get('error', response.text))
                except:
                    pass
                raise UserError(_(
                    "Erreur API ACT365 (Code %s):\n%s"
                ) % (response.status_code, error_msg))
            
            # Retourner les données JSON si disponibles
            if response.text:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {'raw': response.text}
            return {}
            
        except requests.exceptions.Timeout:
            raise UserError(_("Timeout lors de la connexion à ACT365"))
        except requests.exceptions.ConnectionError as e:
            raise UserError(_("Impossible de se connecter à ACT365:\n%s") % str(e))
        except requests.exceptions.RequestException as e:
            raise UserError(_("Erreur de requête ACT365:\n%s") % str(e))

    # =============================================
    # MÉTHODES CARDHOLDERS
    # =============================================
    
    @api.model
    def get_cardholders(self, search_term=None):
        """Récupère la liste des cardholders"""
        params = {}
        if search_term:
            params['search'] = search_term
        return self._make_request('GET', '/api/v1/cardholders', params=params)

    @api.model
    def get_cardholder(self, cardholder_id):
        """Récupère un cardholder spécifique"""
        return self._make_request('GET', f'/api/v1/cardholders/{cardholder_id}')

    @api.model
    def create_cardholder(self, data):
        """
        Crée un nouveau cardholder dans ACT365
        
        Args:
            data (dict): Données du cardholder
                - firstName: Prénom
                - lastName: Nom
                - email: Email (optionnel)
                - phone: Téléphone (optionnel)
                - pin: Code PIN (si non fourni, généré automatiquement)
                - cardholderGroups: Liste des IDs de groupes
                - validFrom: Date de début de validité (ISO format)
                - validTo: Date de fin de validité (ISO format)
                - enabled: True/False
        
        Returns:
            dict: Données du cardholder créé incluant l'ID et le PIN
        """
        return self._make_request('POST', '/api/v1/cardholders', data=data)

    @api.model
    def update_cardholder(self, cardholder_id, data):
        """Met à jour un cardholder existant"""
        return self._make_request('PUT', f'/api/v1/cardholders/{cardholder_id}', data=data)

    @api.model
    def delete_cardholder(self, cardholder_id):
        """Supprime un cardholder"""
        return self._make_request('DELETE', f'/api/v1/cardholders/{cardholder_id}')

    @api.model
    def enable_cardholder(self, cardholder_id):
        """Active un cardholder"""
        return self._make_request('PATCH', f'/api/v1/cardholders/{cardholder_id}/enable')

    @api.model
    def disable_cardholder(self, cardholder_id):
        """Désactive un cardholder"""
        return self._make_request('PATCH', f'/api/v1/cardholders/{cardholder_id}/disable')

    # =============================================
    # MÉTHODES CREDENTIALS / PIN
    # =============================================
    
    @api.model
    def get_cardholder_credentials(self, cardholder_id):
        """Récupère les credentials d'un cardholder (cartes, PIN, etc.)"""
        return self._make_request('GET', f'/api/v1/cardholders/{cardholder_id}/credentials')

    @api.model
    def add_pin_credential(self, cardholder_id, pin_code=None):
        """
        Ajoute un credential PIN à un cardholder
        
        Args:
            cardholder_id: ID du cardholder
            pin_code: Code PIN (si None, sera généré automatiquement)
        
        Returns:
            dict: Données du credential créé
        """
        data = {
            'type': 'PIN',
        }
        if pin_code:
            data['pin'] = pin_code
        return self._make_request('POST', f'/api/v1/cardholders/{cardholder_id}/credentials', data=data)

    @api.model
    def update_pin_credential(self, cardholder_id, credential_id, new_pin):
        """Met à jour le PIN d'un credential"""
        data = {
            'pin': new_pin
        }
        return self._make_request('PUT', f'/api/v1/cardholders/{cardholder_id}/credentials/{credential_id}', data=data)

    @api.model
    def generate_pin(self, length=4):
        """Génère un code PIN aléatoire"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])

    # =============================================
    # MÉTHODES CARDHOLDER GROUPS
    # =============================================
    
    @api.model
    def get_cardholder_groups(self):
        """Récupère la liste des groupes de cardholders"""
        return self._make_request('GET', '/api/v1/cardholdergroups')

    @api.model
    def get_cardholder_group(self, group_id):
        """Récupère un groupe spécifique"""
        return self._make_request('GET', f'/api/v1/cardholdergroups/{group_id}')

    @api.model
    def add_cardholder_to_group(self, cardholder_id, group_id):
        """Ajoute un cardholder à un groupe"""
        return self._make_request('POST', f'/api/v1/cardholdergroups/{group_id}/cardholders/{cardholder_id}')

    @api.model
    def remove_cardholder_from_group(self, cardholder_id, group_id):
        """Retire un cardholder d'un groupe"""
        return self._make_request('DELETE', f'/api/v1/cardholdergroups/{group_id}/cardholders/{cardholder_id}')

    # =============================================
    # MÉTHODES UTILITAIRES
    # =============================================
    
    @api.model
    def test_connection(self):
        """Teste la connexion à l'API ACT365"""
        try:
            result = self._make_request('GET', '/api/v1/status')
            return {
                'success': True,
                'message': _("Connexion à ACT365 réussie!"),
                'data': result
            }
        except UserError as e:
            return {
                'success': False,
                'message': str(e),
                'data': {}
            }

    @api.model
    def sync_cardholder_groups(self):
        """Synchronise les groupes de cardholders depuis ACT365"""
        try:
            groups_data = self.get_cardholder_groups()
            ACT365Group = self.env['act365.cardholder.group']
            
            synced_count = 0
            for group in groups_data.get('data', groups_data if isinstance(groups_data, list) else []):
                group_id = group.get('id')
                group_name = group.get('name', f'Groupe {group_id}')
                
                existing = ACT365Group.search([('act365_id', '=', str(group_id))], limit=1)
                if existing:
                    existing.write({'name': group_name})
                else:
                    ACT365Group.create({
                        'act365_id': str(group_id),
                        'name': group_name,
                    })
                synced_count += 1
            
            return {
                'success': True,
                'message': _("%d groupe(s) synchronisé(s)") % synced_count
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
