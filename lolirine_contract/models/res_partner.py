import base64
import json
import requests
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Champs carte d'identité - images
    id_card_recto = fields.Binary(
        string="Carte d'identite (Recto)",
        attachment=True,
        help="Photo recto de la carte d'identite du client"
    )
    id_card_recto_filename = fields.Char(string="Nom fichier recto")
    
    id_card_verso = fields.Binary(
        string="Carte d'identite (Verso)",
        attachment=True,
        help="Photo verso de la carte d'identite du client"
    )
    id_card_verso_filename = fields.Char(string="Nom fichier verso")
    
    id_card_uploaded = fields.Boolean(
        string="Carte d'identite fournie",
        compute="_compute_id_card_uploaded",
        store=True
    )
    
    # Nouveaux champs pour les informations extraites de la CI
    id_card_birthdate = fields.Date(string="Date de naissance")
    id_card_birthplace = fields.Char(string="Lieu de naissance")
    id_card_gender = fields.Selection([
        ('M', 'Masculin'),
        ('F', 'Feminin')
    ], string="Sexe")
    id_card_nationality = fields.Char(string="Nationalite")
    id_card_expiry_date = fields.Date(string="Date de validite CI")

    @api.depends("id_card_recto", "id_card_verso")
    def _compute_id_card_uploaded(self):
        for partner in self:
            partner.id_card_uploaded = bool(partner.id_card_recto and partner.id_card_verso)

    def action_view_id_card_recto(self):
        """Ouvrir le recto de la carte d'identité en grand"""
        self.ensure_one()
        if not self.id_card_recto:
            raise UserError("Aucune image recto disponible")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/image/res.partner/%s/id_card_recto' % self.id,
            'target': 'new',
        }

    def action_view_id_card_verso(self):
        """Ouvrir le verso de la carte d'identité en grand"""
        self.ensure_one()
        if not self.id_card_verso:
            raise UserError("Aucune image verso disponible")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/image/res.partner/%s/id_card_verso' % self.id,
            'target': 'new',
        }

    def action_extract_id_card_info(self):
        """Extraire les informations de la carte d'identité via OCR (Claude API)"""
        self.ensure_one()
        
        if not self.id_card_recto:
            raise UserError("Veuillez d'abord telecharger le recto de la carte d'identite")
        
        # Récupérer la clé API depuis les paramètres système
        api_key = self.env['ir.config_parameter'].sudo().get_param('lolirine_contract.anthropic_api_key')
        
        if not api_key:
            raise UserError(
                "Cle API Anthropic non configuree.\n\n"
                "Allez dans Configuration > Parametres > Parametres systeme\n"
                "et ajoutez la cle 'lolirine_contract.anthropic_api_key' avec votre cle API."
            )
        
        # Préparer les images en base64
        image_recto = self.id_card_recto.decode('utf-8') if isinstance(self.id_card_recto, bytes) else self.id_card_recto
        
        # Déterminer le type MIME pour le recto
        media_type_recto = "image/jpeg"
        if self.id_card_recto_filename:
            if self.id_card_recto_filename.lower().endswith('.png'):
                media_type_recto = "image/png"
            elif self.id_card_recto_filename.lower().endswith('.gif'):
                media_type_recto = "image/gif"
            elif self.id_card_recto_filename.lower().endswith('.webp'):
                media_type_recto = "image/webp"
        
        # Construire le contenu du message avec les images
        content = []
        
        # Ajouter le recto
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type_recto,
                "data": image_recto
            }
        })
        content.append({
            "type": "text",
            "text": "Ceci est le RECTO de la carte d'identite belge."
        })
        
        # Ajouter le verso s'il existe
        if self.id_card_verso:
            image_verso = self.id_card_verso.decode('utf-8') if isinstance(self.id_card_verso, bytes) else self.id_card_verso
            
            media_type_verso = "image/jpeg"
            if self.id_card_verso_filename:
                if self.id_card_verso_filename.lower().endswith('.png'):
                    media_type_verso = "image/png"
                elif self.id_card_verso_filename.lower().endswith('.gif'):
                    media_type_verso = "image/gif"
                elif self.id_card_verso_filename.lower().endswith('.webp'):
                    media_type_verso = "image/webp"
            
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type_verso,
                    "data": image_verso
                }
            })
            content.append({
                "type": "text",
                "text": "Ceci est le VERSO de la carte d'identite belge."
            })
        
        # Appel à l'API Claude
        headers = {
            "x-api-key": api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        prompt = """Analyse ces images d'une carte d'identite belge (recto et verso si disponible).

IMPORTANT - Localisation des informations sur une carte d'identite belge:
- RECTO: Nom, Prenom, Lieu/Date naissance, Sexe, Nationalite, Numero de CARTE (format XXX-XXXXXXX-XX), Dates de validite
- VERSO: Numero NATIONAL / Registre national (format XX.XX.XX-XXX.XX comme 83.07.13-125.16), Lieu de delivrance

Extrais les informations et reponds UNIQUEMENT avec un JSON valide, sans texte avant ou apres:
{
    "nom": "NOM DE FAMILLE en majuscules",
    "prenom": "PRENOM",
    "date_naissance": "JJ.MM.AAAA",
    "lieu_naissance": "VILLE",
    "sexe": "M ou F",
    "nationalite": "BELGE ou autre",
    "numero_national": "XX.XX.XX-XXX.XX (depuis le VERSO, champ Registre national)",
    "numero_carte": "XXX-XXXXXXX-XX (depuis le RECTO, champ N° carte)",
    "date_validite": "JJ.MM.AAAA (date de fin de validite)",
    "adresse_rue": "RUE ET NUMERO si visible",
    "adresse_cp": "CODE POSTAL si visible",
    "adresse_ville": "VILLE si visible"
}

ATTENTION: Ne confonds PAS le numero de carte (RECTO) avec le numero national (VERSO). Ce sont deux numeros differents!
Si une information n'est pas visible ou lisible, mets null pour cette valeur."""

        content.append({
            "type": "text",
            "text": prompt
        })
        
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ]
        }
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            # Extraire le texte de la réponse
            content = result.get('content', [])
            if content and len(content) > 0:
                text_response = content[0].get('text', '{}')
                
                # Parser le JSON
                try:
                    data = json.loads(text_response)
                except json.JSONDecodeError:
                    # Essayer d'extraire le JSON du texte
                    import re
                    json_match = re.search(r'\{[^{}]*\}', text_response, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                    else:
                        raise UserError("Impossible de parser la reponse de l'API:\n%s" % text_response)
                
                # Mettre à jour les champs du contact
                update_vals = {}
                
                # Log pour debug
                import logging
                _logger = logging.getLogger(__name__)
                _logger.info("=== EXTRACTION CI - Données reçues: %s", data)
                
                # Nom et prénom - seulement pour les particuliers
                if data.get('nom') and data.get('prenom'):
                    if self.company_type == 'person':
                        update_vals['name'] = "%s %s" % (data['prenom'], data['nom'])
                
                # Numéro national - champ Studio existant
                if data.get('numero_national'):
                    update_vals['x_studio_numro_national_1'] = str(data['numero_national'])
                
                # Numéro de carte d'identité - champ Studio existant
                if data.get('numero_carte'):
                    update_vals['x_studio_char_field_9h1_1j04as55r'] = str(data['numero_carte'])
                
                # Date de naissance
                if data.get('date_naissance'):
                    try:
                        date_str = str(data['date_naissance'])
                        parts = date_str.replace('/', '.').replace('-', '.').split('.')
                        if len(parts) == 3:
                            day, month, year = parts[0], parts[1], parts[2]
                            if len(year) == 2:
                                year = '19' + year if int(year) > 30 else '20' + year
                            update_vals['id_card_birthdate'] = "%s-%s-%s" % (year, month.zfill(2), day.zfill(2))
                    except Exception as e:
                        _logger.error("Erreur parsing date naissance: %s", e)
                
                # Lieu de naissance
                if data.get('lieu_naissance'):
                    update_vals['id_card_birthplace'] = str(data['lieu_naissance'])
                
                # Sexe
                if data.get('sexe'):
                    sexe = str(data['sexe']).upper().strip()
                    if sexe in ['M', 'H', 'HOMME', 'MASCULIN']:
                        update_vals['id_card_gender'] = 'M'
                    elif sexe in ['F', 'V', 'FEMME', 'FEMININ']:
                        update_vals['id_card_gender'] = 'F'
                
                # Nationalité
                if data.get('nationalite'):
                    update_vals['id_card_nationality'] = str(data['nationalite'])
                
                # Date de validité
                if data.get('date_validite'):
                    try:
                        date_str = str(data['date_validite'])
                        parts = date_str.replace('/', '.').replace('-', '.').split('.')
                        if len(parts) == 3:
                            day, month, year = parts[0], parts[1], parts[2]
                            if len(year) == 2:
                                year = '20' + year
                            update_vals['id_card_expiry_date'] = "%s-%s-%s" % (year, month.zfill(2), day.zfill(2))
                    except Exception as e:
                        _logger.error("Erreur parsing date validite: %s", e)
                
                # Adresse
                if data.get('adresse_rue'):
                    update_vals['street'] = str(data['adresse_rue'])
                if data.get('adresse_cp'):
                    update_vals['zip'] = str(data['adresse_cp'])
                if data.get('adresse_ville'):
                    update_vals['city'] = str(data['adresse_ville'])
                
                _logger.info("=== EXTRACTION CI - Valeurs à écrire: %s", update_vals)
                
                # Écrire les valeurs
                if update_vals:
                    try:
                        self.sudo().write(update_vals)
                        _logger.info("=== EXTRACTION CI - Écriture réussie!")
                    except Exception as e:
                        _logger.error("=== EXTRACTION CI - Erreur écriture: %s", e)
                        raise UserError("Erreur lors de l'ecriture des donnees: %s" % str(e))
                
                # Retourner un message avec les informations extraites
                info_msg = "Informations extraites et enregistrees:\n\n"
                field_labels = {
                    'name': 'Nom complet',
                    'x_studio_numro_national_1': 'Numero National',
                    'x_studio_char_field_9h1_1j04as55r': 'Numero Carte ID',
                    'id_card_birthdate': 'Date de naissance',
                    'id_card_birthplace': 'Lieu de naissance',
                    'id_card_gender': 'Sexe',
                    'id_card_nationality': 'Nationalite',
                    'id_card_expiry_date': 'Date validite CI',
                    'street': 'Rue',
                    'zip': 'Code postal',
                    'city': 'Ville',
                }
                for field_name, value in update_vals.items():
                    label = field_labels.get(field_name, field_name)
                    info_msg += "- %s: %s\n" % (label, value)
                
                # Retourner une action qui recharge la vue du contact
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'res.partner',
                    'res_id': self.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                raise UserError("Reponse vide de l'API")
                
        except requests.exceptions.RequestException as e:
            raise UserError("Erreur lors de l'appel API: %s" % str(e))
