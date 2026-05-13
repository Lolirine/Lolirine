# -*- coding: utf-8 -*-
import re
import logging
from odoo import models

_logger = logging.getLogger(__name__)

# Pattern utilisé pour retirer la mention "X <période> JJ/MM/AAAA au JJ/MM/AAAA"
# que sale_subscription ajoute automatiquement à la description de ligne.
# Tolérant : couvre mois / semaine(s) / jour(s) / an(s) / année(s).
_RECURRING_PERIOD_RE = re.compile(
    r'\s*\n+\s*\d+\s+'
    r'(?:mois|semaine|semaines|jour|jours|an|ans|année|années)'
    r'\s+\d{2}/\d{2}/\d{4}\s+au\s+\d{2}/\d{2}/\d{4}\s*$',
    re.IGNORECASE,
)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """
        Retire la mention de période ajoutée automatiquement par sale_subscription
        dans la description de ligne de facture. Cette mention prête à confusion
        pour les clients du garde-meuble étant donné que les conditions de paiement
        sont 'à terme échu' alors que la période affichée est celle à venir.

        Ne s'applique QUE aux lignes d'abonnement récurrentes (recurring_invoice=True),
        ce qui protège :
          - les lignes de prorata créées par le wizard de clôture
          - les lignes de frais de rappel / mise en demeure
          - toute autre ligne manuelle ou ad-hoc
        """
        vals = super()._prepare_invoice_line(**optional_values)
        if self.recurring_invoice and vals.get('name'):
            cleaned = _RECURRING_PERIOD_RE.sub('', vals['name']).rstrip()
            if cleaned != vals['name']:
                vals['name'] = cleaned
        return vals
