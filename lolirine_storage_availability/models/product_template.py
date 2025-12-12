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

    show_general_inquiry_button = fields.Boolean(
        string="Afficher bouton demande générale",
        compute='_compute_show_general_inquiry_button',
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

    general_inquiry_url = fields.Char(
        string="URL demande générale",
        compute='_compute_general_inquiry_url',
        store=False
    )

    general_inquiry_button_label = fields.Char(
        string="Label bouton demande générale",
        compute='_compute_general_inquiry_button_label',
        store=False
    )

    storage_status_display = fields.Char(
        string="Statut affiché",
        compute='_compute_storage_status_display',
        store=False
    )

    @api.depends('is_storage_box', 'storage_status', 'storage_appointment_override')
    def _compute_show_appointment_button(self):
        """Calcule si le bouton rendez-vous doit être affiché (box disponible)"""
        config = self.env['ir.config_parameter'].sudo()
        global_enabled = config.get_param('lolirine_storage.enable_appointment_button', 'False') == 'True'

        for product in self:
            show = False
            if product.is_storage_box and product.storage_status == 'available':
                if product.storage_appointment_override == 'show':
                    show = True
                elif product.storage_appointment_override == 'hide':
                    show = False
                else:  # 'default'
                    show = global_enabled
            product.show_appointment_button = show

    @api.depends('is_storage_box', 'storage_status')
    def _compute_show_general_inquiry_button(self):
        """Calcule si le bouton demande générale doit être affiché (box non disponible)"""
        for product in self:
            show = False
            if product.is_storage_box and product.storage_status != 'available':
                show = True
            product.show_general_inquiry_button = show

    @api.depends('storage_appointment_type_id')
    def _compute_appointment_url(self):
        """Calcule l'URL de rendez-vous"""
        config = self.env['ir.config_parameter'].sudo()
        global_appointment_id = config.get_param('lolirine_storage.default_appointment_type_id', False)

        for product in self:
            appointment_type = product.storage_appointment_type_id
            if not appointment_type and global_appointment_id:
                try:
                    appointment_type = self.env['appointment.type'].browse(int(global_appointment_id))
                except (ValueError, TypeError):
                    appointment_type = False
            
            if appointment_type:
                product.appointment_url = '/appointment/%s' % appointment_type.id
            else:
                product.appointment_url = '/appointment'

    @api.depends('storage_button_text')
    def _compute_appointment_button_label(self):
        """Calcule le label du bouton rendez-vous"""
        config = self.env['ir.config_parameter'].sudo()
        global_text = config.get_param('lolirine_storage.appointment_button_text', 'Contactez-nous')

        for product in self:
            product.appointment_button_label = product.storage_button_text or global_text or 'Contactez-nous'

    @api.depends('is_storage_box')
    def _compute_general_inquiry_url(self):
        """Calcule l'URL pour la demande générale"""
        config = self.env['ir.config_parameter'].sudo()
        contact_url = config.get_param('lolirine_storage.general_inquiry_url', '/contactus')

        for product in self:
            product.general_inquiry_url = contact_url

    @api.depends('is_storage_box')
    def _compute_general_inquiry_button_label(self):
        """Calcule le label du bouton demande générale"""
        config = self.env['ir.config_parameter'].sudo()
        global_text = config.get_param('lolirine_storage.general_inquiry_button_text', 'Demande générale')

        for product in self:
            product.general_inquiry_button_label = global_text or 'Demande générale'

    @api.depends('storage_status')
    def _compute_storage_status_display(self):
        """Retourne le texte du statut pour affichage"""
        status_labels = {
            'available': 'Disponible',
            'rented': 'Loué',
            'reserved': 'Réservé',
            'maintenance': 'En maintenance',
        }
        for product in self:
            product.storage_status_display = status_labels.get(product.storage_status, '')

    def action_view_appointments(self):
        """Ouvre la vue des rendez-vous liés à ce produit/box"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rendez-vous',
            'res_model': 'appointment.type',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_set_available(self):
        """Marque le box comme disponible"""
        self.filtered('is_storage_box').write({'storage_status': 'available'})

    def action_set_rented(self):
        """Marque le box comme loué"""
        self.filtered('is_storage_box').write({'storage_status': 'rented'})

    def action_set_reserved(self):
        """Marque le box comme réservé"""
        self.filtered('is_storage_box').write({'storage_status': 'reserved'})

    def action_set_maintenance(self):
        """Marque le box en maintenance"""
        self.filtered('is_storage_box').write({'storage_status': 'maintenance'})

    def action_convert_to_storage_box(self):
        """Convertit le produit en box de stockage"""
        self.write({'is_storage_box': True, 'storage_status': 'available'})
