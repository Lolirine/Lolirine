# -*- coding: utf-8 -*-
"""Marge complémentaire (majoration) sur les lignes des devis piscine et bâtiment.

Une colonne « Marge + » sur la ligne (aucune, +5 %, +10 %, +15 %) augmente le prix
unitaire à partir du prix de base (prix public / prix du tableau des ouvrages).
Le prix de base est gardé sur la ligne : changer ou retirer la majoration
recalcule le prix sans dérive. Un article peut porter une majoration par défaut,
reprise automatiquement quand on l'ajoute à un devis.
La majoration reste interne : le client ne voit que le prix unitaire final.
"""
from odoo import api, fields, models
from odoo.tools import float_compare

MAJORATIONS = [
    ('0', 'Aucune'),
    ('5', '+5 %'),
    ('10', '+10 %'),
    ('15', '+15 %'),
]


def taux_majoration(code):
    try:
        return float(code or 0) / 100.0
    except (TypeError, ValueError):
        return 0.0


class ProductTemplateMajoration(models.Model):
    _inherit = 'product.template'

    pool_majoration_defaut = fields.Selection(
        MAJORATIONS, string="Marge complémentaire par défaut", default='0',
        help="Appliquée automatiquement au prix de cet article quand il est ajouté à un devis "
             "piscine ou bâtiment (article plus cher ailleurs à l'achat). Modifiable ligne par ligne.")


class SaleOrderLineMajoration(models.Model):
    _inherit = 'sale.order.line'

    pool_majoration = fields.Selection(
        MAJORATIONS, string="Marge +", compute='_compute_pool_majoration', store=True, readonly=False,
        precompute=True,
        help="Marge complémentaire ajoutée au prix de base (prix public). Interne : le client ne voit "
             "que le prix unitaire final.")
    pool_prix_base = fields.Float(
        "Prix de base", digits='Product Price', copy=True,
        help="Prix unitaire avant marge complémentaire (prix public ou prix de l'ouvrage).")

    @api.depends('product_id')
    def _compute_pool_majoration(self):
        for line in self:
            line.pool_majoration = (line.product_id.product_tmpl_id.pool_majoration_defaut or '0') \
                if line.product_id and not line.display_type else '0'

    # ── Calcul ──────────────────────────────────────────────────────
    def _pool_arrondi(self, valeur):
        return round(valeur, self.env['decimal.precision'].precision_get('Product Price'))

    def _pool_vals_majoration(self, majoration, base=None):
        """Valeurs à écrire pour passer la ligne à `majoration` (base = prix avant marge)."""
        self.ensure_one()
        if base is None:
            base = self.pool_prix_base or self.price_unit
        prix = self._pool_arrondi(base * (1.0 + taux_majoration(majoration)))
        vals = {'pool_prix_base': base if majoration != '0' else 0.0, 'price_unit': prix}
        # Prix venant de l'article (non manuel) : il le reste, la majoration est réappliquée
        # à chaque recalcul (quantité, liste de prix…).
        if float_compare(self.technical_price_unit, self.price_unit, precision_digits=6) == 0:
            vals['technical_price_unit'] = prix
        return vals

    def _reset_price_unit(self):
        super()._reset_price_unit()
        m = self.pool_majoration
        if m and m != '0' and not self.display_type:
            base = self.price_unit
            prix = self._pool_arrondi(base * (1.0 + taux_majoration(m)))
            self.update({'pool_prix_base': base, 'price_unit': prix, 'technical_price_unit': prix})
        elif self.pool_prix_base:
            self.pool_prix_base = 0.0

    # ── Formulaire ─────────────────────────────────────────────────
    @api.onchange('pool_majoration')
    def _onchange_pool_majoration(self):
        if self.display_type:
            return
        self.update(self._pool_vals_majoration(self.pool_majoration or '0'))

    @api.onchange('price_unit')
    def _onchange_pool_prix_manuel(self):
        """Prix modifié à la main sur une ligne majorée : le nouveau prix devient la référence."""
        m = self.pool_majoration
        if not m or m == '0' or not self.pool_prix_base:
            return
        attendu = self._pool_arrondi(self.pool_prix_base * (1.0 + taux_majoration(m)))
        if float_compare(attendu, self.price_unit, precision_digits=2):
            self.pool_prix_base = self.price_unit / (1.0 + taux_majoration(m))

    # ── Écritures par le code (assistants, scripts) ────────────────
    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line, vals in zip(lines, vals_list):
            m = line.pool_majoration
            if line.display_type or not m or m == '0' or line.pool_prix_base:
                continue
            if 'price_unit' in vals:
                # prix imposé à la création (ouvrage, fourniture…) : la majoration de l'article s'y ajoute
                line.write(line._pool_vals_majoration(m, base=line.price_unit))
            else:
                # prix calculé depuis l'article, déjà majoré : garder le prix de base
                line.with_context(pool_majoration_en_cours=True).pool_prix_base = \
                    line.price_unit / (1.0 + taux_majoration(m))
        return lines

    def write(self, vals):
        if 'pool_majoration' in vals and 'price_unit' not in vals and not self.env.context.get('pool_majoration_en_cours'):
            res = True
            for line in self:
                if line.display_type:
                    res = super(SaleOrderLineMajoration, line).write(vals) and res
                    continue
                base = line.pool_prix_base or line.price_unit
                autres = dict(vals)
                res = super(SaleOrderLineMajoration, line.with_context(pool_majoration_en_cours=True)).write(autres) and res
                line.with_context(pool_majoration_en_cours=True).write(
                    line._pool_vals_majoration(vals['pool_majoration'] or '0', base=base))
            return res
        return super().write(vals)


class SaleOrderMajoration(models.Model):
    _inherit = 'sale.order'

    pool_majoration_montant = fields.Monetary(
        "Marge complémentaire", compute='_compute_pool_majoration_montant',
        help="Supplément HT obtenu par les majorations +5 / +10 / +15 % des lignes.")

    @api.depends('order_line.price_unit', 'order_line.pool_prix_base', 'order_line.pool_majoration',
                 'order_line.product_uom_qty', 'order_line.discount')
    def _compute_pool_majoration_montant(self):
        for o in self:
            total = 0.0
            for l in o.order_line:
                if l.display_type or not l.pool_prix_base or not l.pool_majoration or l.pool_majoration == '0':
                    continue
                total += (l.price_unit - l.pool_prix_base) * l.product_uom_qty * (1 - (l.discount or 0.0) / 100.0)
            o.pool_majoration_montant = total
