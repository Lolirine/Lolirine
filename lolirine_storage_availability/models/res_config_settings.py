# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Activation globale du bouton rendez-vous
    storage_enable_appointment_button = fields.Boolean(
        string="Activer le bouton rendez-vous",
        config_parameter='lolirine_storage.enable_appointment_button',
        help="Affiche un bouton 'Contactez-nous' sur les box de stockage disponibles"
    )

    # Type de rendez-vous par défaut
    storage_default_appointment_type_id = fields.Many2one(
        'appointment.type',
        string="Type de rendez-vous par défaut",
        help="Type de rendez-vous utilisé pour les box de stockage"
    )

    # Texte du bouton par défaut
    storage_appointment_button_text = fields.Char(
        string="Texte du bouton",
        config_parameter='lolirine_storage.appointment_button_text',
        default="Contactez-nous",
        help="Texte affiché sur le bouton de rendez-vous"
    )

    # Afficher le statut sur le e-commerce
    storage_show_status_badge = fields.Boolean(
        string="Afficher le badge de statut",
        config_parameter='lolirine_storage.show_status_badge',
        help="Affiche un badge avec le statut du box sur la page produit"
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        config = self.env['ir.config_parameter'].sudo()
        
        # Récupérer l'ID du type de rendez-vous
        appointment_type_id = config.get_param('lolirine_storage.default_appointment_type_id', False)
        if appointment_type_id:
            res['storage_default_appointment_type_id'] = int(appointment_type_id)
        
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        config = self.env['ir.config_parameter'].sudo()
        
        # Sauvegarder l'ID du type de rendez-vous
        config.set_param(
            'lolirine_storage.default_appointment_type_id',
            self.storage_default_appointment_type_id.id if self.storage_default_appointment_type_id else False
        )
