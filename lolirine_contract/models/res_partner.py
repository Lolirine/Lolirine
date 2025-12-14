import base64
import json
import requests
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

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
        
        # Préparer l'image en base64
        image_data = self.id_card_recto.decode('utf-8') if isinstance(self.id_card_recto, bytes) else self.id_card_recto
        
        # Déterminer le type MIME
        media_type = "image/jpeg"
        if self.id_card_recto_filename:
            if self.id_card_recto_filename.lower().endswith('.png'):
                media_type = "image/png"
            elif self.id_card_recto_filename.lower().endswith('.gif'):
                media_type = "image/gif"
            elif self.id_card_recto_filename.lower().endswith('.webp'):
                media_type = "image/webp"
        
        # Appel à l'API Claude
        headers = {
            "x-api-key": api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        prompt = """Analyse cette image d'une carte d'identité belge et extrais les informations suivantes.
Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après, avec cette structure exacte :
{
    "nom": "NOM DE FAMILLE",
    "prenom": "PRENOM",
    "date_naissance": "JJ.MM.AA",
    "lieu_naissance": "VILLE",
    "sexe": "M ou F",
    "nationalite": "BELGE ou autre",
    "numero_national": "XX.XX.XX-XXX.XX",
    "numero_carte": "XXX-XXXXXXX-XX",
    "date_validite": "JJ.MM.YYYY",
    "adresse_rue": "RUE ET NUMERO",
    "adresse_cp": "CODE POSTAL",
    "adresse_ville": "VILLE"
}
Si une information n'est pas visible ou lisible, mets null pour cette valeur."""

        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
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
                
                # Nom et prénom
                if data.get('nom') and data.get('prenom'):
                    if self.company_type == 'person':
                        update_vals['name'] = "%s %s" % (data['prenom'], data['nom'])
                
                # Numéro national - nom technique: x_studio_numro_national_1
                if data.get('numero_national'):
                    field = self._fields.get('x_studio_numro_national_1')
                    if field and field.type == 'char':
                        update_vals['x_studio_numro_national_1'] = data['numero_national']
                
                # Numéro de carte d'identité - nom technique: x_studio_char_field_9h1_1j04as55r
                if data.get('numero_carte'):
                    field = self._fields.get('x_studio_char_field_9h1_1j04as55r')
                    if field and field.type == 'char':
                        update_vals['x_studio_char_field_9h1_1j04as55r'] = data['numero_carte']
                
                # Adresse - uniquement les champs standard (toujours char)
                if data.get('adresse_rue'):
                    update_vals['street'] = data['adresse_rue']
                if data.get('adresse_cp'):
                    update_vals['zip'] = data['adresse_cp']
                if data.get('adresse_ville'):
                    update_vals['city'] = data['adresse_ville']
                
                if update_vals:
                    self.write(update_vals)
                
                # Retourner un message avec les informations extraites
                info_msg = "Informations extraites de la carte d'identite:\n\n"
                for key, value in data.items():
                    if value:
                        info_msg += "• %s: %s\n" % (key.replace('_', ' ').title(), value)
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Extraction reussie',
                        'message': info_msg,
                        'type': 'success',
                        'sticky': True,
                    }
                }
            else:
                raise UserError("Reponse vide de l'API")
                
        except requests.exceptions.RequestException as e:
            raise UserError("Erreur lors de l'appel API: %s" % str(e))
