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
    'Tu es un expert en piscines, spas, jacuzzis et saunas pour Lolirine Pool Store. '
    'Tu maitrises: piscines hors-sol, enterrees, semi-enterrees, liners, couvertures, '
    'pompes, filtration (sable, cartouche, diatomees), robots nettoyeurs, '
    'traitement eau (chlore, brome, pH, electrolyse sel, oxygene actif, UV), '
    'chauffage piscine (pompes a chaleur, rechauffeurs, solaire), '
    'accessoires (echelles, douches, eclairage LED, alarmes, jeux), '
    'produits chimiques et hivernage. '
    'Reponds toujours en francais. '
    'Quand tu recommandes un produit du catalogue, inclus le lien. '
    'Pour les prix et commandes, redirige vers lolirinepoolstore.be. '
    'Sois professionnel, amical et concis.'
)


class AiChatController(http.Controller):

    def _get_param(self, key, default=''):
        return request.env['ir.config_parameter'].sudo().get_param(
            'lolirine_ai_chat.' + key, default
        )

    def _check_rate_limit(self, session_id):
        max_per_session = int(self._get_param('max_messages_session', '50'))
        Conv = request.env['ai.chat.conversation'].sudo()
        conv = Conv.search([('name', '=', session_id), ('state', '=', 'active')], limit=1)
        if conv and conv.message_count >= max_per_session * 2:
            return False
        return True

    def _search_products(self, query):
        if self._get_param('product_search', 'True') != 'True':
            return '', []
        words = [w.lower() for w in query.split() if len(w) > 3]
        if not words:
            return '', []
        Product = request.env['product.template'].sudo()
        domain = [('website_published', '=', True)]
        sub_domains = [('name', 'ilike', w) for w in words[:3]]
        if len(sub_domains) == 1:
            domain.append(sub_domains[0])
        else:
            or_domain = ['|'] * (len(sub_domains) - 1) + sub_domains
            domain.extend(or_domain)
        products = Product.search(domain, limit=8)
        if not products:
            return '', []
        product_ids = products.ids
        text_lines = ['\n\nPRODUITS DISPONIBLES SUR LE SITE:']
        for p in products:
            url = p.website_url or ''
            cat = p.categ_id.name if p.categ_id else ''
            text_lines.append(
                '- %s | %.2f EUR | Categorie: %s | %s' % (p.name, p.list_price, cat, url)
            )
        text_lines.append('Recommande ces produits quand pertinent.')
        return '\n'.join(text_lines), product_ids

    @http.route('/ai_chat/config', type='json', auth='public', website=True)
    def get_config(self):
        # Check if chat is restricted to a specific website
        website_id_str = self._get_param('website_id', '')
        if website_id_str and hasattr(request, 'website') and request.website:
            try:
                if int(website_id_str) != request.website.id:
                    return {'enabled': False}
            except (ValueError, TypeError):
                pass
        return {
            'enabled': self._get_param('enabled', 'True') == 'True',
            'welcome_message': self._get_param(
                'welcome_message',
                'Bonjour! Je suis votre assistant piscine. Comment puis-je vous aider?'
            ),
            'primary_color': self._get_param('primary_color', '#0369a1'),
            'secondary_color': self._get_param('secondary_color', '#0d9488'),
            'position': self._get_param('position', 'right'),
            'web_search_enabled': self._get_param('web_search', 'True') == 'True',
            'max_messages': int(self._get_param('max_messages_session', '50')),
        }

    @http.route('/ai_chat/send', type='json', auth='public', website=True, csrf=True)
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

        product_ctx, product_ids = self._search_products(message)
        if product_ctx:
            system_prompt += product_ctx

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
                _logger.error('AI Chat API Error %s: %s', resp.status_code, data)
                err_msg = data.get('error', {}).get('message', 'Erreur API')
                return {'error': 'Erreur: ' + err_msg[:100]}
        except requests.exceptions.Timeout:
            return {'error': 'La requete a expire. Reessayez.'}
        except Exception as e:
            _logger.error('AI Chat Exception: %s', str(e))
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
                Conv = request.env['ai.chat.conversation'].sudo()
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

                Msg = request.env['ai.chat.message'].sudo()
                Msg.create({
                    'conversation_id': conv.id,
                    'role': 'user',
                    'content': message,
                })
                msg_vals = {
                    'conversation_id': conv.id,
                    'role': 'assistant',
                    'content': assistant_text,
                    'has_web_search': has_web_search,
                    'web_sources': json.dumps(web_sources) if web_sources else False,
                    'tokens_used': tokens_out,
                    'response_time_ms': elapsed_ms,
                    'model_used': model_name,
                }
                if product_ids:
                    msg_vals['product_ids'] = [(6, 0, product_ids)]
                Msg.create(msg_vals)
            except Exception as e:
                _logger.warning('AI Chat save error: %s', str(e))

        return {
            'session_id': session_id,
            'response': assistant_text,
            'web_sources': web_sources[:5],
            'has_web_search': has_web_search,
            'tokens': {'input': tokens_in, 'output': tokens_out},
        }

    @http.route('/ai_chat/rate', type='json', auth='public', website=True)
    def rate_conversation(self, session_id, rating):
        if not session_id or str(rating) not in ('1', '2', '3', '4', '5'):
            return {'error': 'Parametre invalide'}
        conv = request.env['ai.chat.conversation'].sudo().search(
            [('name', '=', session_id)], limit=1
        )
        if conv:
            conv.write({'rating': str(rating)})
            return {'success': True}
        return {'error': 'Conversation non trouvee'}

    @http.route('/ai_chat/close', type='json', auth='public', website=True)
    def close_conversation(self, session_id):
        if not session_id:
            return {'error': 'Parametre invalide'}
        conv = request.env['ai.chat.conversation'].sudo().search(
            [('name', '=', session_id), ('state', '=', 'active')], limit=1
        )
        if conv:
            conv.write({'state': 'closed'})
            return {'success': True}
        return {'error': 'Conversation non trouvee'}

