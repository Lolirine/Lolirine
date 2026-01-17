# -*- coding: utf-8 -*-
from odoo import models, fields


class Website(models.Model):
    _inherit = 'website'
    
    is_pool_website = fields.Boolean(
        string='Site Pool Store',
        default=False,
        help="Cochez pour identifier ce site comme le Pool Store"
    )
