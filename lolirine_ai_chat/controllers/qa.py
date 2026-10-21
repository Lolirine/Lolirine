import time

from odoo import http
from odoo.http import request

# anti-abus très simple : 1 question / 30 s et 10 / heure par adresse IP
_DERNIERES = {}


class ProductQuestionController(http.Controller):

    def _trop_rapide(self):
        ip = request.httprequest.remote_addr or '?'
        maintenant = time.time()
        historique = [t for t in _DERNIERES.get(ip, []) if maintenant - t < 3600]
        if (historique and maintenant - historique[-1] < 30) or len(historique) >= 10:
            return True
        historique.append(maintenant)
        _DERNIERES[ip] = historique
        return False

    @http.route('/shop/question/<int:tmpl_id>', type='http', auth='public', website=True, methods=['POST'])
    def poser_question(self, tmpl_id, question='', auteur='', email='', site_web='', **kw):
        tmpl = request.env['product.template'].sudo().browse(tmpl_id).exists()
        if not tmpl or not tmpl.website_published:
            return request.redirect('/shop')
        url = tmpl.website_url or '/shop'
        question = (question or '').strip()[:1000]
        # « site_web » est un champ piège invisible : rempli = robot
        if site_web or len(question) < 8 or self._trop_rapide():
            return request.redirect(url + '?lpq=erreur#lpq')
        vals = {
            'product_tmpl_id': tmpl.id,
            'website_id': request.website.id,
            'question': question,
            'auteur': (auteur or '').strip()[:40] or False,
            'email': (email or '').strip()[:120] or False,
            'lang': request.env.lang,
        }
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
            vals['partner_id'] = partner.id
            vals['auteur'] = vals['auteur'] or (partner.name or '').split(' ')[0]
            vals['email'] = vals['email'] or partner.email
        request.env['lolirine.product.question'].sudo().create(vals)
        return request.redirect(url + '?lpq=merci#lpq')

    @http.route('/shop/question/utile', type='jsonrpc', auth='public', website=True)
    def question_utile(self, question_id):
        q = request.env['lolirine.product.question'].sudo().browse(int(question_id)).exists()
        if not q or q.state != 'publiee':
            return {'ok': False}
        q.votes_utiles += 1
        return {'ok': True, 'votes': q.votes_utiles}
