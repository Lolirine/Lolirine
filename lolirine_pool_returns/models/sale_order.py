from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    pool_return_ids = fields.One2many('pool.return', 'order_id', string='Retours')
    pool_return_count = fields.Integer(compute='_compute_pool_return_count', string='Nb retours')

    def _compute_pool_return_count(self):
        for order in self:
            order.pool_return_count = len(order.pool_return_ids)

    def action_voir_retours(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('lolirine_pool_returns.action_pool_return')
        action['domain'] = [('order_id', '=', self.id)]
        action['context'] = {'default_order_id': self.id, 'default_partner_id': self.partner_id.id}
        return action

    def _lpr_lignes_retournables(self):
        """[(ligne, quantité encore retournable)] — articles livrés, hors services et port,
        moins ce qui figure déjà dans un retour non annulé/refusé."""
        self.ensure_one()
        deja = {}
        for ret in self.pool_return_ids.filtered(lambda r: r.state not in ('cancel', 'refused', 'draft')):
            for l in ret.line_ids:
                deja[l.order_line_id.id] = deja.get(l.order_line_id.id, 0.0) + l.quantite
        res = []
        for line in self.order_line:
            if line.display_type or line.is_delivery or not line.product_id or line.product_id.type == 'service':
                continue
            base = line.qty_delivered or 0.0
            reste = base - deja.get(line.id, 0.0)
            if reste > 0:
                res.append((line, reste))
        return res
