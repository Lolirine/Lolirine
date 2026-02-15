# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DropshipConfig(models.Model):
    _name = 'dropship.config'
    _description = 'Configuration Dropshipping'
    _rec_name = 'company_id'

    company_id = fields.Many2one(
        'res.company', string='Société', required=True,
        default=lambda self: self.env.company,
    )
    use_neutral_packaging = fields.Boolean(
        string='Emballage neutre', default=True,
        help="Demander aux fournisseurs un emballage neutre (sans leur logo/facture)",
    )
    include_delivery_note = fields.Boolean(
        string='Inclure bon de livraison', default=False,
    )
    min_margin_percent = fields.Float(
        string='Marge minimale (%)', default=15.0,
        help="Alerte si la marge descend en dessous de ce seuil",
    )
    auto_send_po = fields.Boolean(
        string='Envoi auto BC au fournisseur', default=False,
        help="Envoyer automatiquement le BC par email après confirmation",
    )
    default_delay = fields.Integer(
        string='Délai par défaut (jours)', default=5,
    )

    @api.model
    def get_config(self):
        """Retourne la config pour la société courante, ou en crée une"""
        config = self.search([('company_id', '=', self.env.company.id)], limit=1)
        if not config:
            config = self.create({'company_id': self.env.company.id})
        return config
