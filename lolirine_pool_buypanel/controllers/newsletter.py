"""Inscription à la newsletter du Pool Store + code de bienvenue.

Les formulaires « Recevez les nouveautés… » du site (pied de page, guides)
envoient l'adresse vers /website/newsletter/subscribe. Cette adresse
n'existait pas (erreur 404) : on l'ajoute ici.

À la PREMIÈRE inscription d'une adresse :
  1. l'adresse est ajoutée à la liste de diffusion « Newsletter » ;
  2. un contact client est retrouvé (ou créé) pour cette adresse ;
  3. un coupon à usage unique du programme de bienvenue lui est attribué :
     Odoo envoie aussitôt l'e-mail du programme avec le code.
Une adresse déjà inscrite ne reçoit pas de second code.

Paramètres (Configuration > Paramètres techniques) :
  lolirine_pool_buypanel.newsletter_list_id     liste de diffusion (défaut 1)
  lolirine_pool_buypanel.newsletter_program_id  programme de coupons (0 = pas de code)
"""
import logging

from odoo import http, tools
from odoo.http import request

_logger = logging.getLogger(__name__)
P = 'lolirine_pool_buypanel.'


class PoolNewsletter(http.Controller):

    @http.route('/website/newsletter/subscribe', type='http', auth='public', website=True,
                methods=['POST'], sitemap=False)
    def pool_newsletter_subscribe(self, email='', website_url='', **kw):
        # Champ piège invisible : un robot qui le remplit est ignoré
        if kw.get('lp_hp'):
            return request.redirect('/')
        email = tools.email_normalize(email or '')
        if not email:
            return request.render('lolirine_pool_buypanel.newsletter_merci',
                                  {'lp_erreur': True, 'lp_code': False, 'lp_deja': False})

        icp = request.env['ir.config_parameter'].sudo()
        list_id = int(icp.get_param(P + 'newsletter_list_id', 1) or 1)
        program_id = int(icp.get_param(P + 'newsletter_program_id', 0) or 0)

        Subscription = request.env['mailing.subscription'].sudo()
        Contact = request.env['mailing.contact'].sudo()
        deja = Subscription.search([('list_id', '=', list_id),
                                    ('contact_id.email_normalized', '=', email)], limit=1)
        if deja:
            if deja.opt_out:
                deja.opt_out = False
        else:
            contact = Contact.search([('email_normalized', '=', email)], limit=1) \
                or Contact.create({'name': email.split('@')[0], 'email': email})
            Subscription.create({'contact_id': contact.id, 'list_id': list_id})

        code_envoye = False
        program = request.env['loyalty.program'].sudo().browse(program_id).exists()
        if not deja and program and program.active:
            try:
                Partner = request.env['res.partner'].sudo()
                partner = Partner.search([('email_normalized', '=', email)], limit=1) or Partner.create({
                    'name': email.split('@')[0],
                    'email': email,
                    'lang': request.lang.code,
                })
                Card = request.env['loyalty.card'].sudo()
                if not Card.search_count([('program_id', '=', program.id), ('partner_id', '=', partner.id)]):
                    Card.create({'program_id': program.id, 'partner_id': partner.id, 'points': 1})
                    code_envoye = True
                    # L'e-mail du code est mis en file d'attente : on demande à Odoo
                    # de traiter la file tout de suite plutôt qu'au prochain passage horaire.
                    cron = request.env.ref('mail.ir_cron_mail_scheduler_action', raise_if_not_found=False)
                    if cron:
                        cron.sudo()._trigger()
            except Exception:
                _logger.exception("Newsletter : code de bienvenue non créé pour %s", email)

        return request.render('lolirine_pool_buypanel.newsletter_merci', {
            'lp_erreur': False, 'lp_code': code_envoye, 'lp_deja': bool(deja),
        })
