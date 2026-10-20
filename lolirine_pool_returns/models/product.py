from odoo import api, fields, models


class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    x_non_retournable = fields.Boolean(
        string='Exclue de la rétractation',
        help="Les produits de cette catégorie et de ses sous-catégories ne peuvent pas être "
             "retournés au titre du droit de rétractation (ex. articles sur mesure). "
             "Les pannes et colis abîmés restent pris en charge.")
    x_motif_non_retour = fields.Char(
        string='Motif affiché', default='Article fabriqué sur mesure',
        help="Phrase affichée au client pour expliquer l'exclusion.")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_non_retournable = fields.Selection([
        ('auto', 'Selon la catégorie'),
        ('oui', 'Exclu de la rétractation'),
        ('non', 'Retournable'),
    ], string='Rétractation', default='auto', required=True,
        help="« Selon la catégorie » : exclu si une de ses catégories du site est marquée "
             "« Exclue de la rétractation ».")
    x_motif_non_retour = fields.Char(string='Motif de non-retour')

    def _lolirine_exclu_retractation(self):
        """Retourne (exclu: bool, motif: str) pour le droit de rétractation."""
        self.ensure_one()
        if self.x_non_retournable == 'oui':
            return True, self.x_motif_non_retour or 'Article exclu de la rétractation'
        if self.x_non_retournable == 'non':
            return False, ''
        for categ in self.public_categ_ids:
            c = categ
            while c:
                if c.x_non_retournable:
                    return True, c.x_motif_non_retour or 'Article fabriqué sur mesure'
                c = c.parent_id
        return False, ''
