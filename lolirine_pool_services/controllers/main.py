# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class PoolServicesController(http.Controller):
    
    @http.route('/pool/devis', type='http', auth='public', website=True)
    def pool_devis_page(self, **kw):
        """Page de demande de devis"""
        return request.render('lolirine_pool_services.page_pool_devis', {
            'preselected_service': kw.get('service', ''),
        })
    
    # =============================================
    # PAGE CONTACTEZ-NOUS
    # =============================================
    
    @http.route('/pool/contact', type='http', auth='public', website=True)
    def pool_contact_page(self, **kw):
        """Page Contactez-nous Pool Store"""
        return request.render('lolirine_pool_services.page_pool_contact', {})
    
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
            
            # Déterminer le type de service CRM basé sur le type de demande
            service_type_mapping = {
                'product': 'autre',
                'service': 'entretien',
                'quote': 'autre',
                'general': 'autre',
            }
            
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
                'is_pool_request': True,
                'pool_service_type': service_type_mapping.get(request_type, 'autre'),
                'pool_type': pool_type or False,
                'pool_dimensions': pool_dimensions or False,
                'pool_treatment': pool_treatment or False,
                'pool_problem': message or False,
                'pool_urgency': 'medium',
            }
            
            # Ajouter infos entreprise si professionnel
            if client_type == 'professional' and company_name:
                lead_vals['partner_name'] = company_name
                if vat_number:
                    lead_vals['description'] = description
            
            if team:
                lead_vals['team_id'] = team.id
            
            lead = request.env['crm.lead'].sudo().create(lead_vals)
            _logger.info(f"Pool Store Contact: Opportunité créée - {lead.name} (ID: {lead.id})")
            
            return request.render('lolirine_pool_services.page_pool_contact_success', {
                'name': name,
            })
            
        except Exception as e:
            _logger.error(f"Pool Store Contact: Erreur - {str(e)}")
            return request.render('lolirine_pool_services.page_pool_contact_error', {
                'error': str(e),
            })
    
    @http.route('/pool/devis/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def pool_devis_submit(self, **post):
        """Soumission du formulaire - Crée une opportunité CRM"""
        try:
            # Récupérer les données
            name = post.get('name', '').strip()
            email = post.get('email', '').strip()
            phone = post.get('phone', '').strip()
            service_type = post.get('service_type', '')
            pool_type = post.get('pool_type', '')
            dimensions = post.get('dimensions', '').strip()
            treatment = post.get('treatment', '')
            problem = post.get('problem', '').strip()
            urgency = post.get('urgency', 'medium')
            address = post.get('address', '').strip()
            
            # Labels pour les services
            service_labels = {
                'entretien': 'Entretien',
                'construction': 'Construction/Rénovation',
                'analyse': 'Analyse eau',
                'hivernage': 'Hivernage',
                'estivage': 'Remise en service',
                'contrat_ponctuel': 'Visite ponctuelle',
                'contrat_saison': 'Contrat saison',
                'contrat_annuel': 'Contrat annuel',
                'autre': 'Autre demande',
            }
            service_label = service_labels.get(service_type, 'Demande')
            
            # Nom de l'opportunité
            lead_name = f"[Pool Store] {service_label} - {name}"
            
            # Description formatée
            description = f"""
═══════════════════════════════════════════
  DEMANDE DE DEVIS - POOL STORE
═══════════════════════════════════════════

📋 SERVICE DEMANDÉ : {service_label}
⏰ URGENCE : {urgency}

👤 CLIENT
   Nom : {name}
   Email : {email}
   Téléphone : {phone}
   Adresse piscine : {address or 'Non renseignée'}

🏊 PISCINE
   Type : {dict([('enterree', 'Enterrée'), ('hors_sol', 'Hors-sol'), ('semi_enterree', 'Semi-enterrée'), ('interieure', 'Intérieure'), ('naturelle', 'Naturelle'), ('autre', 'Autre')]).get(pool_type, 'Non renseigné')}
   Dimensions : {dimensions or 'Non renseignées'}
   Traitement : {dict([('chlore', 'Chlore'), ('sel', 'Électrolyse sel'), ('brome', 'Brome'), ('oxygene', 'Oxygène actif'), ('uv', 'UV'), ('autre', 'Autre'), ('inconnu', 'Inconnu')]).get(treatment, 'Non renseigné')}

📝 DESCRIPTION DU BESOIN :
{problem or 'Non renseignée'}

═══════════════════════════════════════════
            """.strip()
            
            # Chercher une équipe commerciale
            team = request.env['crm.team'].sudo().search([], limit=1)
            
            # Créer l'opportunité
            lead_vals = {
                'name': lead_name,
                'contact_name': name,
                'email_from': email,
                'phone': phone,
                'description': description,
                'type': 'opportunity',
                'is_pool_request': True,
                'pool_service_type': service_type or False,
                'pool_type': pool_type or False,
                'pool_dimensions': dimensions or False,
                'pool_treatment': treatment or False,
                'pool_problem': problem or False,
                'pool_urgency': urgency,
                'pool_address': address or False,
            }
            
            if team:
                lead_vals['team_id'] = team.id
            
            lead = request.env['crm.lead'].sudo().create(lead_vals)
            _logger.info(f"Pool Store: Opportunité créée - {lead.name} (ID: {lead.id})")
            
            return request.render('lolirine_pool_services.page_pool_devis_success', {
                'name': name,
            })
            
        except Exception as e:
            _logger.error(f"Pool Store: Erreur création opportunité - {str(e)}")
            return request.render('lolirine_pool_services.page_pool_devis_error', {
                'error': str(e),
            })
