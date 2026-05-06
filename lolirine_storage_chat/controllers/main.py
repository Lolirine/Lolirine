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
    'ACCES AUX BOX: 24h/24 et 7j/7 sans frais supplementaires. '
    '\n\n'
    'TARIFS MENSUELS EN VIGUEUR (HTVA): '
    '- 10,00 m3 : 80 euros/mois '
    '- 12,00 m3 : 90 euros/mois '
    '- 12,50 m3 : 85 a 95 euros/mois '
    '- 15,00 m3 : 115 euros/mois '
    '- 17,00 m3 : 130 euros/mois '
    '- 18,00 m3 : 135 euros/mois '
    '- 20,00 m3 : 150 euros/mois '
    '- 22,00 m3 : 165 a 170 euros/mois '
    '- 25,00 m3 : 190 euros/mois '
    '- 30,00 m3 : 225 euros/mois '
    '\n\n'
    'SECURITE: Videosurveillance 24h, badge individuel, alarme, locaux chauffes. '
    'CONTRAT: Flexible, preavis 1 mois. '
    'Reponds toujours en francais. Sois professionnel, rassurant et concis.'
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

    @http.route('/storage_chat/config', type='jsonrpc', auth='public', website=True)
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
            'teaser_delay': int(self._get_param('teaser_delay', '5')),
            'teaser_interval': int(self._get_param('teaser_interval', '24')),
        }

    @http.route('/storage_chat/send', type='jsonrpc', auth='public', website=True, csrf=True)
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
                Msg.create({'conversation_id': conv.id, 'role': 'user', 'content': message})
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

    @http.route('/storage_chat/rate', type='jsonrpc', auth='public', website=True)
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

    @http.route('/storage_chat/close', type='jsonrpc', auth='public', website=True)
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
