# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


# Remises accordees par SCP selon la lettre tarifaire du catalogue.
# Le coefficient est ce qui reste a payer : 1 - remise.
REMISES_SCP = {
    'A': 0.525,
    'B': 0.335,
    'C': 0.430,
    'D': 0.380,
    'E': 0.250,
    'F': 0.300,
    'P': 0.500,
}

COEF_ACHAT = dict((k, round(1.0 - v, 4)) for k, v in REMISES_SCP.items())

LIBELLES = [
    ('A', 'A — remise 52,5 %'),
    ('B', 'B — remise 33,5 %'),
    ('C', 'C — remise 43 %'),
    ('D', 'D — remise 38 %'),
    ('E', 'E — remise 25 %'),
    ('F', 'F — remise 30 %'),
    ('P', 'P — remise 50 %'),
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_lettre_scp = fields.Selection(
        LIBELLES,
        string="Lettre tarifaire SCP",
        help="Lettre figurant en face du prix dans le catalogue SCP. "
             "Elle determine la remise consentie par le fournisseur.",
        tracking=True,
    )
    x_prix_catalogue = fields.Float(
        string="Prix catalogue SCP",
        digits='Product Price',
        help="Prix HT affiche dans le catalogue SCP, avant remise.",
        tracking=True,
    )
    x_coef_vente = fields.Float(
        string="Coefficient de vente",
        digits=(12, 4),
        default=0.95,
        help="Part du prix catalogue retenue comme prix de vente. "
             "0,95 par defaut. Descendre a 0,85 pour une promotion de 15 % "
             "sur le tarif catalogue.",
        tracking=True,
    )

    x_remise_scp = fields.Float(
        string="Remise SCP",
        compute='_compute_tarification_scp',
        store=True,
        digits=(12, 4),
        help="Remise correspondant a la lettre, en pourcentage.",
    )
    x_cout_calcule = fields.Float(
        string="Coût calculé",
        compute='_compute_tarification_scp',
        store=True,
        digits='Product Price',
        help="Prix catalogue diminue de la remise de la lettre.",
    )
    x_pv_calcule = fields.Float(
        string="Prix de vente calculé",
        compute='_compute_tarification_scp',
        store=True,
        digits='Product Price',
        help="Prix catalogue multiplie par le coefficient de vente.",
    )
    x_marge_eur = fields.Float(
        string="Marge calculée",
        compute='_compute_tarification_scp',
        store=True,
        digits='Product Price',
    )
    x_marge_pct = fields.Float(
        string="Marge calculée (%)",
        compute='_compute_tarification_scp',
        store=True,
        digits=(12, 1),
    )
    x_ecart_prix = fields.Float(
        string="Écart avec le prix de vente",
        compute='_compute_ecart',
        digits='Product Price',
        help="Difference entre le prix de vente calcule et le prix de vente "
             "reellement enregistre sur la fiche.",
    )
    x_marge_reelle_pct = fields.Float(
        string="Marge réelle (%)",
        compute='_compute_ecart',
        digits=(12, 1),
        help="Marge sur les valeurs effectivement enregistrees, prix de vente "
             "et cout, independamment du calcul SCP.",
    )

    @api.depends('x_lettre_scp', 'x_prix_catalogue', 'x_coef_vente')
    def _compute_tarification_scp(self):
        for rec in self:
            remise = REMISES_SCP.get(rec.x_lettre_scp, 0.0)
            coef_achat = COEF_ACHAT.get(rec.x_lettre_scp, 0.0)
            catalogue = rec.x_prix_catalogue or 0.0
            coef_vente = rec.x_coef_vente or 0.0
            rec.x_remise_scp = remise * 100.0
            if not rec.x_lettre_scp or not catalogue:
                rec.x_cout_calcule = 0.0
                rec.x_pv_calcule = 0.0
                rec.x_marge_eur = 0.0
                rec.x_marge_pct = 0.0
                continue
            cout = round(catalogue * coef_achat, 2)
            pv = round(catalogue * coef_vente, 2)
            rec.x_cout_calcule = cout
            rec.x_pv_calcule = pv
            rec.x_marge_eur = round(pv - cout, 2)
            rec.x_marge_pct = round((pv - cout) / pv * 100.0, 1) if pv else 0.0

    @api.depends('x_pv_calcule', 'list_price', 'standard_price')
    def _compute_ecart(self):
        for rec in self:
            rec.x_ecart_prix = round((rec.list_price or 0.0)
                                     - (rec.x_pv_calcule or 0.0), 2)
            pv, cout = rec.list_price or 0.0, rec.standard_price or 0.0
            rec.x_marge_reelle_pct = round((pv - cout) / pv * 100.0, 1) if pv else 0.0

    @api.onchange('x_lettre_scp', 'x_prix_catalogue', 'x_coef_vente')
    def _onchange_tarification_scp(self):
        """Repercute immediatement le calcul sur le prix et le cout, dans le
        formulaire. Rien n'est enregistre tant que la fiche n'est pas sauvee."""
        for rec in self:
            if rec.x_lettre_scp and rec.x_prix_catalogue:
                coef_achat = COEF_ACHAT.get(rec.x_lettre_scp, 0.0)
                rec.standard_price = round(rec.x_prix_catalogue * coef_achat, 2)
                rec.list_price = round(rec.x_prix_catalogue
                                       * (rec.x_coef_vente or 0.0), 2)

    def action_appliquer_tarif_scp(self):
        """Ecrit le cout et le prix de vente calcules sur les fiches
        selectionnees. Utilisable en masse depuis la liste des produits."""
        applicables = self.filtered(lambda r: r.x_lettre_scp and r.x_prix_catalogue)
        if not applicables:
            raise UserError(
                "Aucune des fiches selectionnees ne porte a la fois une lettre "
                "tarifaire et un prix catalogue."
            )
        for rec in applicables:
            rec.write({
                'standard_price': rec.x_cout_calcule,
                'list_price': rec.x_pv_calcule,
            })
        ignorees = len(self) - len(applicables)
        message = "%s fiche(s) mise(s) a jour." % len(applicables)
        if ignorees:
            message += (" %s ignoree(s), faute de lettre ou de prix catalogue."
                        % ignorees)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Tarification SCP",
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_deduire_prix_catalogue(self):
        """Pour les fiches deja tarifees sans prix catalogue enregistre :
        reconstitue le prix catalogue a partir du prix de vente et du
        coefficient de vente. A n'utiliser que sur des fiches dont le prix de
        vente est juste."""
        n = 0
        for rec in self:
            if rec.x_prix_catalogue or not rec.list_price:
                continue
            coef = rec.x_coef_vente or 0.95
            if coef:
                rec.x_prix_catalogue = round(rec.list_price / coef, 2)
                n += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Tarification SCP",
                'message': "%s prix catalogue reconstitue(s)." % n,
                'type': 'success',
                'sticky': False,
            },
        }
