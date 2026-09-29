from odoo import models


class Website(models.Model):
    _inherit = 'website'

    def _lolirine_shop_zones(self):
        """Zones « univers » de la page boutique (liste vide si rien à montrer)."""
        self.ensure_one()
        return self.env['lolirine.pool.universe'].sudo()._get_shop_zones(self)
