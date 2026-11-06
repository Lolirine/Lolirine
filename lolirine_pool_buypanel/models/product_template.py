from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_specs_techniques = fields.Html(
        string="Caractéristiques techniques",
        translate=True,
        sanitize=False,
    )
    x_contenu_colis = fields.Html(
        string="Contenu du colis et compatibilités",
        translate=True,
        sanitize=False,
        help="Ce qui est livré, avec quoi le produit fonctionne, accessoires conseillés (affiché sur la fiche du site).",
    )
    x_conseils = fields.Html(
        string="Conseils d'installation et d'entretien",
        translate=True,
        sanitize=False,
        help="Pose, mise en service, entretien, hivernage, erreurs à éviter (affiché sur la fiche du site).",
    )
    x_faq = fields.Html(
        string="Questions fréquentes",
        translate=True,
        sanitize=False,
        help="Questions-réponses, une balise <details><summary>question</summary><p>réponse</p></details> par question.",
    )
