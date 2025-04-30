from odoo import http
from odoo.http import request

class BoxMapController(http.Controller):

    @http.route('/boxes/plan', type='http', auth='public', website=True)
    def box_map(self, **kwargs):
        boxes = request.env['box.stockage'].sudo().search([])
        return request.render('box_storage_map.box_map_template', {'boxes': boxes})
