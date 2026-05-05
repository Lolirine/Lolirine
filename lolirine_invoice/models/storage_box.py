# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class StorageBox(models.Model):
    """Extension de storage.box (storage_plan_module) pour ajouter
    des champs et actions de gestion interne Lolirine.
    """
    _inherit = "storage.box"

    is_personal_use = fields.Boolean(
        string="Usage personnel",
        default=False,
        help="Cocher si ce box est utilisé personnellement (par exemple par "
             "le gérant) et ne doit pas être facturé ni proposé à la location. "
             "Ces box seront exclus des audits de cohérence (statut 'Personal use').",
    )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_mark_as_personal(self):
        """Bouton : marque la box comme usage personnel + statut 'inspection'.

        Refuse si la box est sous contrat actif (il faut d'abord clôturer).
        """
        for box in self:
            if box.current_subscription_id:
                raise UserError(_(
                    "Impossible : la box %(box)s est sous contrat (%(sub)s pour %(client)s).\n"
                    "Vous devez d'abord clôturer le contrat avant de la marquer comme personnelle."
                ) % {
                    'box': box.name,
                    'sub': box.current_subscription_id.name,
                    'client': box.current_customer_name or '',
                })
            box.write({
                'is_personal_use': True,
                'status': 'inspection',
            })
            box.message_post(
                body=_("Box marquée comme usage personnel — statut mis à 'En inspection'.")
            )
        return True

    def action_unmark_as_personal(self):
        """Bouton : retire le statut personnel + remet en disponible."""
        for box in self:
            box.write({
                'is_personal_use': False,
                'status': 'disponible',
            })
            box.message_post(
                body=_("Box remise en exploitation — statut mis à 'Disponible'.")
            )
        return True
