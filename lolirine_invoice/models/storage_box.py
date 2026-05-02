# -*- coding: utf-8 -*-

from odoo import fields, models


class StorageBox(models.Model):
    """Extension de storage.box (storage_plan_module) pour ajouter
    des champs de gestion interne Lolirine.
    """
    _inherit = "storage.box"

    is_personal_use = fields.Boolean(
        string="Usage personnel",
        default=False,
        help="Cocher si ce box est utilisé personnellement (par exemple par "
             "le gérant) et ne doit pas être facturé ni proposé à la location. "
             "Ces box seront exclus des audits de cohérence (statut 'Personal use').",
    )
