from odoo import http
from odoo.http import request

class ReservationBoxController(http.Controller):

    @http.route(['/formulaire-location'], type='http', auth="public", website=True)
    def formulaire_location(self, box_id=None, **kwargs):
        product = request.env['product.product'].sudo().browse(int(box_id)) if box_id else None
        return request.render('module_reservation_box.formulaire_location_template', {
            'product': product
        })

    @http.route(['/submit-location-form'], type='http', auth="public", website=True, csrf=False)
    def submit_location_form(self, **post):
        body = (
            "<p>Nom: {}</p>"
            "<p>Email: {}</p>"
            "<p>Box ID: {}</p>"
            "<p>Date de début: {}</p>"
            "<p>Message: {}</p>"
        ).format(
            post.get('name'),
            post.get('email'),
            post.get('box_id'),
            post.get('start_date'),
            post.get('message')
        )
        request.env['mail.mail'].sudo().create({
            'subject': 'Nouvelle réservation de box',
            'body_html': body,
            'email_to': 'info@lolirine.be',
        }).send()
        return request.redirect('/merci')