from odoo import api, fields, models
from odoo.exceptions import UserError


class LolirineQuotationWizard(models.TransientModel):
    _name = "lolirine.quotation.wizard"
    _description = "Assistant creation devis Lolirine"

    partner_id = fields.Many2one(
        "res.partner",
        string="Client (optionnel)",
        help="Laissez vide pour un devis general sans client specifique"
    )
    line_ids = fields.One2many(
        "lolirine.quotation.wizard.line",
        "wizard_id",
        string="Produits"
    )
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Si on vient d'un produit, l'ajouter automatiquement
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        
        if active_model == 'product.template' and active_id:
            product_tmpl = self.env['product.template'].browse(active_id)
            # Trouver le product.product correspondant
            product = product_tmpl.product_variant_id
            if product:
                res['line_ids'] = [(0, 0, {
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': product.lst_price,
                })]
        elif active_model == 'product.product' and active_id:
            product = self.env['product.product'].browse(active_id)
            res['line_ids'] = [(0, 0, {
                'product_id': product.id,
                'quantity': 1,
                'price_unit': product.lst_price,
            })]
        
        return res

    def action_print_quotation(self):
        """Imprimer le devis PDF directement"""
        self.ensure_one()
        
        if not self.line_ids:
            raise UserError("Veuillez ajouter au moins un produit")
        
        # Générer le PDF avec les données du wizard
        return self.env.ref('lolirine_contract.action_report_quotation_wizard').report_action(self)

    def action_create_and_send(self):
        """Créer un abonnement et envoyer le devis par email"""
        self.ensure_one()
        
        if not self.line_ids:
            raise UserError("Veuillez ajouter au moins un produit")
        
        if not self.partner_id:
            raise UserError("Veuillez selectionner un client pour envoyer le devis par email")
        
        # Créer l'abonnement
        order_lines = []
        for line in self.line_ids:
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'price_unit': line.price_unit,
            }))
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': order_lines,
        })
        
        # Ouvrir l'assistant d'envoi d'email
        template = self.env.ref("lolirine_contract.email_template_quotation", raise_if_not_found=False)
        compose_form = self.env.ref("mail.email_compose_message_wizard_form", raise_if_not_found=False)
        
        ctx = {
            "default_model": "sale.order",
            "default_res_ids": sale_order.ids,
            "default_template_id": template.id if template else False,
            "default_composition_mode": "comment",
            "force_email": True,
        }
        
        return {
            "name": "Envoyer le devis",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form.id, "form")],
            "view_id": compose_form.id,
            "target": "new",
            "context": ctx,
        }

    @api.depends('line_ids.subtotal')
    def _compute_totals(self):
        for wizard in self:
            wizard.amount_untaxed = sum(wizard.line_ids.mapped('subtotal'))
            wizard.amount_tax = wizard.amount_untaxed * 0.21
            wizard.amount_total = wizard.amount_untaxed + wizard.amount_tax
    
    amount_untaxed = fields.Monetary(string="Total HTVA", compute="_compute_totals", currency_field='currency_id')
    amount_tax = fields.Monetary(string="TVA (21%)", compute="_compute_totals", currency_field='currency_id')
    amount_total = fields.Monetary(string="Total TVAC", compute="_compute_totals", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)


class LolirineQuotationWizardLine(models.TransientModel):
    _name = "lolirine.quotation.wizard.line"
    _description = "Ligne devis Lolirine"

    wizard_id = fields.Many2one("lolirine.quotation.wizard", string="Wizard", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Produit", required=True)
    quantity = fields.Float(string="Quantite", default=1)
    price_unit = fields.Float(string="Prix unitaire HTVA")
    subtotal = fields.Float(string="Sous-total", compute="_compute_subtotal", store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price
