# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Mapping statut → priorité pour le tri (plus petit = plus urgent)
STATUS_PRIORITY = {
    'multiple_so': 1,
    'partner_mismatch': 2,
    'plan_orphan': 3,
    'so_orphan': 4,
    'occupied_no_so': 5,
    'no_box_product': 6,
    'personal_use': 7,
    'vacant': 8,
    'ok': 9,
}

INCONSISTENT_STATUSES = (
    'multiple_so', 'partner_mismatch', 'plan_orphan',
    'so_orphan', 'occupied_no_so',
)


class LolirineBoxConsistencyWizard(models.TransientModel):
    _name = 'lolirine.box.consistency.wizard'
    _description = "Audit de cohérence box ↔ contrat"

    consistency_line_ids = fields.One2many(
        'lolirine.box.consistency.line',
        'wizard_id',
        string="Résultats",
    )

    has_results = fields.Boolean(compute='_compute_stats')
    total_boxes = fields.Integer(string="Box analysés", compute='_compute_stats')
    total_ok = fields.Integer(string="✓ OK", compute='_compute_stats')
    total_vacant = fields.Integer(string="○ Vacants (libres)", compute='_compute_stats')
    total_personal_use = fields.Integer(string="🏠 Usage personnel", compute='_compute_stats')
    total_multiple_so = fields.Integer(string="🚨 Conflits multi-SO", compute='_compute_stats')
    total_partner_mismatch = fields.Integer(string="🚨 Partner divergent", compute='_compute_stats')
    total_plan_orphan = fields.Integer(string="⚠ Plan orphelin", compute='_compute_stats')
    total_so_orphan = fields.Integer(string="⚠ SO orphelin", compute='_compute_stats')
    total_occupied_no_so = fields.Integer(string="⚠ Occupé sans SO", compute='_compute_stats')
    total_no_box_product = fields.Integer(string="⚠ SO sans box", compute='_compute_stats')
    total_inconsistent = fields.Integer(string="Total incohérences", compute='_compute_stats')
    total_resyncable = fields.Integer(compute='_compute_stats')

    @api.depends('consistency_line_ids', 'consistency_line_ids.status')
    def _compute_stats(self):
        for wiz in self:
            lines = wiz.consistency_line_ids
            wiz.has_results = bool(lines)
            wiz.total_boxes = len(lines)
            wiz.total_ok = len(lines.filtered(lambda l: l.status == 'ok'))
            wiz.total_vacant = len(lines.filtered(lambda l: l.status == 'vacant'))
            wiz.total_personal_use = len(lines.filtered(lambda l: l.status == 'personal_use'))
            wiz.total_multiple_so = len(lines.filtered(lambda l: l.status == 'multiple_so'))
            wiz.total_partner_mismatch = len(lines.filtered(lambda l: l.status == 'partner_mismatch'))
            wiz.total_plan_orphan = len(lines.filtered(lambda l: l.status == 'plan_orphan'))
            wiz.total_so_orphan = len(lines.filtered(lambda l: l.status == 'so_orphan'))
            wiz.total_occupied_no_so = len(lines.filtered(lambda l: l.status == 'occupied_no_so'))
            wiz.total_no_box_product = len(lines.filtered(lambda l: l.status == 'no_box_product'))
            wiz.total_inconsistent = len(lines.filtered(
                lambda l: l.status in INCONSISTENT_STATUSES + ('no_box_product',)
            ))
            # Lignes effectivement resynchronisables (qui ont un box associé)
            wiz.total_resyncable = len(lines.filtered(
                lambda l: l.status in INCONSISTENT_STATUSES and l.box_id
            ))

    # ==================== ACTION : LANCER L'AUDIT ====================

    def action_run_audit(self):
        self.ensure_one()
        self.consistency_line_ids.unlink()

        if 'storage.box' not in self.env:
            raise UserError(_(
                "Le module 'storage_plan_module' n'est pas installé ou le modèle storage.box est introuvable."
            ))

        all_boxes = self.env['storage.box'].search([])

        active_subs = self.env['sale.order'].search([
            ('is_subscription', '=', True),
            ('state', '=', 'sale'),
            ('subscription_state', 'in', ['3_progress', '4_paused', '5_renewed']),
        ])

        so_by_template = {}
        for so in active_subs:
            for line in so.order_line:
                if not line.product_id or line.display_type:
                    continue
                if 'FRAIS' in (line.product_id.default_code or '').upper():
                    continue
                tmpl_id = line.product_id.product_tmpl_id.id
                so_by_template.setdefault(tmpl_id, []).append(so)

        line_vals_list = []

        for box in all_boxes:
            tmpl_id = box.product_tmpl_id.id if box.product_tmpl_id else False
            sos_for_box = so_by_template.get(tmpl_id, []) if tmpl_id else []

            vals = {
                'wizard_id': self.id,
                'box_id': box.id,
                'box_code': box.display_name or box.name or '',
                'product_tmpl_id': tmpl_id or False,
                'plan_partner_id': box.current_partner_id.id if box.current_partner_id else False,
                'plan_subscription_id': box.current_subscription_id.id if box.current_subscription_id else False,
                'date_available': box.date_available or False,
                'active_so_ids': [(6, 0, [s.id for s in sos_for_box])],
            }

            if len(sos_for_box) > 1:
                vals['status'] = 'multiple_so'
                vals['expected_partner_id'] = sos_for_box[0].partner_id.id
                vals['details'] = "Conflit : %d SOs actifs : %s" % (
                    len(sos_for_box),
                    ', '.join(s.name for s in sos_for_box),
                )

            elif len(sos_for_box) == 1:
                so = sos_for_box[0]
                vals['expected_partner_id'] = so.partner_id.id

                if box.current_subscription_id and box.current_subscription_id.id == so.id:
                    if (box.current_partner_id
                            and box.current_partner_id.id != so.partner_id.id):
                        vals['status'] = 'partner_mismatch'
                        vals['details'] = "Plan: %s | SO: %s" % (
                            box.current_partner_id.name or '?',
                            so.partner_id.name or '?',
                        )
                    else:
                        vals['status'] = 'ok'
                        vals['details'] = ""
                elif box.current_subscription_id:
                    old_so = box.current_subscription_id
                    vals['status'] = 'plan_orphan'
                    vals['details'] = ("Plan référence %s (état: %s) "
                                       "mais SO actif réel = %s") % (
                        old_so.name,
                        old_so.subscription_state or old_so.state,
                        so.name,
                    )
                else:
                    vals['status'] = 'so_orphan'
                    vals['details'] = ("SO actif %s (%s) non reflété dans le plan") % (
                        so.name,
                        so.partner_id.name or '?',
                    )

            else:
                if box.current_subscription_id:
                    vals['status'] = 'plan_orphan'
                    vals['details'] = ("Plan référence %s (état: %s) "
                                       "mais aucun SO actif réel") % (
                        box.current_subscription_id.name,
                        box.current_subscription_id.subscription_state
                            or box.current_subscription_id.state,
                    )
                elif getattr(box, 'is_personal_use', False):
                    # Box utilisé personnellement par le gérant — pas une incohérence
                    vals['status'] = 'personal_use'
                    vals['details'] = "Usage personnel (non commercialisé)"
                elif not box.date_available:
                    vals['status'] = 'occupied_no_so'
                    vals['details'] = ("Plan dit occupé (date_available vide) "
                                       "mais aucun SO actif")
                else:
                    vals['status'] = 'vacant'
                    vals['details'] = "Disponible depuis le %s" % (
                        box.date_available.strftime('%d/%m/%Y'),
                    )

            line_vals_list.append((0, 0, vals))

        # SOs actifs sur des produits sans storage.box correspondant
        all_box_template_ids = set(all_boxes.mapped('product_tmpl_id.id'))
        for so in active_subs:
            for sline in so.order_line:
                if not sline.product_id or sline.display_type:
                    continue
                if 'FRAIS' in (sline.product_id.default_code or '').upper():
                    continue
                tmpl_id = sline.product_id.product_tmpl_id.id
                if tmpl_id not in all_box_template_ids:
                    line_vals_list.append((0, 0, {
                        'wizard_id': self.id,
                        'box_id': False,
                        'box_code': sline.product_id.default_code or '?',
                        'product_tmpl_id': tmpl_id,
                        'expected_partner_id': so.partner_id.id,
                        'active_so_ids': [(6, 0, [so.id])],
                        'status': 'no_box_product',
                        'details': ("SO %s référence le produit '%s' mais "
                                    "aucun storage.box ne lui correspond") % (
                            so.name,
                            sline.product_id.default_code or sline.product_id.name,
                        ),
                    }))

        self.consistency_line_ids = line_vals_list
        return self._reload()

    # ==================== ACTIONS DE RESYNCHRONISATION ====================

    def action_resync_all_inconsistent(self):
        """Force le recompute de _compute_current_customer sur tous les box
        dont l'audit a détecté une incohérence."""
        self.ensure_one()
        boxes_to_sync = self.consistency_line_ids.filtered(
            lambda l: l.status in INCONSISTENT_STATUSES and l.box_id
        ).mapped('box_id')

        if not boxes_to_sync:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Resynchronisation"),
                    'message': _("Aucun box à resynchroniser."),
                    'type': 'info',
                },
            }

        synced_count = 0
        errors = []
        for box in boxes_to_sync:
            try:
                box._compute_current_customer()
                synced_count += 1
            except Exception as e:
                errors.append("%s: %s" % (box.display_name, str(e)[:100]))
                _logger.exception("Erreur resync box %s", box.display_name)

        # Re-run l'audit pour montrer le résultat
        self.action_run_audit()

        msg = _("%d box resynchronisé(s).") % synced_count
        if errors:
            msg += _(" Erreurs : %s") % ' | '.join(errors[:5])

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Resynchronisation terminée"),
                'message': msg,
                'type': 'success' if not errors else 'warning',
                'sticky': bool(errors),
                'next': self._reload(),
            },
        }

    def action_filter_inconsistent(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Incohérences box ↔ contrat"),
            'res_model': 'lolirine.box.consistency.line',
            'view_mode': 'list,form',
            'domain': [
                ('wizard_id', '=', self.id),
                ('status', 'not in', ('ok', 'vacant')),
            ],
            'target': 'current',
        }

    def action_filter_vacant(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Box vacants disponibles"),
            'res_model': 'lolirine.box.consistency.line',
            'view_mode': 'list,form',
            'domain': [
                ('wizard_id', '=', self.id),
                ('status', '=', 'vacant'),
            ],
            'target': 'current',
        }

    def _reload(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.box.consistency.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }


