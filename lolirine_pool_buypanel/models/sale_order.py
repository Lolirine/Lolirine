from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _lp_franco_info(self):
        """Barre « livraison offerte » du panier : seuil, montant, reste, % et 3 suggestions."""
        self.ensure_one()
        Liv = self.env['lolirine.livraison'].sudo()
        seuil, base = Liv.seuil_franco(self.website_id)
        lignes = self.order_line.filtered(lambda l: not l.display_type and not getattr(l, 'is_delivery', False))
        if base == 'ht':
            montant = sum(lignes.mapped('price_subtotal'))
        else:
            montant = sum(lignes.mapped('price_total'))
        reste = max(seuil - montant, 0.0)
        info = {
            'seuil': seuil, 'base': 'HT' if base == 'ht' else 'TVAC', 'montant': montant, 'reste': reste,
            'pct': min(100, int(round(montant * 100.0 / seuil))) if seuil else 100,
            'atteint': reste <= 0, 'suggestions': [],
        }
        if reste > 0 and lignes:
            deja = set(lignes.mapped('product_id.product_tmpl_id').ids)
            cands = lignes.mapped('product_id.product_tmpl_id.accessory_product_ids.product_tmpl_id') | \
                lignes.mapped('product_id.product_tmpl_id.alternative_product_ids')
            def prix(t):
                """Prix de la liste de prix du panier, HT ou TVAC selon la base du seuil."""
                pu = self.pricelist_id._get_product_price(t.product_variant_id, 1.0) if self.pricelist_id else t.list_price
                taxes = t.taxes_id.filtered(lambda x: x.company_id == self.company_id)
                if not taxes:
                    return pu, pu
                res = taxes.compute_all(pu, product=t.product_variant_id)
                return res['total_excluded'], res['total_included']
            retenus = []
            for t in cands.filtered(lambda t: t.id not in deja and t.is_published and t.sale_ok and t.image_128):
                ht, ttc = prix(t)
                valeur = ht if base == 'ht' else ttc
                if reste <= valeur <= reste * 1.6 + 25:
                    retenus.append((valeur, t, ttc))
            retenus.sort(key=lambda x: x[0])
            info['suggestions'] = [{'tmpl': t, 'prix': ttc} for _v, t, ttc in retenus[:3]]
        return info
