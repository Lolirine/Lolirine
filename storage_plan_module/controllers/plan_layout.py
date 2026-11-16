# -*- coding: utf-8 -*-
"""Geometrie du plan du hangar, identique a celle de www.lolirine.be.

Un SVG de 310 x 460 par niveau. Chaque entree :
    (code, x, y, largeur, hauteur, local_technique)
Les coordonnees sont celles du plan historique (echelle x1,5).
"""

PLAN_VIEWBOX = (310, 460)

PLAN_LAYOUT = [
    ('Rez-de-chauss\u00e9e', [
        ('BUR', 36, 393.5, 83.5, 58, True),
        ('CNC1', 36, 11, 118, 118, True),
        ('SDS', 223.5, 26, 50.5, 13, True),
        ('TECH', 238.5, 401, 35.5, 50.5, True),
        ('WC', 238.5, 371, 35.5, 28, True),
        ('1D15', 156, 251, 35.5, 46, False),
        ('1D16', 156, 221, 35.5, 28, False),
        ('1D17', 156, 191, 35.5, 28, False),
        ('1D18', 156, 161, 35.5, 28, False),
        ('1D19', 156, 131, 35.5, 28, False),
        ('1D20', 156, 101, 35.5, 28, False),
        ('1D21', 156, 71, 35.5, 28, False),
        ('1D22', 156, 41, 35.5, 28, False),
        ('1D23', 156, 11, 118, 28, False),
        ('1D24', 238.5, 41, 35.5, 28, False),
        ('1D25', 238.5, 71, 35.5, 28, False),
        ('1D26', 238.5, 101, 35.5, 28, False),
        ('1D27', 238.5, 131, 35.5, 28, False),
        ('1D28', 238.5, 161, 35.5, 28, False),
        ('1D29', 238.5, 191, 35.5, 28, False),
        ('1D30', 238.5, 221, 35.5, 28, False),
        ('1D31', 238.5, 251, 35.5, 28, False),
        ('1D32', 238.5, 281, 35.5, 28, False),
        ('1D33', 238.5, 311, 35.5, 28, False),
        ('1D34', 238.5, 341, 35.5, 28, False),
        ('1D35', 153, 299, 38.5, 46, False),
        ('1G01', 36, 347, 35.5, 44.5, False),
        ('1G02', 36, 317, 35.5, 28, False),
        ('1G03', 36, 287, 35.5, 28, False),
        ('1G04', 36, 257, 35.5, 28, False),
        ('1G05', 36, 227, 35.5, 28, False),
        ('1G06', 36, 197, 35.5, 28, False),
        ('1G07', 36, 167, 35.5, 28, False),
        ('1G08', 36, 131, 58, 34, False),
        ('1G09', 96, 131, 58, 34, False),
        ('1G10', 111, 167, 43, 22, False),
        ('1G11', 111, 191, 43, 28, False),
        ('1G12', 111, 221, 43, 28, False),
        ('1G13', 111, 251, 43, 46, False),
        ('1G14', 111, 299, 40, 46, False),
    ]),
    ('1er \u00e9tage', [
        ('CNC2', 36, 11, 118, 118, True),
        ('S', 73.5, 393.5, 13, 13, True),
        ('2D51', 156, 305, 35.5, 22, False),
        ('2D52', 156, 281, 35.5, 22, False),
        ('2D53', 156, 251, 35.5, 28, False),
        ('2D54', 156, 221, 35.5, 28, False),
        ('2D55', 156, 191, 35.5, 28, False),
        ('2D56', 156, 161, 35.5, 28, False),
        ('2D57', 156, 131, 35.5, 28, False),
        ('2D58', 156, 101, 35.5, 28, False),
        ('2D59', 156, 71, 35.5, 28, False),
        ('2D60', 156, 41, 35.5, 28, False),
        ('2D61', 156, 11, 58, 28, False),
        ('2D62', 216, 11, 58, 28, False),
        ('2D63', 238.5, 41, 35.5, 43, False),
        ('2D64', 238.5, 86, 35.5, 28, False),
        ('2D65', 238.5, 116, 35.5, 28, False),
        ('2D66', 238.5, 146, 35.5, 28, False),
        ('2D67', 238.5, 176, 35.5, 28, False),
        ('2D68', 238.5, 206, 35.5, 28, False),
        ('2D69', 238.5, 236, 35.5, 28, False),
        ('2D70', 238.5, 266, 35.5, 28, False),
        ('2D71', 238.5, 296, 35.5, 28, False),
        ('2D72', 238.5, 326, 35.5, 28, False),
        ('2D73', 238.5, 356, 35.5, 28, False),
        ('2D74', 238.5, 386, 35.5, 50.5, False),
        ('2G35', 36, 393.5, 35.5, 58, False),
        ('2G36', 36, 347, 35.5, 44.5, False),
        ('2G37', 36, 317, 35.5, 28, False),
        ('2G38', 36, 287, 35.5, 28, False),
        ('2G39', 36, 257, 35.5, 28, False),
        ('2G40', 36, 227, 35.5, 28, False),
        ('2G41', 36, 197, 35.5, 28, False),
        ('2G42', 36, 167, 35.5, 28, False),
        ('2G43', 36, 131, 53.5, 34, False),
        ('2G44', 91.5, 131, 62.5, 34, False),
        ('2G45', 111, 167, 43, 28, False),
        ('2G46', 111, 197, 43, 28, False),
        ('2G47', 111, 227, 43, 28, False),
        ('2G48', 111, 257, 43, 28, False),
        ('2G49', 111, 287, 43, 19, False),
        ('2G50', 111, 308, 43, 19, False),
        ('2G75', 73.5, 393.5, 43, 58, False),
    ]),
]

# Statut Odoo (storage.box.status) -> statut d'affichage du plan public
STATUS_TO_PLAN = {
    'disponible': 'libre',
    'occupe': 'occupe',
    'reserve': 'reserve',
    'bientot_dispo': 'bientot_libre',
}
PLAN_DEFAULT = 'hors_service'   # maintenance, nettoyage, inspection, technique

PLAN_COLORS = {
    'libre': '#28A164',
    'occupe': '#E01B0C',
    'reserve': '#F39C12',
    'bientot_libre': '#2E86C1',
    'hors_service': '#8A8F98',
}
PLAN_LABELS = {
    'libre': 'Libre',
    'occupe': 'Occup\u00e9',
    'reserve': 'R\u00e9serv\u00e9',
    'bientot_libre': 'Libre prochainement',
    'hors_service': 'Hors service',
}
PLAN_LEGEND_ORDER = ['libre', 'bientot_libre', 'occupe', 'reserve', 'hors_service']
