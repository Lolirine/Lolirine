import json
import logging
import time
import uuid
import requests

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'


class AiChatController(http.Controller):

    def _get_config(self):
        """Retrieve all AI chat configuration parameters."""
        ICP = request.env['ir.config_parameter'].sudo()
        return {
            'api_key': ICP.get_param('lolirine_ai_chat.api_key', ''),
            'model': ICP.get_param('lolirine_ai_chat.model', 'claude-sonnet-4-20250514'),
            'max_tokens': int(ICP.get_param('lolirine_ai_chat.max_tokens', '1024')),
            'enabled': ICP.get_param('lolirine_ai_chat.enabled', 'True') == 'True',
            'web_search': ICP.get_param('lolirine_ai_chat.web_search', 'True') == 'True',
            'product_search': ICP.get_param('lolirine_ai_chat.product_search', 'True') == 'True',
            'save_conversations': ICP.get_param('lolirine_ai_chat.save_conversations', 'True') == 'True',
            'system_prompt': ICP.get_param('lolirine_ai_chat.system_prompt', ''),
            'welcome_message': ICP.get_param('lolirine_ai_chat.welcome_message', ''),
            'primary_color': ICP.get_param('lolirine_ai_chat.primary_color', '#0369a1'),
            'secondary_color': ICP.get_param('lolirine_ai_chat.secondary_color', '#0d9488'),
            'position': ICP.get_param('lolirine_ai_chat.position', 'bottom-right'),
            'max_messages_per_session': int(ICP.get_param('lolirine_ai_chat.max_messages_per_session', '50')),
            'max_messages_per_day_ip': int(ICP.get_param('lolirine_ai_chat.max_messages_per_day_ip', '100')),
        }

    def _get_product_context(self, query):
        """Search products in catalog and build context string."""
        ICP = request.env['ir.config_parameter'].sudo()
        if ICP.get_param('lolirine_ai_chat.product_search', 'True') != 'True':
            return '', []

        products = request.env['product.template'].sudo().search([
            ('website_published', '=', True),
            '|', '|',
            ('name', 'ilike', query),
            ('description_sale', 'ilike', query),
            ('public_categ_ids.name', 'ilike', query),
        ], limit=10)

        if not products:
            # Broader search: split query into words
            words = query.split()
            domain = [('website_published', '=', True)]
            word_domains = []
            for word in words:
                if len(word) > 3:
                    word_domains.append([
                        '|', '|',
                        ('name', 'ilike', word),
                        ('description_sale', 'ilike', word),
                        ('public_categ_ids.name', 'ilike', word),
                    ])
            if word_domains:
                from odoo.osv.expression import OR
                domain += OR(word_domains)
                products = request.env['product.template'].sudo().search(domain, limit=10)

        if not products:
            return '', []

        context_parts = ["\n\n📦 PRODUITS DISPONIBLES SUR LE SITE:"]
        product_ids = []
        for p in products:
            price = p.list_price
            categ = ', '.join(p.public_categ_ids.mapped('name')) or 'Non catégorisé'
            url = p.website_url or ''
            desc = (p.description_sale or '')[:200]
            context_parts.append(
                f"- {p.name} | {price:.2f}€ | Catégorie: {categ} | URL: {url}"
                + (f"\n  {desc}" if desc else "")
            )
            product_ids.append(p.id)

        return '\n'.join(context_parts), product_ids

    def _get_or_create_conversation(self, session_id):
        """Get existing conversation or create new one."""
        Conversation = request.env['ai.chat.conversation'].sudo()
        conversation = Conversation.search([
            ('session_id', '=', session_id),
            ('state', '=', 'active'),
        ], limit=1)

        if not conversation:
            vals = {
                'session_id': session_id,
                'source_url': request.httprequest.referrer or '',
                'user_agent': request.httprequest.user_agent.string or '',
                'ip_address': request.httprequest.remote_addr or '',
            }
            # Link to partner if user is logged in
            if request.env.user and not request.env.user._is_public():
                vals['partner_id'] = request.env.user.partner_id.id
                vals['visitor_name'] = request.env.user.partner_id.name
            conversation = Conversation.create(vals)

        return conversation

    # =========================================================================
    # PUBLIC ENDPOINTS
    # =========================================================================

    @http.route('/ai_chat/config', type='json', auth='public', website=True)
    def get_chat_config(self):
        """Return frontend configuration (no sensitive data)."""
        config = self._get_config()
        return {
            'enabled': config['enabled'],
            'welcome_message': config['welcome_message'],
            'primary_color': config['primary_color'],
            'secondary_color': config['secondary_color'],
            'position': config['position'],
            'web_search_enabled': config['web_search'],
            'max_messages_per_session': config['max_messages_per_session'],
        }

    @http.route('/ai_chat/send', type='json', auth='public', website=True, csrf=True)
    def send_message(self, session_id=None, message='', conversation_history=None):
        """Process a chat message and return AI response."""
        config = self._get_config()

        # Validation
        if not config['enabled']:
            return {'error': 'Le chat IA est actuellement désactivé.'}
        if not config['api_key']:
            _logger.error('AI Chat: API key not configured')
            return {'error': 'Configuration incomplète. Contactez l\'administrateur.'}
        if not message or not message.strip():
            return {'error': 'Message vide.'}

        # Session management
        if not session_id:
            session_id = str(uuid.uuid4())

        # Rate limiting check
        conversation = None
        if config['save_conversations']:
            conversation = self._get_or_create_conversation(session_id)
            msg_count = len(conversation.message_ids.filtered(lambda m: m.role == 'user'))
            if msg_count >= config['max_messages_per_session']:
                return {
                    'error': f"Limite de {config['max_messages_per_session']} messages atteinte. "
                             "Commencez une nouvelle conversation.",
                    'session_id': session_id,
                }

        # Build system prompt with product context
        system_prompt = config['system_prompt'] or ''
        product_context, product_ids = self._get_product_context(message)
        if product_context:
            system_prompt += product_context

        # Build messages for API
        messages = []
        if conversation_history and isinstance(conversation_history, list):
            for msg in conversation_history[-20:]:  # Keep last 20 messages for context
                if msg.get('role') in ('user', 'assistant') and msg.get('content'):
                    messages.append({
                        'role': msg['role'],
                        'content': msg['content'],
                    })

        # Ensure current message is included
        if not messages or messages[-1].get('content') != message:
            messages.append({'role': 'user', 'content': message})

        # Build API request
        api_payload = {
            'model': config['model'],
            'max_tokens': config['max_tokens'],
            'system': system_prompt,
            'messages': messages,
        }

        # Add web search tool if enabled
        if config['web_search']:
            api_payload['tools'] = [{
                'type': 'web_search_20250305',
                'name': 'web_search',
            }]

        # Call Anthropic API
        start_time = time.time()
        try:
            response = requests.post(
                ANTHROPIC_API_URL,
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': config['api_key'],
                    'anthropic-version': '2023-06-01',
                },
                json=api_payload,
                timeout=60,
            )
            response_data = response.json()
            elapsed_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                error_msg = response_data.get('error', {}).get('message', 'Erreur API')
                _logger.error('AI Chat API Error: %s', error_msg)
                return {'error': 'Une erreur est survenue. Réessayez dans un instant.'}

        except requests.exceptions.Timeout:
            _logger.error('AI Chat API Timeout')
            return {'error': 'Le serveur met trop de temps à répondre. Réessayez.'}
        except Exception as e:
            _logger.error('AI Chat API Exception: %s', str(e))
            return {'error': 'Erreur de connexion. Réessayez.'}

        # Extract response content
        content_blocks = response_data.get('content', [])
        text_parts = []
        web_sources = []
        has_web_search = False

        for block in content_blocks:
            if block.get('type') == 'text':
                text_parts.append(block['text'])
            elif block.get('type') == 'web_search_tool_result':
                has_web_search = True
                for result in block.get('content', []):
                    if result.get('type') == 'web_search_result':
                        web_sources.append({
                            'title': result.get('title', ''),
                            'url': result.get('url', ''),
                        })

        assistant_text = '\n'.join(text_parts)
        tokens_used = response_data.get('usage', {}).get('output_tokens', 0)

        # Save to database
        if config['save_conversations'] and conversation:
            try:
                # Save user message
                request.env['ai.chat.message'].sudo().create({
                    'conversation_id': conversation.id,
                    'role': 'user',
                    'content': message,
                })
                # Save assistant response
                request.env['ai.chat.message'].sudo().create({
                    'conversation_id': conversation.id,
                    'role': 'assistant',
                    'content': assistant_text,
                    'has_web_search': has_web_search,
                    'web_sources': json.dumps(web_sources) if web_sources else False,
                    'tokens_used': tokens_used,
                    'response_time_ms': elapsed_ms,
                    'model_used': config['model'],
                    'product_ids': [(6, 0, product_ids)] if product_ids else False,
                })
            except Exception as e:
                _logger.warning('AI Chat: Failed to save messages: %s', str(e))

        return {
            'session_id': session_id,
            'response': assistant_text,
            'web_sources': web_sources[:5],
            'has_web_search': has_web_search,
            'response_time_ms': elapsed_ms,
        }

    @http.route('/ai_chat/rate', type='json', auth='public', website=True)
    def rate_conversation(self, session_id, rating):
        """Allow user to rate a conversation."""
        if not session_id or rating not in ('1', '2', '3', '4', '5'):
            return {'error': 'Invalid rating'}

        conversation = request.env['ai.chat.conversation'].sudo().search([
            ('session_id', '=', session_id),
        ], limit=1)

        if conversation:
            conversation.write({'rating': str(rating)})
            return {'success': True}
        return {'error': 'Conversation not found'}

    @http.route('/ai_chat/close', type='json', auth='public', website=True)
    def close_conversation(self, session_id):
        """Close a conversation session."""
        if not session_id:
            return {'error': 'No session'}

        conversation = request.env['ai.chat.conversation'].sudo().search([
            ('session_id', '=', session_id),
            ('state', '=', 'active'),
        ], limit=1)

        if conversation:
            conversation.action_close()
            return {'success': True}
        return {'error': 'Conversation not found'}