class LolirineBoxConsistencyLine(models.TransientModel):
    _name = 'lolirine.box.consistency.line'
    _description = "Ligne d'audit de cohérence box"
    _order = 'priority, box_code'

    wizard_id = fields.Many2one(
        'lolirine.box.consistency.wizard',
        ondelete='cascade',
        required=True,
        index=True,
    )

    box_id = fields.Many2one('storage.box', string="Box (plan)", readonly=True)
    box_code = fields.Char(string="Code", readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string="Produit", readonly=True)

    plan_partner_id = fields.Many2one(
        'res.partner', string="Partner (plan)", readonly=True,
    )
    plan_subscription_id = fields.Many2one(
        'sale.order', string="SO référencé par le plan", readonly=True,
    )
    expected_partner_id = fields.Many2one(
        'res.partner', string="Partner (SO actif)", readonly=True,
    )
    active_so_ids = fields.Many2many(
        'sale.order', string="SOs actifs sur ce box", readonly=True,
    )
    date_available = fields.Date(string="Disponible depuis", readonly=True)

    status = fields.Selection([
        ('ok', '✓ OK'),
        ('vacant', '○ Vacant'),
        ('personal_use', '🏠 Usage personnel'),
        ('multiple_so', '🚨 Conflit multi-SO'),
        ('partner_mismatch', '🚨 Partner divergent'),
        ('plan_orphan', '⚠ Plan orphelin'),
        ('so_orphan', '⚠ SO orphelin'),
        ('occupied_no_so', '⚠ Occupé sans SO'),
        ('no_box_product', '⚠ SO sans box'),
    ], string="Statut", readonly=True, index=True)

    priority = fields.Integer(compute='_compute_priority', store=True)

    details = fields.Char(string="Détails", readonly=True)

    @api.depends('status')
    def _compute_priority(self):
        for line in self:
            line.priority = STATUS_PRIORITY.get(line.status, 99)

    def action_open_box(self):
        self.ensure_one()
        if not self.box_id:
            raise UserError(_("Aucun box associé à cette ligne."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'storage.box',
            'res_id': self.box_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_first_so(self):
        self.ensure_one()
        if not self.active_so_ids:
            raise UserError(_("Aucun SO actif associé à cette ligne."))
        if len(self.active_so_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': self.active_so_ids[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _("SOs en conflit sur %s", self.box_code),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.active_so_ids.ids)],
            'target': 'current',
        }

    def action_open_plan_so(self):
        self.ensure_one()
        if not self.plan_subscription_id:
            raise UserError(_("Aucun SO référencé par le plan."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.plan_subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_resync_box(self):
        """Force le recompute de _compute_current_customer sur ce box.

        Utile pour corriger les box dont les valeurs stockées sont obsolètes
        (cas des SO clôturés en 6_churn ou cancel non reflétés dans le plan).
        """
        self.ensure_one()
        if not self.box_id:
            raise UserError(_("Aucun box associé à cette ligne."))

        try:
            self.box_id._compute_current_customer()
        except Exception as e:
            _logger.exception("Erreur resync box %s", self.box_id.display_name)
            raise UserError(_("Erreur lors de la resynchronisation : %s") % e)

        # Re-run audit pour rafraîchir l'affichage
        self.wizard_id.action_run_audit()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Box resynchronisé"),
                'message': _("Le box %s a été resynchronisé avec succès.") % self.box_code,
                'type': 'success',
                'next': self.wizard_id._reload(),
            },
        }
