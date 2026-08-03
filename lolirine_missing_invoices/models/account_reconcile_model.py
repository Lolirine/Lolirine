# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    x_no_invoice_expected = fields.Boolean(
        string="Aucune facture attendue",
        help="Les transactions bancaires captées par ce modèle n'ont jamais de "
             "facture correspondante : remboursements de crédit, TVA, virements "
             "internes, avances en compte courant, frais bancaires... Elles sont "
             "exclues du rapport « Factures manquantes » mais restent visibles "
             "dans le rapprochement bancaire tant qu'elles ne sont pas traitées.",
    )
