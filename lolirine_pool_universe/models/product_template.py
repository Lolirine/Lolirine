from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pu_campaign_excluded = fields.Boolean(
        string="Exclu de l'encart", compute='_compute_pu_campaign_excluded',
        help="Vrai si le produit est exclu de l'encart saisonnier ouvert (contexte pu_campaign_id).")

    @api.depends_context('pu_campaign_id')
    def _compute_pu_campaign_excluded(self):
        campaign = self.env['lolirine.pool.campaign'].sudo().browse(
            self.env.context.get('pu_campaign_id')).exists()
        excluded = set(campaign.exclude_product_ids.ids) if campaign else set()
        for product in self:
            product.pu_campaign_excluded = product.id in excluded

    def _lolirine_universe_data(self, website=None):
        """Données du défilé « univers » pour la fiche produit (False si rien à montrer)."""
        self.ensure_one()
        return self.env['lolirine.pool.universe'].sudo()._get_for_product(self, website)

    def _pu_context_campaign(self):
        campaign = self.env['lolirine.pool.campaign'].browse(
            self.env.context.get('pu_campaign_id')).exists()
        if not campaign:
            raise UserError(_("Enregistrez d'abord l'encart, puis recommencez."))
        return campaign

    def action_pu_campaign_exclude(self):
        """Exclut de l'encart le(s) produit(s) : bouton de ligne ou sélection multiple."""
        campaign = self._pu_context_campaign()
        campaign.write({'exclude_product_ids': [(4, product.id) for product in self]})
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    def action_pu_campaign_include(self):
        """Remet le(s) produit(s) dans l'encart."""
        campaign = self._pu_context_campaign()
        campaign.write({'exclude_product_ids': [(3, product.id) for product in self]})
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}
