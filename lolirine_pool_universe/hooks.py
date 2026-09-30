"""Univers par défaut du Pool Store (website_id = 6).

Relançable depuis le shell :
    from odoo.addons.lolirine_pool_universe.hooks import seed_universes
    seed_universes(env, force=True); env.cr.commit()
"""

WEBSITE_ID = 6

# (séquence, nom, titre, sous-titre, catégories déclencheuses, gammes montrées)
UNIVERSES = [
    (5, "Liner & revêtement",
     "Pour compléter votre revêtement",
     "Pièces à sceller, éclairage, échelles et couvertures assortis",
     [104, 158],
     [159, 107, 161, 103, 105, 106, 155, 157, 160]),
    (8, "Éclairage",
     "Autour de l'éclairage",
     "Niches, transformateurs, électricité et pièces à sceller",
     [161, 103],
     [161, 103, 146, 159, 107]),
    (10, "Construction",
     "Tout pour construire votre piscine",
     "Blocs, pièces à sceller, liners, tuyauterie et équipements du bassin",
     [156, 107, 105],
     [156, 107, 105, 104, 161, 144, 121]),
    (20, "Local technique",
     "Pour équiper votre local technique",
     "Filtration, pompes, chauffage, traitement, vannes et raccords",
     [100, 110, 102, 177, 145, 168, 169, 146, 144, 108],
     [100, 110, 102, 177, 145, 146, 144, 121]),
    (30, "Traitement de l'eau",
     "Pour une eau saine et limpide",
     "Produits, analyse, régulation automatique et désinfection UV",
     [79, 183, 166],
     [183, 79, 171, 169, 177, 168, 145]),
    (40, "Nettoyage",
     "Pour l'entretien de votre bassin",
     "Robots, accessoires de nettoyage, couvertures et produits",
     [87],
     [87, 106, 155, 183]),
    (50, "Couvertures",
     "Pour protéger votre piscine",
     "Bâches, couvertures automatiques, volets et hivernage",
     [106, 155, 140],
     [106, 155, 140, 87, 193, 84]),
    (60, "Wellness",
     "Pour votre espace bien-être",
     "Spas, accessoires, traitement de l'eau et saunas",
     [93],
     [94, 97, 98, 96, 148, 149]),
    (70, "Étang & jardin",
     "Pour votre bassin et votre jardin",
     "Pompes, filtration, aération, irrigation et accessoires",
     [150, 172],
     [150, 172]),
]


def seed_universes(env, force=False):
    Universe = env['lolirine.pool.universe'].with_context(active_test=False)
    if Universe.search_count([]) and not force:
        return
    if force:
        Universe.search([]).unlink()
    website = env['website'].browse(WEBSITE_ID).exists()
    Categ = env['product.public.category']
    for seq, name, title, subtitle, triggers, related in UNIVERSES:
        Universe.create({
            'sequence': seq,
            'name': name,
            'title': title,
            'subtitle': subtitle,
            'website_id': website.id if website else False,
            'trigger_categ_ids': [(6, 0, Categ.browse(triggers).exists().ids)],
            'related_categ_ids': [(6, 0, Categ.browse(related).exists().ids)],
        })


def post_init_hook(env):
    seed_universes(env)
