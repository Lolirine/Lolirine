from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _lolirine_universe_data(self, website=None):
        """Données du défilé « univers » pour la fiche produit (False si rien à montrer)."""
        self.ensure_one()
        return self.env['lolirine.pool.universe'].sudo()._get_for_product(self, website)
