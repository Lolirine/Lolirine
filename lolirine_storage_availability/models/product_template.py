# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Champ pour identifier si c'est un box de stockage
    is_storage_box = fields.Boolean(
        string="Box de stockage",
        default=False,
        help="Cochez si ce produit est un box de stockage géré par contrat/abonnement"
    )

    # Statut de disponibilité du box
    storage_status = fields.Selection([
        ('available', 'Disponible'),
        ('rented', 'Loué'),
        ('reserved', 'Réservé'),
        ('maintenance', 'En maintenance'),
    ], string="Statut du box", default='available',
        help="Statut actuel du box de stockage")

    # Configuration individuelle du bouton rendez-vous
    storage_appointment_override = fields.Selection([
        ('default', 'Utiliser les paramètres globaux'),
        ('show', 'Toujours afficher le bouton'),
        ('hide', 'Ne jamais afficher le bouton'),
    ], string="Affichage bouton RDV", default='default',
        help="Surcharge l'affichage du bouton rendez-vous pour ce produit")

    # Type de rendez-vous spécifique au produit (override)
    storage_appointment_type_id = fields.Many2one(
        'appointment.type',
        string="Type de RDV spécifique",
        help="Si défini, utilise ce type de rendez-vous au lieu du type global"
    )

    # Texte personnalisé du bouton
    storage_button_text = fields.Char(
        string="Texte du bouton",
        help="Texte personnalisé du bouton (laissez vide pour utiliser le texte par défaut)"
    )

    # Champs calculés pour l'affichage e-commerce
    show_appointment_button = fields.Boolean(
        string="Afficher bouton RDV",
        compute='_compute_show_appointment_button',
        store=False
    )

    appointment_url = fields.Char(
        string="URL de rendez-vous",
        compute='_compute_appointment_url',
        store=False
    )

    appointment_button_label = fields.Char(
        string="Label du bouton",
        compute='_compute_appointment_button_label',
        store=False
    )

    @api.depends('is_storage_box', 'storage_status', 'storage_appointment_override')
    def _compute_show_appointment_button(self):
        """Calcule si le bouton rendez-vous doit être affiché"""
        # Récupérer les paramètres globaux
        config = self.env['ir.config_parameter'].sudo()
        global_enabled = config.get_param('lolirine_storage.enable_appointment_button', 'False') == 'True'

        for product in self:
            show = False
            if product.is_storage_box:
                # Vérifier l'override du produit
                if product.storage_appointment_override == 'show':
                    show = product.storage_status == 'available'
                elif product.storage_appointment_override == 'hide':
                    show = False
                else:  # 'default' - utiliser les paramètres globaux
                    show = global_enabled and product.storage_status == 'available'
            product.show_appointment_button = show

    @api.depends('storage_appointment_type_id')
    def _compute_appointment_url(self):
        """Calcule l'URL de rendez-vous"""
        config = self.env['ir.config_parameter'].sudo()
        global_appointment_id = config.get_param('lolirine_storage.default_appointment_type_id', False)

        for product in self:
            appointment_type = product.storage_appointment_type_id
            if not appointment_type and global_appointment_id:
                appointment_type = self.env['appointment.type'].browse(int(global_appointment_id))
            
            if appointment_type:
                product.appointment_url = '/appointment/%s' % appointment_type.id
            else:
                product.appointment_url = '/appointment'

    @api.depends('storage_button_text')
    def _compute_appointment_button_label(self):
        """Calcule le label du bouton"""
        config = self.env['ir.config_parameter'].sudo()
        global_text = config.get_param('lolirine_storage.appointment_button_text', 'Contactez-nous')

        for product in self:
            product.appointment_button_label = product.storage_button_text or global_text or 'Contactez-nous'
