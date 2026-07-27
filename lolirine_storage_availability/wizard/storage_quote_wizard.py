# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError


class StorageQuoteWizard(models.TransientModel):
    _name = 'storage.quote.wizard'
    _description = 'Devis box de stockage'

    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
    )
    box_product_ids = fields.Many2many(
        'product.template',
        string='Box(es)',
        domain=[('is_storage_box', '=', True)],
        required=True,
    )
    sale_order_template_id = fields.Many2one(
        'sale.order.template',
        string='Modele de devis',
        default=lambda self: self._default_quote_template(),
        help="Modele de devis abonnement habituel : son plan de recurrence "
             "et ses conditions generales seront repris sur le devis.",
    )
    plan_id = fields.Many2one(
        'sale.subscription.plan',
        string='Plan de recurrence',
        compute='_compute_plan_id',
        store=True,
        readonly=False,
        required=True,
    )
    warning_message = fields.Text(
        compute='_compute_warning_message',
    )

    @api.model
    def _default_quote_template(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'lolirine_storage_availability.quote_template_id')
        if param and str(param).isdigit():
            tmpl = self.env['sale.order.template'].browse(int(param)).exists()
            if tmpl:
                return tmpl
        return self.env['sale.order.template'].search(
            [('plan_id', '!=', False)], limit=1)

    @api.depends('sale_order_template_id')
    def _compute_plan_id(self):
        for wiz in self:
            if wiz.sale_order_template_id.plan_id:
                wiz.plan_id = wiz.sale_order_template_id.plan_id
            elif not wiz.plan_id:
                wiz.plan_id = self.env['sale.subscription.plan'].search([], limit=1)

    @api.depends('box_product_ids')
    def _compute_warning_message(self):
        for wiz in self:
            rented = wiz.box_product_ids.filtered(
                lambda p: p.storage_status == 'rented')
            if rented:
                details = []
                for box in rented:
                    tenant = box.current_tenant_id.name or 'locataire inconnu'
                    sub = box.current_subscription_id.name or ''
                    details.append("- %s : loue par %s %s" % (
                        box.name, tenant, "(%s)" % sub if sub else ''))
                wiz.warning_message = (
                    "Box actuellement loue(s) :\n%s\n\n"
                    "Le devis pourra etre etabli et envoye, mais ne pourra pas "
                    "etre confirme tant que l'abonnement en cours est actif."
                    % "\n".join(details))
            else:
                wiz.warning_message = False

    def _create_quote(self):
        self.ensure_one()
        if not self.box_product_ids:
            raise UserError(_("Selectionnez au moins un box."))
        if not self.plan_id:
            raise UserError(_("Aucun plan de recurrence defini."))

        order_vals = {
            'partner_id': self.partner_id.id,
            'plan_id': self.plan_id.id,
            'origin': _("Devis box - fiche client"),
            'order_line': [
                Command.create({
                    'product_id': tmpl.product_variant_id.id,
                    'product_uom_qty': 1.0,
                })
                for tmpl in self.box_product_ids
            ],
        }
        # Reprise des conditions generales du modele de devis abonnement
        if self.sale_order_template_id and self.sale_order_template_id.note:
            order_vals['note'] = self.sale_order_template_id.note

        return self.env['sale.order'].create(order_vals)

    def action_create_quote(self):
        """Cree le devis en brouillon et ouvre sa fiche."""
        order = self._create_quote()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Devis box'),
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_and_send(self):
        """Cree le devis puis ouvre le compositeur d'e-mail :
        corps du message modifiable + PDF du devis en piece jointe.
        Rien n'est envoye tant que l'utilisateur ne confirme pas."""
        order = self._create_quote()
        return order.action_quotation_send()
