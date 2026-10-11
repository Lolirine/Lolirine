import logging
import time

from odoo import api, fields, models
from odoo.http import request

from .pool_universe import _SHOP_CACHE, SHOP_TTL

_logger = logging.getLogger(__name__)

# Blocs du groupe « Vitrines produits » qui reçoivent un aperçu dans la fenêtre « Insérer un bloc »
PREVIEW_BLOCKS = ('showcase', 'tiles', 'lowprice', 'saison_hivernage', 'saison_remise_en_route')
PREVIEW_ITEMS = 8


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

    # ------------------------------------------------------------------
    # Aperçus de la fenêtre « Insérer un bloc » (constructeur de site)
    # Lecture seule : appelé depuis render_public_asset (curseur en lecture).
    # ------------------------------------------------------------------
    @api.model
    def _lolirine_snippet_previews(self):
        """{bloc: html} pour le site courant, mis en cache 10 minutes."""
        website = self.get_current_website()
        if not website:
            return {}
        key = ('snippet_preview', website.id, self.env.lang)
        hit = _SHOP_CACHE.get(key)
        if hit and time.time() - hit[0] < SHOP_TTL:
            return hit[1]
        previews = {}
        for block in PREVIEW_BLOCKS:
            try:
                previews[block] = website._lolirine_snippet_preview(block)
            except Exception:
                _logger.exception("Lolirine : aperçu du bloc %s impossible", block)
                previews[block] = ''
        _SHOP_CACHE[key] = (time.time(), previews)
        return previews

    @staticmethod
    def _pu_trim(data, size=PREVIEW_ITEMS):
        """Copie d'un bloc avec moins de produits (l'aperçu est réduit à 30 %)."""
        if not data:
            return data
        data = dict(data)
        if data.get('items'):
            data['items'] = data['items'][:size]
            data['duration'] = max(20, round(len(data['items']) * 3.5))
        if data.get('rows'):
            data['rows'] = [dict(row, items=row['items'][:size],
                                 duration=max(20, round(len(row['items'][:size]) * 3.5)))
                            for row in data['rows']]
        return data

    @staticmethod
    def _pu_period_label(campaign):
        return "du %02d/%02d au %02d/%02d" % (
            campaign.start_day or 1, campaign.start_month or 1,
            campaign.end_day or 31, campaign.end_month or 12)

    def _lolirine_snippet_preview(self, block):
        """HTML de l'aperçu d'un bloc : bandeau d'état + contenu réel (réduit)."""
        self.ensure_one()
        values = {'website': self, 'pc': False, 'pu_home': False, 'block': block,
                  'pv_level': 'on', 'pv_text': '', 'pv_empty': ''}

        if block.startswith('saison_'):
            code = block[len('saison_'):]
            campaign = self.env['lolirine.pool.campaign'].sudo().with_context(active_test=False).search([
                ('code', '=', code), ('website_id', 'in', [self.id, False]),
            ], limit=1)
            if not campaign:
                values.update(pv_level='off', pv_text="Encart introuvable",
                              pv_empty="Créez-le dans Site Web → Configuration → Encarts saisonniers.")
            else:
                period = self._pu_period_label(campaign)
                if not campaign.active or campaign.mode == 'off':
                    values.update(pv_level='off',
                                  pv_text="Masqué : n'apparaît pas sur le site")
                elif campaign.mode == 'on':
                    values.update(pv_level='on', pv_text="Toujours affiché")
                elif campaign._in_period():
                    values.update(pv_level='on',
                                  pv_text="Affiché en ce moment · %s" % period)
                else:
                    values.update(pv_level='wait',
                                  pv_text="Hors période · s'affichera %s" % period)
                values['pc'] = self._pu_trim(campaign._block_data(self))
                if not values['pc']:
                    values['pv_empty'] = ("Pas assez de produits avec image pour le défilé "
                                          "(minimum 4) : vérifiez les catégories et mots-clés de l'encart.")
        else:
            if not self.pu_home_enabled:
                values.update(pv_level='off',
                              pv_text="Vitrines d'accueil désactivées dans les réglages du site")
            elif self.pu_home_auto:
                values.update(pv_level='wait',
                              pv_text="Placement automatique actif : ce bloc est déjà sur l'accueil")
            else:
                values.update(pv_level='on',
                              pv_text="Contenu renouvelé automatiquement sur le site publié")
            blocks = self._lolirine_home_blocks() if self.pu_home_enabled else {}
            if blocks and blocks.get(block):
                trimmed = dict(blocks)
                if block in ('showcase', 'lowprice'):
                    trimmed[block] = self._pu_trim(blocks[block])
                values['pu_home'] = trimmed
            else:
                values['pv_empty'] = "Rien à afficher pour l'instant avec les réglages actuels."

        return self.env['ir.qweb']._render('lolirine_pool_universe.snippet_preview', values)
