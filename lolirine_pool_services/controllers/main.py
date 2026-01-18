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
