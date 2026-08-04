# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_invoice_policy = fields.Selection(
        selection=[
            ('expected', 'Facture attendue'),
            ('none', 'Jamais de facture'),
        ],
        string="Politique de facturation",
        company_dependent=False,
        help="Facture attendue : ce fournisseur emet une facture qu'il faut "
             "recuperer. Les transactions bancaires non rattachees sont signalees "
             "en priorite dans le rapport.\n"
             "Jamais de facture : achats en magasin sur ticket de caisse, frais "
             "bancaires, prelevements sans piece. Les transactions sont classees "
             "« Sans facture attendue » et sortent du rapport.\n"
             "Non defini : comportement par defaut, la transaction est signalee "
             "si aucune facture ne correspond.",
    )
    x_bank_label = fields.Char(
        string="Motif du libelle bancaire",
        help="Texte identifiant ce fournisseur dans le libelle des transactions "
             "bancaires, quand celui-ci ne porte pas son nom exact. Plusieurs "
             "motifs possibles, separes par une barre verticale.\n"
             "Exemple pour Anthropic : ANTHROPIC|CLAUDE.AI\n"
             "La comparaison ignore la casse.",
    )
