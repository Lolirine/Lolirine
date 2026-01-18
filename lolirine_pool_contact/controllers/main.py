# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class PoolContactController(http.Controller):
    """
    Controller pour la page Contactez-nous du Pool Store
    """
    
    @http.route('/pool/contact', type='http', auth='public', website=True)
    def pool_contact_page(self, **kw):
        """Page Contactez-nous Pool Store"""
        return request.render('lolirine_pool_contact.page_pool_contact', {})
    
    @http.route('/pool/contact/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def pool_contact_submit(self, **post):
        """Soumission du formulaire contact - Crée une opportunité CRM"""
        try:
            # Récupérer les données
            request_type = post.get('request_type', 'general')
            client_type = post.get('client_type', 'particular')
            company_name = post.get('company_name', '').strip()
            vat_number = post.get('vat_number', '').strip()
            name = post.get('name', '').strip()
            email = post.get('email', '').strip()
            phone = post.get('phone', '').strip()
            zip_code = post.get('zip_code', '').strip()
            pool_type = post.get('pool_type', '')
            pool_treatment = post.get('pool_treatment', '')
            pool_dimensions = post.get('pool_dimensions', '').strip()
            subject = post.get('subject', '').strip()
            message = post.get('message', '').strip()
            pref_email = post.get('pref_email', '')
            pref_phone = post.get('pref_phone', '')
            pref_whatsapp = post.get('pref_whatsapp', '')
            
            # Labels
            request_labels = {
                'product': 'Question produit',
                'service': 'Demande service',
                'quote': 'Demande devis',
                'general': 'Question générale',
            }
            request_label = request_labels.get(request_type, 'Contact')
            
            client_label = 'Professionnel' if client_type == 'professional' else 'Particulier'
            
            pool_type_labels = {
                'enterree': 'Enterrée',
                'hors_sol': 'Hors-sol',
                'semi_enterree': 'Semi-enterrée',
                'interieure': 'Intérieure',
                'spa': 'Spa / Jacuzzi',
                'autre': 'Autre',
            }
            
            treatment_labels = {
                'chlore': 'Chlore',
                'sel': 'Électrolyse sel',
                'brome': 'Brome',
                'oxygene': 'Oxygène actif',
                'uv': 'UV',
                'inconnu': 'Inconnu',
            }
            
            # Préférences contact
            prefs = []
            if pref_email:
                prefs.append('Email')
            if pref_phone:
                prefs.append('Téléphone')
            if pref_whatsapp:
                prefs.append('WhatsApp')
            pref_str = ', '.join(prefs) if prefs else 'Email'
            
            # Nom de l'opportunité
            lead_name = f"[Pool Store] {request_label} - {name}"
            if company_name:
                lead_name = f"[Pool Store] {request_label} - {company_name}"
            
            # Description formatée
            description = f"""
═══════════════════════════════════════════
  CONTACT - POOL STORE
═══════════════════════════════════════════

📋 TYPE DE DEMANDE : {request_label}
📌 SUJET : {subject}

👤 CLIENT ({client_label})
   Nom : {name}
   Email : {email}
   Téléphone : {phone}
   Code postal : {zip_code or 'Non renseigné'}"""
            
            if client_type == 'professional':
                description += f"""
   
🏢 ENTREPRISE
   Société : {company_name}
   N° TVA : {vat_number or 'Non renseigné'}"""
            
            if pool_type or pool_treatment or pool_dimensions:
                description += f"""

🏊 PISCINE
   Type : {pool_type_labels.get(pool_type, 'Non renseigné')}
   Traitement : {treatment_labels.get(pool_treatment, 'Non renseigné')}
   Dimensions : {pool_dimensions or 'Non renseignées'}"""
            
            description += f"""

📞 PRÉFÉRENCE DE CONTACT : {pref_str}

💬 MESSAGE :
{message}

═══════════════════════════════════════════
            """.strip()
            
            # Chercher équipe commerciale
            team = request.env['crm.team'].sudo().search([], limit=1)
            
            # Créer l'opportunité
            lead_vals = {
                'name': lead_name,
                'contact_name': name,
                'email_from': email,
                'phone': phone,
                'description': description,
                'type': 'opportunity',
            }
            
            # Ajouter infos entreprise si professionnel
            if client_type == 'professional' and company_name:
                lead_vals['partner_name'] = company_name
            
            if team:
                lead_vals['team_id'] = team.id
            
            lead = request.env['crm.lead'].sudo().create(lead_vals)
            _logger.info(f"Pool Store Contact: Opportunité créée - {lead.name} (ID: {lead.id})")
            
            return request.render('lolirine_pool_contact.page_pool_contact_success', {
                'name': name,
            })
            
        except Exception as e:
            _logger.error(f"Pool Store Contact: Erreur - {str(e)}")
            return request.render('lolirine_pool_contact.page_pool_contact_error', {
                'error': str(e),
            })
