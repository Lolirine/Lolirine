from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = "res.partner"
    
    # Compteur de scans TVA
    scan_tva_count = fields.Integer(
        string="Nombre de scans",
        compute="_compute_scan_tva_count"
    )
    
    # Compte fournisseur par défaut
    property_account_expense_id = fields.Many2one(
        "account.account",
        string="Compte de charge par defaut",
        domain="[('account_type', 'in', ('expense', 'expense_direct_cost'))]",
        company_dependent=True,
        help="Compte de charge utilise par defaut pour les factures de ce fournisseur"
    )

    def _compute_scan_tva_count(self):
        ScanTva = self.env['lolirine.scan.tva']
        for partner in self:
            partner.scan_tva_count = ScanTva.search_count([
                ('partner_id', '=', partner.id)
            ])

    def action_view_scan_tva(self):
        """Voir les scans TVA du fournisseur"""
        self.ensure_one()
        return {
            'name': _('Scans TVA'),
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.scan.tva',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
