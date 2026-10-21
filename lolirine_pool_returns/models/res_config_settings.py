from odoo import fields, models

P = 'lolirine_pool_returns.'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lpr_delai_retractation = fields.Integer(
        string='Délai de rétractation (jours)', default=14, config_parameter=P + 'delai_retractation')
    lpr_delai_pro = fields.Integer(
        string='Délai de retour commercial pro (jours)', default=7, config_parameter=P + 'delai_pro')
    lpr_frais_pro = fields.Float(
        string='Frais de remise en stock pro (%)', default=15.0, config_parameter=P + 'frais_pro')
    lpr_garantie_mois = fields.Integer(
        string='Garantie légale (mois)', default=24, config_parameter=P + 'garantie_mois',
        help="Garantie légale de conformité due par le vendeur au consommateur dans l'Union européenne : 2 ans "
             "à compter de la livraison (biens neufs).")
    lpr_delai_dommage = fields.Integer(
        string='Signalement colis abîmé (jours ouvrables)', default=2, config_parameter=P + 'delai_dommage',
        help="SCP exige des réserves au transporteur sous 48 h et chez SCP sous 3 jours : 2 jours ouvrables "
             "laissent le temps de transmettre.")
    lpr_seuil_sans_retour = fields.Float(
        string='Remboursement sans renvoi en dessous de (€)', default=15.0,
        config_parameter=P + 'seuil_sans_retour',
        help="Pour un article défectueux, abîmé ou erroné de faible valeur : inutile de le renvoyer.")
    lpr_auto_accepter = fields.Boolean(
        string='Accepter automatiquement les rétractations dans les délais',
        default=True, config_parameter=P + 'auto_accepter')
    lpr_adresse_retour = fields.Char(
        string='Adresse de renvoi', config_parameter=P + 'adresse_retour',
        help="Une ligne par élément, séparés par « ; ». Vide = adresse de la société.")
    lpr_lien_cgv = fields.Char(
        string='Lien des conditions de retour', default='/terms', config_parameter=P + 'lien_cgv')
    lpr_delai_fournisseur = fields.Integer(
        string='Délai de reprise du fournisseur (jours)', default=8, config_parameter=P + 'delai_fournisseur',
        help="SCP reprend le matériel neuf 8 jours après réception, avec autorisation (RMA). Une rétractation "
             "demandée assez tôt peut repartir directement chez le fournisseur ; au-delà, elle revient à Boninne.")
    lpr_adresse_fournisseur = fields.Char(
        string='Adresse de retour du fournisseur', config_parameter=P + 'adresse_fournisseur',
        default='SCP Benelux ; Maalbeekweg 21 ; 1930 Zaventem ; Belgique')
    lpr_email_rma_neuf = fields.Char(
        string='E-mail RMA matériel neuf', default='info.benelux@scppool.com', config_parameter=P + 'email_rma_neuf')
    lpr_email_rma_sav = fields.Char(
        string='E-mail RMA SAV / garantie', default='technicalsupport.benelux@scppool.com',
        config_parameter=P + 'email_rma_sav')
