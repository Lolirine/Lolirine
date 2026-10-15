# -*- coding: utf-8 -*-
"""Corrige une seule fois le domaine du Pool Store.

Avant cette version, data/website_data.xml n'était pas en noupdate et
remettait le domaine "lolirine-pool.be" à chaque mise à jour du module.
Le fichier est désormais en noupdate="1" : on corrige ici l'enregistrement
existant, et on le marque noupdate pour qu'il ne soit plus jamais réécrit.
"""
import logging

_logger = logging.getLogger(__name__)

OLD_DOMAINS = ("lolirine-pool.be", "https://lolirine-pool.be", "http://lolirine-pool.be",
               "https://www.lolirine-pool.be", "www.lolirine-pool.be")
NEW_DOMAIN = "https://www.lolirinepoolstore.be"


def migrate(cr, version):
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
         WHERE module = 'lolirine_pool_website' AND name = 'website_pool' AND model = 'website'
        """
    )
    row = cr.fetchone()
    if not row:
        _logger.warning("lolirine_pool_website: enregistrement website_pool introuvable")
        return
    website_id = row[0]
    cr.execute(
        "UPDATE website SET domain = %s WHERE id = %s AND (domain IS NULL OR domain IN %s)",
        (NEW_DOMAIN, website_id, OLD_DOMAINS),
    )
    _logger.info("lolirine_pool_website: domaine du site %s -> %s (%s ligne)", website_id, NEW_DOMAIN, cr.rowcount)
    cr.execute(
        """
        UPDATE ir_model_data SET noupdate = TRUE
         WHERE module = 'lolirine_pool_website' AND name = 'website_pool'
        """
    )
