"""Suggestions d'achat dans l'espace client du Pool Store.

Sur l'aperçu en ligne d'un devis, d'une commande ou d'une facture (site 6) :
  * « À racheter »          : les produits déjà commandés (chimie, consommables...),
                               seulement une fois la commande confirmée / facturée ;
  * « Pour compléter »      : accessoires et produits optionnels/alternatifs
                               des produits commandés ;
  * complété si besoin par d'autres produits des mêmes catégories de la boutique.
Seuls les produits publiés, vendables et non « service » sont proposés.
"""
import logging

from odoo import models

_logger = logging.getLogger(__name__)

SITE_POOL_STORE = 6
MAX_RACHETER = 4
MAX_COMPLETER = 8


class LpSuggestionsMixin(models.AbstractModel):
    _name = 'lp.suggestions.mixin'
    _description = 'Pool Store : suggestions d\'achat (espace client)'

    def _lp_produits_vendables(self, templates, site):
        return templates.filtered(lambda t: t.sale_ok and t.is_published and t.type != 'service'
                                  and (not t.website_id or t.website_id == site))

    def _lp_carte(self, tmpl, site):
        prix = tmpl.list_price
        try:
            info = tmpl.with_context(website_id=site.id)._get_combination_info(add_qty=1)
            prix = info.get('price', prix)
        except Exception:  # prix catalogue en secours
            pass
        return {
            'name': tmpl.name,
            'url': tmpl.website_url,
            'img': '/web/image/product.template/%s/image_256' % tmpl.id,
            'price': prix,
        }

    def _lp_suggestions(self, lignes_templates, site, racheter=False):
        """lignes_templates : product.template déjà commandés (dans l'ordre)."""
        Tmpl = self.env['product.template'].sudo()
        deja = self._lp_produits_vendables(lignes_templates.sudo(), site)

        complements = Tmpl
        for t in lignes_templates.sudo():
            complements |= t.accessory_product_ids.product_tmpl_id
            complements |= t.optional_product_ids if 'optional_product_ids' in t._fields else Tmpl
            complements |= t.alternative_product_ids if 'alternative_product_ids' in t._fields else Tmpl
        complements = self._lp_produits_vendables(complements - lignes_templates, site)[:MAX_COMPLETER]

        if len(complements) < MAX_COMPLETER and 'public_categ_ids' in Tmpl._fields:
            categories = lignes_templates.sudo().public_categ_ids
            if categories:
                autres = Tmpl.search([
                    ('public_categ_ids', 'in', categories.ids),
                    ('id', 'not in', (lignes_templates | complements).ids),
                    ('is_published', '=', True), ('sale_ok', '=', True), ('type', '!=', 'service'),
                    ('website_id', 'in', [False, site.id]),
                ], order='website_sequence, id', limit=MAX_COMPLETER * 3)
                complements |= self._lp_produits_vendables(autres, site)[:MAX_COMPLETER - len(complements)]

        return {
            'racheter': [self._lp_carte(t, site) for t in deja[:MAX_RACHETER]] if racheter else [],
            'completer': [self._lp_carte(t, site) for t in complements],
        }


class SaleOrderSuggestions(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'lp.suggestions.mixin']

    def _lp_suggestions_portail(self, website=None):
        self.ensure_one()
        vide = {'racheter': [], 'completer': []}
        if not website or website.id != SITE_POOL_STORE:
            return vide
        try:
            lignes = self.order_line.filtered(lambda l: l.product_id and not l.display_type)
            return self._lp_suggestions(lignes.product_id.product_tmpl_id, website,
                                        racheter=self.state == 'sale')
        except Exception:
            _logger.exception("Pool Store : suggestions impossibles pour %s", self.name)
            return vide


class AccountMoveSuggestions(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'lp.suggestions.mixin']

    def _lp_suggestions_portail(self, website=None):
        self.ensure_one()
        vide = {'racheter': [], 'completer': []}
        if not website or website.id != SITE_POOL_STORE or self.move_type != 'out_invoice':
            return vide
        try:
            lignes = self.invoice_line_ids.filtered(lambda l: l.product_id and l.display_type == 'product')
            return self._lp_suggestions(lignes.product_id.product_tmpl_id, website, racheter=True)
        except Exception:
            _logger.exception("Pool Store : suggestions impossibles pour %s", self.name)
            return vide
