from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    peppol_eas = fields.Selection([
        ('0208', '0208 - BE:EN'),
        ('9930', '9930 - BE:VAT'),
    ], string="EAS (Peppol)", help="Electronic Address Scheme pour Peppol")

    peppol_endpoint = fields.Char(
        string="Endpoint Peppol",
        help="Identifiant Peppol du partenaire (ex: numero d'entreprise pour BE:EN)"
    )

    auto_send_invoice = fields.Boolean(
        string="Envoi auto factures",
        default=False,
        help="Envoyer automatiquement les factures par email lors de la confirmation"
    )
