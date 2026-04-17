# -*- coding: utf-8 -*-
"""
pool_catalog_pdf_wizard_methods.py
==================================
Méthodes pour ouvrir les wizards depuis le modèle d'import principal.
"""

from odoo import models


class PoolCatalogPdfImport(models.Model):
    _inherit = 'pool.catalog.pdf.import'
    
    def action_push_wizard(self):
        """Ouvre le wizard de push vers production."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Push images - {self.filename}',
            'res_model': 'pool.catalog.image.push.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_pdf_import_id': self.id,
            }
        }
    
    def action_bulk_assign_wizard(self):
        """Ouvre le wizard d'attribution en masse."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Attribution en masse - {self.filename}',
            'res_model': 'pool.catalog.image.bulk.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_pdf_import_id': self.id,
            }
        }
