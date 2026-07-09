# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Company-dependent : la preference peut differer par societe (utile en multi-company)
    property_purchase_journal_id = fields.Many2one(
        'account.journal',
        string="Journal d'achat par defaut",
        company_dependent=True,
        domain="[('type', '=', 'purchase')]",
        help=(
            "Journal d'achat utilise par defaut lors de la creation d'une facture "
            "fournisseur pour ce partenaire. Laisser vide pour utiliser le journal "
            "d'achat par defaut de la societe."
        ),
    )

    property_sale_journal_id = fields.Many2one(
        'account.journal',
        string="Journal de vente par defaut",
        company_dependent=True,
        domain="[('type', '=', 'sale')]",
        help=(
            "Journal de vente utilise par defaut lors de la creation d'une facture "
            "client pour ce partenaire. Laisser vide pour utiliser le journal de "
            "vente par defaut de la societe."
        ),
    )
