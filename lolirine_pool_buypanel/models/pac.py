"""Caractéristiques « calculateur » des pompes à chaleur (Pool Store).

Le calculateur piscine lit la puissance et la plage de volume dans le nom des
déclinaisons (« 13,5 kW (30-50 m³) »). Beaucoup de gammes nomment leurs
déclinaisons par un code fabricant (Zodiac « MD5 », AquaForte « MS140 »,
AstralPool « ECO ELYO-09 ») : ces champs portent alors la donnée fabricant,
sans toucher aux variantes. Ils sont prioritaires sur le nom.
"""
from odoo import fields, models


class ProductProductPac(models.Model):
    _inherit = 'product.product'

    x_lp_puissance_kw = fields.Float(
        string='Puissance de chauffe (kW)', digits=(6, 2),
        help="Puissance restituée (air 26 °C / eau 26 °C), utilisée par le calculateur piscine.")
    x_lp_volume_min = fields.Float(string='Volume conseillé min. (m³)', digits=(8, 1))
    x_lp_volume_max = fields.Float(string='Volume conseillé max. (m³)', digits=(8, 1))
    x_lp_triphase = fields.Boolean(string='Triphasé (400 V)')
