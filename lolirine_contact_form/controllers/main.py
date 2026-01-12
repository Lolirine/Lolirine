# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class LolirineContactForm(http.Controller):

    @http.route(['/contactus', '/contact'], type='http', auth='public', website=True)
    def redirect_old_contact(self, **kwargs):
        """Rediriger les anciennes URLs vers le nouveau formulaire"""
        return request.redirect('/contact-garde-meubles', code=301)

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
            # Déterminer le nom à utiliser
            is_company = post.get('is_company') == 'on'
            if is_company:
                name = post.get('legal_name', '') or post.get('company_name', '')
                contact_name = post.get('contact_person', '') or post.get('name', '')
            else:
                name = post.get('name', '')
                contact_name = name
            
            # Récupérer les données du formulaire
            lead_vals = {
                'name': f"Demande web - {name or 'Sans nom'}",
                'contact_name': contact_name,
                'partner_name': name if is_company else '',
                'email_from': post.get('email', ''),
                'phone': post.get('phone', ''),
                'mobile': post.get('mobile', ''),
                'description': post.get('message', ''),
                
                # Informations entreprise
                'is_company_contact': is_company,
                'company_name_contact': post.get('company_name', ''),
                'legal_name': post.get('legal_name', ''),
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

    @http.route('/api/config/google-api-key', type='json', auth='public', cors='*')
    def get_google_api_key(self, **kwargs):
        """Récupérer la clé API Google depuis les paramètres système"""
        try:
            api_key = request.env['ir.config_parameter'].sudo().get_param(
                'lolirine_contact_form.google_places_api_key', 
                default=''
            )
            return {'api_key': api_key}
        except Exception as e:
            _logger.error(f"Erreur lors de la récupération de la clé API Google: {str(e)}")
            return {'api_key': '', 'error': str(e)}

    @http.route('/api/address/validate-vat', type='json', auth='public', cors='*')
    def validate_vat(self, vat='', **kwargs):
        """Valider un numéro de TVA belge et récupérer les infos entreprise"""
        # Nettoyer le numéro de TVA
        vat = vat.upper().replace(' ', '').replace('.', '').replace('-', '')
        if not vat.startswith('BE'):
            vat = 'BE' + vat
        
        try:
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
