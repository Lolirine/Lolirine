from odoo import fields, models
from odoo.http import request

from .pool_universe import _SHOP_CACHE


class Website(models.Model):
    _inherit = 'website'

    pu_home_enabled = fields.Boolean(string="Vitrines sur la page d'accueil", default=True)
    pu_home_auto = fields.Boolean(
        string="Placement automatique", default=True,
        help="Coché : vitrine en haut, tuiles et petits prix en bas de l'accueil. "
             "Décoché : seuls les blocs déposés avec le constructeur de site s'affichent, "
             "à l'endroit où tu les as placés.")
    pu_showcase_count = fields.Integer(string="Produits dans la vitrine du haut", default=36)
    pu_home_tiles = fields.Boolean(string="Tuiles « Explorez par univers »", default=True)
    pu_home_lowprice = fields.Boolean(string="Défilé « Petits prix »", default=True)
    pu_lowprice_max = fields.Float(string="Prix maximum des petits prix (HTVA)", default=25.0)

    def write(self, vals):
        if any(key.startswith('pu_') for key in vals):
            _SHOP_CACHE.clear()
        return super().write(vals)

    def _lolirine_shop_zones(self):
        """Zones « univers » de la page boutique (liste vide si rien à montrer)."""
        self.ensure_one()
        return self.env['lolirine.pool.universe'].sudo()._get_shop_zones(self)

    def _lolirine_home_blocks(self):
        """Vitrine, tuiles et petits prix de la page d'accueil."""
        self.ensure_one()
        return self.env['lolirine.pool.universe'].sudo()._get_home_blocks(self)

    def _lolirine_is_home(self):
        """Vrai uniquement sur la page d'accueil (/, /fr, /nl…, ou l'URL d'accueil personnalisée)."""
        self.ensure_one()
        if not self.pu_home_enabled or not request:
            return False
        try:
            path = request.httprequest.path or '/'
        except RuntimeError:
            return False
        parts = [p for p in path.split('/') if p]
        codes = set(self.language_ids.mapped('url_code'))
        if parts and parts[0] in codes:
            parts = parts[1:]
        if not parts:
            return True
        home = (getattr(self, 'homepage_url', False) or '').strip('/')
        return bool(home) and '/'.join(parts) == home
