# -*- coding: utf-8 -*-
from odoo import models

# Rapports standard d'Odoo Achats (mise en page de la société = garde-meuble)
RAPPORTS_ACHAT = ('purchase.report_purchasequotation', 'purchase.report_purchaseorder')


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """Bons fournisseurs dropship du Pool Store : le bouton « Imprimer », le menu
        d'impression et la pièce jointe de « Envoyer une demande de prix » produisent
        le « Bon de commande fournisseur » Pool Store au lieu du modèle standard."""
        if res_ids:
            report = self._get_report(report_ref)
            if report.report_name in RAPPORTS_ACHAT:
                ids = [res_ids] if isinstance(res_ids, int) else list(res_ids)
                bons = self.env['purchase.order'].browse(ids).exists()
                if bons and all(bons.mapped('is_dropship_order')):
                    pool = self.env.ref('lolirine_pool_dropship.action_report_dropship_purchase_order',
                                        raise_if_not_found=False)
                    if pool:
                        return super()._render_qweb_pdf(pool, res_ids, data=data)
        return super()._render_qweb_pdf(report_ref, res_ids, data=data)
