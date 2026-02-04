# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request
from odoo.addons.sale_subscription.controllers.portal import CustomerPortal as SubscriptionPortal


class PortalIdCard(http.Controller):
    @http.route(['/my/id_card'], type='http', auth='user', website=False)
    def portal_id_card(self, **kw):
        partner = request.env.user.partner_id
        values = {
            'partner': partner,
            'page_name': 'id_card',
            'error': kw.get('error'),
            'success': kw.get('success'),
        }
        return request.render('lolirine_contract.portal_my_id_card', values)

    @http.route(['/my/id_card/upload'], type='http', auth='user', website=False, methods=['POST'], csrf=True)
    def portal_id_card_upload(self, **post):
        partner = request.env.user.partner_id
        
        values = {}
        error = None
        
        if 'id_card_recto' in request.httprequest.files:
            file_recto = request.httprequest.files['id_card_recto']
            if file_recto and file_recto.filename:
                file_content = file_recto.read()
                if len(file_content) > 10 * 1024 * 1024:
                    error = "Le fichier recto est trop volumineux (max 10 MB)"
                else:
                    values['id_card_recto'] = base64.b64encode(file_content)
                    values['id_card_recto_filename'] = file_recto.filename

        if 'id_card_verso' in request.httprequest.files:
            file_verso = request.httprequest.files['id_card_verso']
            if file_verso and file_verso.filename:
                file_content = file_verso.read()
                if len(file_content) > 10 * 1024 * 1024:
                    error = "Le fichier verso est trop volumineux (max 10 MB)"
                else:
                    values['id_card_verso'] = base64.b64encode(file_content)
                    values['id_card_verso_filename'] = file_verso.filename

        if error:
            return request.redirect('/my/id_card?error=%s' % error)
        if values:
            partner.sudo().write(values)
            return request.redirect('/my/id_card?success=1')
        return request.redirect('/my/id_card')


class CustomerPortalSubscription(SubscriptionPortal):

    def _get_subscription_domain(self, partner):
        domain = super()._get_subscription_domain(partner)
        current_website = request.website
        if current_website:
            domain += [
                '|',
                ('website_id', '=', current_website.id),
                ('website_id', '=', False),
            ]
        return domain
