from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    contract_access_code = fields.Char(string="Code accès")
    contract_forklift_code = fields.Char(string="Code gerbeur")
    contract_deposit_date = fields.Date(string="Date de dépôt des effets")
    contract_signature_date = fields.Date(string="Date de signature", default=fields.Date.context_today)
    contract_signature_location = fields.Char(string="Lieu de signature", default="Boninne")
    contract_deposit_amount = fields.Monetary(string="Montant caution", compute="_compute_contract_amounts", store=True)
    contract_monthly_rent = fields.Monetary(string="Loyer mensuel", compute="_compute_contract_amounts", store=True)
    contract_dossier_fees = fields.Monetary(string="Frais de dossier", compute="_compute_contract_amounts", store=True)

    # Champs related pour la carte d'identité du client
    partner_id_card_recto = fields.Binary(related="partner_id.id_card_recto", string="CI Recto", readonly=True)
    partner_id_card_verso = fields.Binary(related="partner_id.id_card_verso", string="CI Verso", readonly=True)
    partner_id_card_uploaded = fields.Boolean(related="partner_id.id_card_uploaded", string="CI fournie", readonly=True)

    @api.depends("order_line", "order_line.price_total", "order_line.product_id")
    def _compute_contract_amounts(self):
        for order in self:
            monthly_rent = 0.0
            dossier_fees = 0.0
            for line in order.order_line:
                if line.product_id and line.product_id.recurring_invoice:
                    monthly_rent += line.price_total
                elif line.product_id and "dossier" in (line.product_id.name or "").lower():
                    dossier_fees += line.price_total
            order.contract_monthly_rent = monthly_rent
            order.contract_dossier_fees = dossier_fees
            order.contract_deposit_amount = monthly_rent * 2

    def action_preview_contract(self):
        """Aperçu du contrat PDF dans le navigateur (nouvel onglet)"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/report/pdf/lolirine_contract.report_contract_document/{self.id}",
            "target": "new",
        }

    def action_preview_quotation(self):
        """Aperçu du devis PDF dans le navigateur (nouvel onglet)"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/report/pdf/lolirine_contract.report_lolirine_quotation_document/{self.id}",
            "target": "new",
        }

    def action_send_contract(self):
        """Ouvrir le wizard d'envoi du contrat"""
        self.ensure_one()
        return {
            "name": "Envoyer le contrat",
            "type": "ir.actions.act_window",
            "res_model": "send.document.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_order_id": self.id,
                "default_document_type": "contract",
                "active_id": self.id,
            },
        }

    def action_send_quotation(self):
        """Ouvrir le wizard d'envoi du devis"""
        self.ensure_one()
        return {
            "name": "Envoyer le devis",
            "type": "ir.actions.act_window",
            "res_model": "send.document.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_order_id": self.id,
                "default_document_type": "quotation",
                "active_id": self.id,
            },
        }
