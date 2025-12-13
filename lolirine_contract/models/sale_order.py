from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    contract_access_code = fields.Char(string="Code acces")
    contract_forklift_code = fields.Char(string="Code gerbeur")
    contract_deposit_date = fields.Date(string="Date de depot des effets")
    contract_signature_date = fields.Date(string="Date de signature", default=fields.Date.context_today)
    contract_signature_location = fields.Char(string="Lieu de signature", default="Boninne")
    contract_deposit_amount = fields.Monetary(string="Montant caution", compute='_compute_contract_amounts', store=True)
    contract_monthly_rent = fields.Monetary(string="Loyer mensuel", compute='_compute_contract_amounts', store=True)
    contract_dossier_fees = fields.Monetary(string="Frais de dossier", compute='_compute_contract_amounts', store=True)

    @api.depends('order_line', 'order_line.price_subtotal', 'order_line.product_id')
    def _compute_contract_amounts(self):
        for order in self:
            monthly_rent = 0.0
            dossier_fees = 0.0
            for line in order.order_line:
                if line.product_id and line.product_id.recurring_invoice:
                    monthly_rent += line.price_subtotal
                elif line.product_id and 'dossier' in (line.product_id.name or '').lower():
                    dossier_fees += line.price_subtotal
            order.contract_monthly_rent = monthly_rent
            order.contract_dossier_fees = dossier_fees
            order.contract_deposit_amount = monthly_rent * 2

    def action_send_contract(self):
        self.ensure_one()
        template = self.env.ref('lolirine_contract.email_template_contract', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        return True
