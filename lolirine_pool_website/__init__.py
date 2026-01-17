# -*- coding: utf-8 -*-
from . import models


def _post_init_hook(env):
    """
    Configure le site Pool Store après l'installation du module.
    Met à jour les informations de contact.
    """
    Website = env['website']
    
    # Chercher le site Pool Store
    pool_website = Website.search([
        '|', '|',
        ('name', 'ilike', 'Pool Store'),
        ('name', 'ilike', 'Lolirine Pool'),
        ('domain', 'ilike', 'lolirinepoolstore'),
    ], limit=1)
    
    if pool_website:
        # Mettre à jour les informations
        pool_website.write({
            'name': 'Lolirine Pool Store',
            'domain': 'www.lolirinepoolstore.be',
            'is_pool_website': True,
        })
        
        # Mettre à jour les informations de la société liée si possible
        if pool_website.company_id:
            # Les infos de contact sont généralement sur la société
            # On peut aussi les mettre dans les paramètres du site
            pass
        
        env.cr.commit()

