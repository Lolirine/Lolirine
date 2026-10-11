from odoo import _, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _lolirine_universe_data(self, website=None):
        """Données du défilé « univers » pour la fiche produit (False si rien à montrer)."""
        self.ensure_one()
        return self.env['lolirine.pool.universe'].sudo()._get_for_product(self, website)

    def action_pu_campaign_exclude(self):
        """Bouton « Exclure » de l'onglet Produits trouvés d'un encart saisonnier."""
        campaign = self.env['lolirine.pool.campaign'].browse(
            self.env.context.get('pu_campaign_id')).exists()
        if not campaign:
            raise UserError(_("Enregistrez d'abord l'encart, puis recommencez."))
        campaign.write({'exclude_product_ids': [(4, product.id) for product in self]})
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}
