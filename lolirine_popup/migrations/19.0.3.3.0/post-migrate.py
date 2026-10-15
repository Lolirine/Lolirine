# -*- coding: utf-8 -*-
"""Rattache les popups existants au site du garde-meuble.

Avant cette version, les popups n'avaient pas de site web et s'affichaient
aussi sur le Lolirine Pool Store (popup « Box Disponible »). Tous les popups
existants concernent le garde-meuble : on les rattache au site par défaut
(Srl Lolirine). Un popup peut ensuite être mis sur « tous les sites » en
vidant le champ Site web.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env.ref('website.default_website', raise_if_not_found=False)
    if not website:
        _logger.warning("lolirine_popup : site par défaut introuvable, popups non rattachés")
        return
    popups = env['lolirine.popup.config'].with_context(active_test=False).search(
        [('website_id', '=', False)])
    popups.write({'website_id': website.id})
    _logger.info("lolirine_popup : %s popup(s) rattaché(s) au site %s (%s)",
                 len(popups), website.name, website.id)
