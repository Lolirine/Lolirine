# -*- coding: utf-8 -*-
from urllib.parse import urlparse

from odoo import models
from odoo.tools import urls


def _hote(adresse):
    """Nom d'hôte sans « www. », en minuscules ('' si l'adresse est vide)."""
    if not adresse:
        return ''
    if '://' not in adresse:
        adresse = 'https://' + adresse
    hote = (urlparse(adresse).hostname or '').lower()
    return hote[4:] if hote.startswith('www.') else hote


class LinkTracker(models.Model):
    _inherit = 'link.tracker'

    def _compute_short_url_host(self):
        """Lien court (/r/xxx) sur le domaine du site visé par le lien.

        Par défaut Odoo prend le site « courant » du backend ou celui de la
        société (le garde-meuble) : un lien vers www.lolirinepoolstore.be,
        publié depuis le Marketing social, devenait
        https://lolirine-lolirine.odoo.com/r/xxx. Si l'adresse suivie
        appartient au domaine d'un site, le lien court utilise ce domaine.
        La route /r/<code> répond sur tous les domaines de la base.
        """
        super()._compute_short_url_host()
        sites = self.env['website'].sudo().search([('domain', '!=', False)])
        par_hote = {_hote(s.domain): s for s in sites if _hote(s.domain)}
        for tracker in self:
            site = par_hote.get(_hote(tracker.url))
            if site:
                base = site.domain if '://' in site.domain else 'https://' + site.domain
                tracker.short_url_host = urls.urljoin(base, '/r/')
