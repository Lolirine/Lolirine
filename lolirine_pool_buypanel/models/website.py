"""Prix TTC belges pour les visiteurs anonymes hors Union européenne.

Odoo choisit la position fiscale d'un visiteur non connecté d'après la
géolocalisation de son adresse IP. Un visiteur situé hors UE (et Googlebot,
qui explore depuis les États-Unis) reçoit la position « Import/Export » :
TVA à 0 %, donc des prix hors TVA affichés comme « Toutes taxes comprises »,
et un flux Google Merchant Center envoyé hors TVA.

Sur le Pool Store, un visiteur anonyme hors UE voit donc les prix belges
TVAC. À la commande, la position fiscale est recalculée sur l'adresse de
livraison (export à 0 % si le client est réellement hors UE).
"""
from odoo import models
from odoo.http import request

SITE_POOL_STORE = 6
CLE_SESSION = 'fiscal_position_id'


class Website(models.Model):
    _inherit = 'website'

    def _get_and_cache_current_fiscal_position(self):
        fpos_sudo = super()._get_and_cache_current_fiscal_position()
        if self.id != SITE_POOL_STORE or not request:
            return fpos_sudo
        visiteur_anonyme = self.partner_id.id == self.env.user.partner_id.id
        if not visiteur_anonyme:
            return fpos_sudo
        pays = request.geoip.country_code
        europe = self.env.ref('base.europe', raise_if_not_found=False)
        if europe and pays and pays in europe.sudo().country_ids.mapped('code'):
            return fpos_sudo
        # Hors UE ou pays inconnu : pas de position fiscale = TVA belge
        request.session[CLE_SESSION] = False
        return self.env['account.fiscal.position'].sudo()
