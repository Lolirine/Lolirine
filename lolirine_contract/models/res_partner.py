from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    id_card_recto = fields.Binary(
        string="Carte d'identite (Recto)",
        attachment=True,
        help="Photo recto de la carte d'identite du client"
    )
    id_card_recto_filename = fields.Char(string="Nom fichier recto")
    
    id_card_verso = fields.Binary(
        string="Carte d'identite (Verso)",
        attachment=True,
        help="Photo verso de la carte d'identite du client"
    )
    id_card_verso_filename = fields.Char(string="Nom fichier verso")
    
    id_card_uploaded = fields.Boolean(
        string="Carte d'identite fournie",
        compute="_compute_id_card_uploaded",
        store=True
    )

    @api.depends("id_card_recto", "id_card_verso")
    def _compute_id_card_uploaded(self):
        for partner in self:
            partner.id_card_uploaded = bool(partner.id_card_recto and partner.id_card_verso)
