import json
import logging
import time
import uuid
import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'

DEFAULT_SYSTEM_PROMPT = (
    'Tu es l assistant virtuel de Lolirine Garde-Meuble, un service de self-stockage '
    'situe a Boninne (Namur), Belgique. '
    'Adresse: Rue de la Dreve Boninas 2, B-5021 Boninne. '
    'Telephones: 0498/52.11.31 et 0497/44.41.46. '
    'Email: gardemeuble@lolirine.be. '
    'TVA: BE0650.891.279. '
    '\n\n'
    'HORAIRES BUREAU: Lundi au Jeudi 9h00-18h00, Vendredi 9h00-17h00, Samedi 10h00-16h00, Dimanche ferme. '
    'ACCES AUX BOX: 24h/24 et 7j/7 sans frais supplementaires (contrairement a d autres operateurs). '
    '\n\n'
    'LOCALISATION: A proximite du centre-ville de Namur, a 5 minutes de l autoroute E411. '
    'Parking accessible PMR, entree accessible PMR. '
    '\n\n'
    'TARIFS MENSUELS EN VIGUEUR (HTVA): '
    '- 10,00 m3 (4,00 m2) : 80 euros/mois '
    '- 10,50 m3 (4,20 m2) : 80 euros/mois '
    '- 12,00 m3 (5,00 m2) : 90 euros/mois (rez-de-chaussee) '
    '- 12,50 m3 (5,00 m2) : 85 a 95 euros/mois selon le box '
    '- 15,00 m3 (6,00 m2) : 115 euros/mois '
    '- 17,00 m3 (6,80 m2) : 130 euros/mois '
    '- 18,00 m3 (7,20 m2) : 135 euros/mois '
    '- 18,50 m3 (7,40 m2) : 140 euros/mois '
    '- 20,00 m3 (8,00 m2) : 150 euros/mois '
    '- 21,50 m3 (8,60 m2) : 160 euros/mois '
    '- 22,00 m3 (8,81 m2) : 165 a 170 euros/mois '
    '- 24,00 m3 (9,60 m2) : 180 euros/mois '
    '- 25,00 m3 (10,00 m2) : 190 euros/mois '
    '- 30,00 m3 (12,00 m2) : 225 euros/mois '
    '\n\n'
    'CAPACITE: 76 box au total sur 2 niveaux (rez-de-chaussee et premier etage). '
    'Les box au rez-de-chaussee sont accessibles de plain-pied. '
    'Les box a l etage necessitent le service gerbeur pour les objets lourds. '
    'Pour connaitre les box disponibles en temps reel, inviter le client a consulter '
    'la page Disponibilite sur le site ou a appeler. '
    '\n\n'
    'SERVICE GERBEUR: Pour les box a l etage, un gerbeur electrique est disponible '
    'pour aider a monter/descendre les effets. Rendez-vous obligatoire minimum 3 jours '
    'a l avance, uniquement pendant les heures de bureau. '
    '\n\n'
    'SECURITE: Entrepot ultra-securise, locaux sains et chauffes, '
    'videosurveillance 24h/24, systeme d acces par badge individuel, alarme. '
    'Chaque client conserve sa propre cle/cadenas pour son box. '
    '\n\n'
    'CLIENTS: Particuliers et professionnels. '
    'Contrat flexible, preavis de 1 mois. Location au mois. '
    'Paiement par virement bancaire. '
    '\n\n'
    'AVIS CLIENTS: Note de 5.0/5 (plus de 20 avis). '
    'Les clients apprecient: proprete, securite, bon accueil, prix competitifs. '
    '\n\n'
    'CONSEILS DE STOCKAGE que tu peux donner: '
    '- Emballer les meubles avec des couvertures ou du papier bulle '
    '- Demonter ce qui peut l etre (lits, armoires, tables) '
    '- Utiliser des cartons solides et les fermer avec du ruban adhesif '
    '- Placer les objets lourds en bas, les legers en haut '
    '- Laisser un passage pour acceder a tout le box '
    '- Ne pas stocker de denrees perissables, produits inflammables ou dangereux '
    '- Proteger matelas et canapes avec des housses '
    '\n\n'
    'REGLES: Reponds toujours en francais. Sois professionnel, rassurant et concis. '
    'Tu peux donner les tarifs ci-dessus car ce sont les tarifs en vigueur. '
    'Pour la disponibilite exacte des box, invite a appeler au 0498/52.11.31 '
    'ou 0497/44.41.46 ou envoyer un email a gardemeuble@lolirine.be. '
    'Ne jamais inventer d informations non fournies ici.'
)


