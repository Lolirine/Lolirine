from odoo import fields, models

P = 'lolirine_pool_returns.'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lpr_delai_retractation = fields.Integer(
        string='Délai de rétractation (jours)', default=14, config_parameter=P + 'delai_retractation')
    lpr_delai_pro = fields.Integer(
        string='Délai de retour commercial pro (jours)', default=30, config_parameter=P + 'delai_pro')
    lpr_frais_pro = fields.Float(
        string='Frais de remise en stock pro (%)', default=15.0, config_parameter=P + 'frais_pro')
    lpr_delai_dommage = fields.Integer(
        string='Signalement colis abîmé (jours ouvrables)', default=3, config_parameter=P + 'delai_dommage')
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
