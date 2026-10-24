import json
import logging
import re
import time
import uuid
import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _msg_langue(fr, nl, en):
    """Message d'erreur dans la langue du visiteur (site en /fr, /nl, /en)."""
    lg = (request.env.lang or 'fr_BE')[:2] if request else 'fr'
    return {'nl': nl, 'en': en}.get(lg, fr)

ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'
MODELE_DEFAUT = 'claude-sonnet-5-5'
# Modèles retirés par Anthropic : remplacés automatiquement par leur successeur
MODELES_RETIRES = {
    'claude-sonnet-4-20250514': 'claude-sonnet-5-5',
    'claude-haiku-4-5-20251001': 'claude-haiku-5-5',
}

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

    REGLES = (
        '\n\nREGLES DE REPONSE :\n'
        '- Reponds dans la langue du visiteur (francais par defaut ; neerlandais ou anglais s il ecrit dans ces langues).\n'
        '- Appuie-toi d abord sur les sections CONTENU DU SITE et PRODUITS DU SITE ci-dessous : '
        'c est la source officielle pour les produits, prix, services, livraison et contact de la boutique.\n'
        '- N invente jamais un prix, un stock, un delai ou une caracteristique absente de ces sections ; '
        'si tu ne sais pas, propose au visiteur de contacter la boutique (page contact).\n'
        '- Quand tu cites un produit, une categorie ou une page, donne exactement le lien fourni.\n'
        '- La recherche web sert uniquement aux conseils techniques generaux (dosages, entretien, normes), '
        'jamais pour recommander un autre vendeur.\n'
    )

    def _website_id(self):
        return request.website.id if getattr(request, 'website', None) else None

    def _search_knowledge(self, query):
        Know = request.env['ai.chat.knowledge'].sudo()
        essentiels, pertinentes = Know.chercher(query, website_id=self._website_id())
        if not essentiels and not pertinentes:
            return ''
        lignes = ['\n\nCONTENU DU SITE (source officielle) :']
        for rec in essentiels | pertinentes:
            lignes.append('### %s%s\n%s' % (rec.name, (' — ' + rec.url) if rec.url else '', (rec.content or '')[:1800]))
        return '\n'.join(lignes)

    def _search_products(self, query):
        if self._get_param('product_search', 'True') != 'True':
            return '', []
        from ..models.ai_chat_knowledge import mots_cles, normaliser
        mots = list(dict.fromkeys(mots_cles(query)))[:6]
        bruts = [w for w in re.findall(r'[\w\-/]{3,}', query) if normaliser(w) in mots or any(c.isdigit() for c in w)][:6]
        termes = list(dict.fromkeys(mots + bruts))
        if not termes:
            return '', []
        Product = request.env['product.template'].sudo()
        domain = [('is_published', '=', True), ('sale_ok', '=', True)]
        site_id = self._website_id()
        if site_id:
            domain += ['|', ('website_id', '=', False), ('website_id', '=', site_id)]
            param_site = self._get_param('website_id', '0') or '0'
            if 'is_pool_product' in Product._fields and param_site.isdigit() and int(param_site) == site_id:
                domain.append(('is_pool_product', '=', True))
        champs = ['name', 'default_code', 'public_categ_ids.name']
        if 'pool_brand_id' in Product._fields:
            champs.append('pool_brand_id.name')
        conditions = [(c, 'ilike', t) for t in termes for c in champs]
        domain += ['|'] * (len(conditions) - 1) + conditions
        candidats = Product.search(domain, limit=80)
        if not candidats:
            return '', []

        def note(p):
            nom = normaliser(p.name)
            cats = normaliser(' '.join(p.public_categ_ids.mapped('name')))
            marque = normaliser(p.pool_brand_id.name) if 'pool_brand_id' in Product._fields and p.pool_brand_id else ''
            n = 0.0
            for m in mots:
                n += 3 if m in nom else 0
                n += 1 if m in cats else 0
                n += 2 if m in marque else 0
            for b in bruts:
                if p.default_code and normaliser(b) == normaliser(p.default_code):
                    n += 6
            n += 0.5 if p.image_128 else 0
            n += 0.3 if p.list_price > 0 else 0
            return n

        products = candidats.sorted(note, reverse=True)[:8]
        base = request.website.get_base_url() if site_id else ''
        lignes = ['\n\nPRODUITS DU SITE correspondant a la question (prix catalogue) :']
        for i, p in enumerate(products):
            prix = ('%.2f EUR' % p.list_price) if p.list_price > 0 else 'sur devis'
            cat = ', '.join(p.public_categ_ids.mapped('name')[:2])
            lignes.append('- %s | %s | %s | %s%s' % (p.name, prix, cat, base, p.website_url or ''))
            if i < 2 and 'accessory_product_ids' in Product._fields and p.accessory_product_ids:
                acc = p.accessory_product_ids[:4]
                lignes.append('    accessoires conseilles : %s' % '; '.join(
                    '%s (%s%s)' % (a.name, base, a.product_tmpl_id.website_url or '') for a in acc))
        return '\n'.join(lignes), products.ids

    @http.route('/ai_chat/config', type='jsonrpc', auth='public', website=True)
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
            'teaser_delay': int(self._get_param('teaser_delay', '5')),
            'teaser_interval': int(self._get_param('teaser_interval', '24')),
        }

    @http.route('/ai_chat/send', type='jsonrpc', auth='public', website=True, csrf=True)
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

        model_name = self._get_param('model', MODELE_DEFAUT) or MODELE_DEFAUT
        model_name = MODELES_RETIRES.get(model_name, model_name)
        max_tokens = int(self._get_param('max_tokens', '1024'))
        system_prompt = self._get_param('system_prompt', '') or DEFAULT_SYSTEM_PROMPT

        system_prompt += self.REGLES
        try:
            system_prompt += self._search_knowledge(message)
        except Exception as e:
            _logger.warning('AI Chat knowledge error: %s', str(e))
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
                return {'error': _msg_langue(
                    "L'assistant est momentanément indisponible. "
                    "Réessayez dans un instant ou contactez-nous via la page contact.",
                    "De assistent is tijdelijk niet beschikbaar. "
                    "Probeer het zo meteen opnieuw of neem contact met ons op via de contactpagina.",
                    "The assistant is temporarily unavailable. "
                    "Please try again shortly or contact us via the contact page.")}
        except requests.exceptions.Timeout:
            return {'error': _msg_langue("La requête a expiré. Réessayez.",
                                         "De aanvraag duurde te lang. Probeer opnieuw.",
                                         "The request timed out. Please try again.")}
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

    @http.route('/ai_chat/rate', type='jsonrpc', auth='public', website=True)
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

    @http.route('/ai_chat/close', type='jsonrpc', auth='public', website=True)
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

