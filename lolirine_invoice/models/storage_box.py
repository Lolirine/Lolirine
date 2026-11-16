# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# storage.box.status (plan) -> product.template.storage_status (boutique).
# La selection cote produit est plus pauvre : inspection et technique sont
# ranges sous "maintenance" (box non louable pour le moment).
BOX_TO_PRODUCT_STATUS = {
    'disponible': 'available',
    'occupe': 'rented',
    'reserve': 'reserved',
    'bientot_dispo': 'soon_available',
    'nettoyage': 'cleaning',
    'maintenance': 'maintenance',
    'inspection': 'maintenance',
    'technique': 'maintenance',
}
ACTIVE_SUB_STATES = ('3_progress', '4_paused')


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

    # ------------------------------------------------------------------
    # Synchronisation contrats -> plan -> boutique
    # ------------------------------------------------------------------
    def write(self, vals):
        """Tout changement de statut du plan est repercute sur la fiche
        produit (statut + ruban de la boutique)."""
        res = super().write(vals)
        if 'status' in vals or 'is_personal_use' in vals or 'product_tmpl_id' in vals:
            self._lolirine_push_status_to_product()
        return res

    def _lolirine_active_subscription(self):
        """Abonnement confirme, en cours ou en pause, qui porte ce box."""
        self.ensure_one()
        if not self.product_tmpl_id:
            return self.env['sale.order']
        return self.env['sale.order'].sudo().search([
            ('is_subscription', '=', True),
            ('state', '=', 'sale'),
            ('subscription_state', 'in', ACTIVE_SUB_STATES),
            ('order_line.product_template_id', '=', self.product_tmpl_id.id),
        ], limit=1, order='date_order desc, id desc')

    def _lolirine_last_subscription(self):
        """Dernier contrat (hors devis) ayant porte ce box, quel que soit
        son etat. Sert de garde-fou avant de liberer un box."""
        self.ensure_one()
        if not self.product_tmpl_id:
            return self.env['sale.order']
        return self.env['sale.order'].sudo().search([
            ('is_subscription', '=', True),
            ('state', 'in', ('sale', 'cancel')),
            ('order_line.product_template_id', '=', self.product_tmpl_id.id),
        ], limit=1, order='date_order desc, id desc')

    def _lolirine_push_status_to_product(self):
        """Aligne product.template (statut boutique, ruban, locataire) sur
        le box du plan."""
        for box in self:
            tmpl = box.product_tmpl_id.sudo()
            if not tmpl or 'storage_status' not in tmpl._fields:
                continue
            active_sub = box._lolirine_active_subscription()
            if box.is_personal_use:
                target = 'rented'  # jamais propose a la location
            else:
                target = BOX_TO_PRODUCT_STATUS.get(box.status, 'maintenance')
            vals = {}
            if tmpl.storage_status != target:
                vals['storage_status'] = target
            if tmpl.current_subscription_id != active_sub:
                vals['current_subscription_id'] = active_sub.id or False
            tenant = active_sub.partner_id
            if tmpl.current_tenant_id != tenant:
                vals['current_tenant_id'] = tenant.id or False
            if vals:
                tmpl.write(vals)
            # Le ruban peut etre faux meme si le statut est deja bon.
            if hasattr(tmpl, '_sync_ribbon_with_status'):
                tmpl._sync_ribbon_with_status()

    def _lolirine_sync_availability(self):
        """Recalcule client, statut et date de disponibilite depuis les
        contrats, puis repercute sur la boutique.

        Regles :
        - contrat actif -> Occupe (date videe). Exception : un box que le
          gerant a mis en "Bientot disponible" pour CE contrat le reste
          (depart annonce, date pas encore connue). Si le contrat actif a
          une date de fin a venir -> Bientot disponible a fin + 1 jour.
        - plus de contrat actif et box "Occupe" -> libere uniquement si le
          dernier contrat du box est bien CLOTURE (6_churn). Un contrat
          annule ou supprime ne libere jamais le box (cas Careme / Libert).
        - "Bientot disponible" date et sans contrat -> Disponible a la date.
        - maintenance, nettoyage, inspection, technique, reserve et usage
          personnel ne sont jamais ecrases tant qu'il n'y a pas de contrat.
        """
        today = fields.Date.context_today(self)
        prev_sub = {b.id: b.current_subscription_id.id for b in self}
        self._compute_current_customer()

        for box in self:
            if box.is_personal_use or not box.product_tmpl_id:
                continue
            active_sub = box._lolirine_active_subscription()
            vals = {}

            if active_sub:
                end = active_sub.end_date
                if end and end >= today:
                    vals = {'status': 'bientot_dispo',
                            'date_available': end + timedelta(days=1)}
                elif (box.status == 'bientot_dispo'
                        and prev_sub.get(box.id) == active_sub.id):
                    vals = {}  # depart annonce a la main : on n'y touche pas
                else:
                    vals = {'status': 'occupe', 'date_available': False}

            elif box.status == 'occupe':
                last = box._lolirine_last_subscription()
                if last and last.subscription_state == '6_churn':
                    free_on = (last.end_date or today) + timedelta(days=1)
                    if free_on <= today:
                        vals = {'status': 'disponible', 'date_available': False}
                    else:
                        vals = {'status': 'bientot_dispo',
                                'date_available': free_on}
                else:
                    _logger.warning(
                        "Box %s : occupe sans contrat actif et dernier contrat "
                        "non cloture (%s) - statut laisse tel quel, a verifier.",
                        box.name, last.name or 'aucun')

            elif (box.status == 'bientot_dispo' and box.date_available
                    and box.date_available <= today):
                vals = {'status': 'disponible', 'date_available': False}

            vals = {k: v for k, v in vals.items() if box[k] != v}
            if vals:
                old = box.status
                box.write(vals)
                if 'status' in vals:
                    box.message_post(body=_(
                        "Statut synchronisé depuis les contrats : %(old)s → %(new)s"
                    ) % {'old': old, 'new': box.status})

        self._lolirine_push_status_to_product()
        return True

    @api.model
    def cron_lolirine_sync_availability(self):
        """Passage quotidien : filet de securite + bascule des box
        "Bientot disponible" arrives a leur date."""
        self.search([])._lolirine_sync_availability()
        return True