class StorageChatController(http.Controller):

    def _get_param(self, key, default=''):
        return request.env['ir.config_parameter'].sudo().get_param(
            'lolirine_storage_chat.' + key, default
        )

    def _check_rate_limit(self, session_id):
        max_per_session = int(self._get_param('max_messages_session', '50'))
        Conv = request.env['storage.chat.conversation'].sudo()
        conv = Conv.search([('name', '=', session_id), ('state', '=', 'active')], limit=1)
        if conv and conv.message_count >= max_per_session * 2:
            return False
        return True

    @http.route('/storage_chat/config', type='json', auth='public', website=True)
    def get_config(self):
        return {
            'enabled': self._get_param('enabled', 'True') == 'True',
            'welcome_message': self._get_param(
                'welcome_message',
                'Bonjour! Je suis votre assistant Lolirine Garde-Meuble. Comment puis-je vous aider?'
            ),
            'primary_color': self._get_param('primary_color', '#C91E18'),
            'secondary_color': self._get_param('secondary_color', '#8B0000'),
            'position': self._get_param('position', 'right'),
            'web_search_enabled': self._get_param('web_search', 'True') == 'True',
            'max_messages': int(self._get_param('max_messages_session', '50')),
        }

    @http.route('/storage_chat/send', type='json', auth='public', website=True, csrf=True)
    def send_message(self, session_id=None, message='', conversation_history=None):
        api_key = self._get_param('api_key', '')
        if not api_key:
            return {'error': 'API non configuree. Contactez l administrateur.'}
        if self._get_param('enabled', 'True') != 'True':
            return {'error': 'Chat IA temporairement desactive.'}
        if not message or not message.strip():
            return {'error': 'Message vide.'}
        message = message.strip()[:2000]
        if not session_id:
            session_id = str(uuid.uuid4())
        if not self._check_rate_limit(session_id):
            return {'error': 'Limite de messages atteinte pour cette session.'}

        model_name = self._get_param('model', 'claude-sonnet-4-20250514')
        max_tokens = int(self._get_param('max_tokens', '1024'))
        system_prompt = self._get_param('system_prompt', '') or DEFAULT_SYSTEM_PROMPT

        messages = []
        if conversation_history and isinstance(conversation_history, list):
            for msg in conversation_history[-20:]:
                if msg.get('role') in ('user', 'assistant') and msg.get('content'):
                    messages.append({'role': msg['role'], 'content': msg['content']})
        if not messages or messages[-1].get('content') != message:
            messages.append({'role': 'user', 'content': message})

        payload = {
            'model': model_name,
            'max_tokens': max_tokens,
            'system': system_prompt,
            'messages': messages,
        }
        if self._get_param('web_search', 'True') == 'True':
            payload['tools'] = [{'type': 'web_search_20250305', 'name': 'web_search'}]

        start_time = time.time()
        try:
            resp = requests.post(
                ANTHROPIC_API_URL,
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                },
                json=payload,
                timeout=60,
            )
            data = resp.json()
            elapsed_ms = int((time.time() - start_time) * 1000)
            if resp.status_code != 200:
                _logger.error('Storage Chat API Error %s: %s', resp.status_code, data)
                err_msg = data.get('error', {}).get('message', 'Erreur API')
                return {'error': 'Erreur: ' + err_msg[:100]}
        except requests.exceptions.Timeout:
            return {'error': 'La requete a expire. Reessayez.'}
        except Exception as e:
            _logger.error('Storage Chat Exception: %s', str(e))
            return {'error': 'Erreur de connexion. Verifiez votre reseau.'}

        text_parts = []
        web_sources = []
        has_web_search = False
        for block in data.get('content', []):
            if block.get('type') == 'text':
                text_parts.append(block['text'])
            elif block.get('type') == 'web_search_tool_result':
                has_web_search = True
                for r in block.get('content', []):
                    if r.get('type') == 'web_search_result':
                        web_sources.append({
                            'title': r.get('title', ''),
                            'url': r.get('url', ''),
                        })

        assistant_text = '\n'.join(text_parts)
        tokens_in = data.get('usage', {}).get('input_tokens', 0)
        tokens_out = data.get('usage', {}).get('output_tokens', 0)

        if self._get_param('save_conversations', 'True') == 'True':
            try:
                Conv = request.env['storage.chat.conversation'].sudo()
                conv = Conv.search([
                    ('name', '=', session_id), ('state', '=', 'active')
                ], limit=1)
                if not conv:
                    vals = {
                        'name': session_id,
                        'source_url': request.httprequest.referrer or '',
                        'ip_address': request.httprequest.remote_addr or '',
                        'user_agent': (request.httprequest.user_agent.string or '')[:250],
                    }
                    if not request.env.user._is_public():
                        vals['partner_id'] = request.env.user.partner_id.id
                        vals['visitor_name'] = request.env.user.partner_id.name
                    conv = Conv.create(vals)

                Msg = request.env['storage.chat.message'].sudo()
                Msg.create({
                    'conversation_id': conv.id,
                    'role': 'user',
                    'content': message,
                })
                Msg.create({
                    'conversation_id': conv.id,
                    'role': 'assistant',
                    'content': assistant_text,
                    'has_web_search': has_web_search,
                    'web_sources': json.dumps(web_sources) if web_sources else False,
                    'tokens_used': tokens_out,
                    'response_time_ms': elapsed_ms,
                    'model_used': model_name,
                })
            except Exception as e:
                _logger.warning('Storage Chat save error: %s', str(e))

        return {
            'session_id': session_id,
            'response': assistant_text,
            'web_sources': web_sources[:5],
            'has_web_search': has_web_search,
            'tokens': {'input': tokens_in, 'output': tokens_out},
        }

    @http.route('/storage_chat/rate', type='json', auth='public', website=True)
    def rate_conversation(self, session_id, rating):
        if not session_id or str(rating) not in ('1', '2', '3', '4', '5'):
            return {'error': 'Parametre invalide'}
        conv = request.env['storage.chat.conversation'].sudo().search(
            [('name', '=', session_id)], limit=1
        )
        if conv:
            conv.write({'rating': str(rating)})
            return {'success': True}
        return {'error': 'Conversation non trouvee'}

    @http.route('/storage_chat/close', type='json', auth='public', website=True)
    def close_conversation(self, session_id):
        if not session_id:
            return {'error': 'Parametre invalide'}
        conv = request.env['storage.chat.conversation'].sudo().search(
            [('name', '=', session_id), ('state', '=', 'active')], limit=1
        )
        if conv:
            conv.write({'state': 'closed'})
            return {'success': True}
        return {'error': 'Conversation non trouvee'}
