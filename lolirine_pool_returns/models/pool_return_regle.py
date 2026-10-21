from odoo import api, fields, models


class PoolReturnRegle(models.Model):
    """Conditions de reprise d'un fournisseur (dropshipping) : délais, frais, contacts RMA."""
    _name = 'pool.return.regle'
    _description = 'Conditions de retour par fournisseur'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Libellé', required=True)
    partner_id = fields.Many2one('res.partner', string='Fournisseur', required=True,
                                 domain=[('is_company', '=', True)])
    delai_reprise = fields.Integer(
        string='Reprise sans frais (jours)', default=8,
        help="Nombre de jours après la réception pendant lesquels le fournisseur reprend le matériel neuf "
             "sans retenue (SCP : 8 ; Fluidra : 14).")
    delai_reprise_max = fields.Integer(
        string='Reprise maximale (jours)', default=8,
        help="Au-delà, le fournisseur ne reprend plus (Fluidra : 2 mois, avec retenue).")
    frais_apres_pct = fields.Float(
        string='Retenue après le délai sans frais (%)', default=0.0,
        help="Fluidra : 10 % de la facture d'origine au-delà de 2 semaines.")
    delai_dommage_heures = fields.Integer(
        string='Signalement d\'un dommage (heures)', default=48,
        help="Délai imposé par le fournisseur pour signaler un dommage ou un vice apparent "
             "(SCP : 48 h au transporteur ; Fluidra : 24 h).")
    garantie_mois = fields.Integer(
        string='Garantie fabricant / fournisseur (mois)', default=24,
        help="Durée pendant laquelle le fournisseur prend en charge un défaut (appareils : 2 ans en général). "
             "Le consommateur a de toute façon 2 ans de garantie légale chez Lolirine : au-delà de cette durée, "
             "le défaut reste à charge de Lolirine sans recours.")
    email_rma_neuf = fields.Char(string='E-mail retour de matériel neuf')
    email_rma_sav = fields.Char(string='E-mail SAV / garantie')
    adresse_retour = fields.Text(string='Adresse de retour',
                                 help="Adresse où le client renvoie directement l'article après accord (RMA).")
    note = fields.Text(string='Rappels (CGV du fournisseur)')
    active = fields.Boolean(default=True)

    @api.model
    def pour(self, partner):
        """Règle applicable au fournisseur (ou à sa société mère), sinon vide."""
        if not partner:
            return self.browse()
        commercial = partner.commercial_partner_id
        return self.search([('partner_id', 'in', (partner | commercial).ids)], limit=1)
