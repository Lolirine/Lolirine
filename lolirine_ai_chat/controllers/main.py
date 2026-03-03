import json
import logging
import time
import uuid
import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'


class AiChatController(http.Controller):

    def _get_param(self, key, default=''):
        return request.env['ir.config_parameter'].sudo().get_param(
            'lolirine_ai_chat.' + key, default
        )

    @http.route('/ai_chat/config', type='json', auth='public', website=True)
    def get_config(self):
        return {
            'enabled': self._get_param('enabled', 'True') == 'True',
            'welcome_message': self._get_param('welcome_message', 'Bonjour!'),
            'primary_color': self._get_param('primary_color', '#0369a1'),
            'web_search_enabled': self._get_param('web_search', 'True') == 'True',
        }

    @http.route('/ai_chat/send', type='json', auth='public', website=True, csrf=True)
    def send_message(self, session_id=None, message='', conversation_history=None):
        api_key = self._get_param('api_key', '')
        if not api_key:
            return {'error': 'API non configuree.'}
        if self._get_param('enabled', 'True') != 'True':
            return {'error': 'Chat desactive.'}
        if not message or not message.strip():
            return {'error': 'Message vide.'}
        if not session_id:
            session_id = str(uuid.uuid4())

        model_name = self._get_param('model', 'claude-sonnet-4-20250514')
        max_tokens = int(self._get_param('max_tokens', '1024'))
        system_prompt = self._get_param('system_prompt', '') or ''

        # Search products
        if self._get_param('product_search', 'True') == 'True':
            words = [w for w in message.split() if len(w) > 3]
            if words:
                domain = [('website_published', '=', True), ('name', 'ilike', words[0])]
                prods = request.env['product.template'].sudo().search(domain, limit=8)
                if prods:
                    lines = ['\n\nPRODUITS DU SITE:']
                    for p in prods:
                        lines.append('- %s | %.2f EUR | %s' % (p.name, p.list_price, p.website_url or ''))
                    system_prompt += '\n'.join(lines)

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
                _logger.error('AI Chat API Error: %s', data)
                return {'error': 'Erreur API. Reessayez.'}
        except requests.exceptions.Timeout:
            return {'error': 'Timeout. Reessayez.'}
        except Exception as e:
            _logger.error('AI Chat Exception: %s', str(e))
            return {'error': 'Erreur de connexion.'}

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
        tokens_used = data.get('usage', {}).get('output_tokens', 0)

        # Save to DB
        try:
            Conv = request.env['ai.chat.conversation'].sudo()
            conv = Conv.search([('name', '=', session_id), ('state', '=', 'active')], limit=1)
            if not conv:
                vals = {'name': session_id, 'source_url': request.httprequest.referrer or ''}
                if not request.env.user._is_public():
                    vals['partner_id'] = request.env.user.partner_id.id
                    vals['visitor_name'] = request.env.user.partner_id.name
                conv = Conv.create(vals)
            Msg = request.env['ai.chat.message'].sudo()
            Msg.create({'conversation_id': conv.id, 'role': 'user', 'content': message})
            Msg.create({
                'conversation_id': conv.id,
                'role': 'assistant',
                'content': assistant_text,
                'has_web_search': has_web_search,
                'web_sources': json.dumps(web_sources) if web_sources else False,
                'tokens_used': tokens_used,
                'response_time_ms': elapsed_ms,
                'model_used': model_name,
            })
        except Exception as e:
            _logger.warning('AI Chat save error: %s', str(e))

        return {
            'session_id': session_id,
            'response': assistant_text,
            'web_sources': web_sources[:5],
            'has_web_search': has_web_search,
        }

    @http.route('/ai_chat/rate', type='json', auth='public', website=True)
    def rate_conversation(self, session_id, rating):
        if not session_id or str(rating) not in ('1', '2', '3', '4', '5'):
            return {'error': 'Invalid'}
        conv = request.env['ai.chat.conversation'].sudo().search(
            [('name', '=', session_id)], limit=1
        )
        if conv:
            conv.write({'rating': str(rating)})
            return {'success': True}
        return {'error': 'Not found'}
