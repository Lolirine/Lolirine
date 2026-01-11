# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class LolirineContactForm(http.Controller):

    @http.route('/contact-garde-meubles', type='http', auth='public', website=True)
    def contact_form_page(self, **kwargs):
        """Page du formulaire de contact optimisé"""
        countries = request.env['res.country'].sudo().search([])
        belgium = request.env.ref('base.be', raise_if_not_found=False)
        
        return request.render('lolirine_contact_form.contact_form_page', {
            'countries': countries,
            'default_country': belgium,
        })

    @http.route('/contact-garde-meubles/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def contact_form_submit(self, **post):
        """Traitement du formulaire de contact"""
        try:
            # Récupérer les données du formulaire
            lead_vals = {
                'name': f"Demande web - {post.get('name', 'Sans nom')}",
                'contact_name': post.get('name', ''),
                'email_from': post.get('email', ''),
                'phone': post.get('phone', ''),
                'mobile': post.get('mobile', ''),
                'description': post.get('message', ''),
                
                # Informations entreprise
                'is_company_contact': post.get('is_company') == 'on',
                'company_name_contact': post.get('company_name', ''),
                'vat_number': post.get('vat', ''),
                
                # Adresse
                'contact_street': post.get('street', ''),
                'contact_street_number': post.get('street_number', ''),
                'contact_street2': post.get('street2', ''),
                'contact_zip': post.get('zip', ''),
                'contact_city': post.get('city', ''),
                
                # Informations garde-meubles
                'storage_type': post.get('storage_type', 'unknown'),
                'storage_duration': post.get('storage_duration', 'unknown'),
                'storage_content': post.get('storage_content', ''),
                'desired_start_date': post.get('start_date') or False,
                'how_did_you_hear': post.get('source', ''),
                'special_requests': post.get('special_requests', ''),
                
                # Type de lead
                'type': 'lead',
            }
            
            # Pays
            country_id = post.get('country_id')
            if country_id:
                lead_vals['contact_country_id'] = int(country_id)
            else:
                belgium = request.env.ref('base.be', raise_if_not_found=False)
                if belgium:
                    lead_vals['contact_country_id'] = belgium.id
            
            # Trouver l'équipe commerciale par défaut
            sales_team = request.env['crm.team'].sudo().search([
                ('use_opportunities', '=', True)
            ], limit=1)
            if sales_team:
                lead_vals['team_id'] = sales_team.id
            
            # Créer le lead
            lead = request.env['crm.lead'].sudo().create(lead_vals)
            
            _logger.info(f"Lead créé: {lead.id} - {lead.name}")
            
            # Rediriger vers la page de confirmation
            return request.redirect('/contact-garde-meubles/merci')
            
        except Exception as e:
            _logger.error(f"Erreur lors de la création du lead: {str(e)}")
            return request.render('lolirine_contact_form.contact_form_error', {
                'error': str(e)
            })

    @http.route('/contact-garde-meubles/merci', type='http', auth='public', website=True)
    def contact_form_thanks(self, **kwargs):
        """Page de remerciement après soumission"""
        return request.render('lolirine_contact_form.contact_form_thanks')

    @http.route('/api/address/autocomplete', type='json', auth='public', cors='*')
    def address_autocomplete(self, query='', country='BE', **kwargs):
        """API d'autocomplétion d'adresse via Nominatim (OpenStreetMap)"""
        import requests
        
        if len(query) < 3:
            return {'results': []}
        
        try:
            # Utiliser l'API Nominatim (gratuite)
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': query,
                'countrycodes': country.lower(),
                'format': 'json',
                'addressdetails': 1,
                'limit': 5,
            }
            headers = {
                'User-Agent': 'Lolirine-Odoo/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            data = response.json()
            
            results = []
            for item in data:
                address = item.get('address', {})
                results.append({
                    'display_name': item.get('display_name', ''),
                    'street': address.get('road', ''),
                    'house_number': address.get('house_number', ''),
                    'postcode': address.get('postcode', ''),
                    'city': address.get('city') or address.get('town') or address.get('village') or address.get('municipality', ''),
                    'country': address.get('country', ''),
                })
            
            return {'results': results}
            
        except Exception as e:
            _logger.error(f"Erreur autocomplétion adresse: {str(e)}")
            return {'results': [], 'error': str(e)}

    @http.route('/api/address/validate-vat', type='json', auth='public', cors='*')
    def validate_vat(self, vat='', **kwargs):
        """Valider un numéro de TVA belge et récupérer les infos entreprise"""
        import requests
        
        # Nettoyer le numéro de TVA
        vat = vat.upper().replace(' ', '').replace('.', '').replace('-', '')
        if not vat.startswith('BE'):
            vat = 'BE' + vat
        
        try:
            # Utiliser l'API VIES de l'UE
            # Note: En production, utiliser une vraie API de validation TVA
            # Pour l'instant, on fait une validation basique
            
            if len(vat) == 12 and vat.startswith('BE'):
                return {
                    'valid': True,
                    'vat': vat,
                    'message': 'Format valide'
                }
            else:
                return {
                    'valid': False,
                    'vat': vat,
                    'message': 'Format invalide. Le numéro TVA belge doit contenir 10 chiffres après BE.'
                }
                
        except Exception as e:
            return {'valid': False, 'error': str(e)}
