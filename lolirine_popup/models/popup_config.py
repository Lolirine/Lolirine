# -*- coding: utf-8 -*-

from odoo import models, fields, api


class LolirinePopupConfig(models.Model):
    _name = 'lolirine.popup.config'
    _description = 'Configuration du Popup Lolirine'
    _rec_name = 'title'

    active = fields.Boolean(string='Actif', default=True)
    
    # Contenu
    title = fields.Char(string='Titre', required=True, default='Box Disponible')
    subtitle = fields.Text(string='Sous-titre / Message', 
        default='Nous vous invitons à vous diriger vers notre formulaire d\'enregistrement pour introduire vos informations de réservation.')
    
    # Bouton principal
    button_text = fields.Char(string='Texte du bouton', default='Nouveau client / Vers le Formulaire')
    button_url = fields.Char(string='URL du bouton', default='/contact-garde-meubles',
        help='URL de redirection quand on clique sur le bouton')
    button_target = fields.Selection([
        ('_self', 'Même fenêtre'),
        ('_blank', 'Nouvelle fenêtre'),
    ], string='Ouvrir dans', default='_self')
    
    # Bouton secondaire (optionnel)
    show_secondary_button = fields.Boolean(string='Afficher bouton secondaire', default=False)
    secondary_button_text = fields.Char(string='Texte bouton secondaire', default='En savoir plus')
    secondary_button_url = fields.Char(string='URL bouton secondaire', default='/nos-tarifs')
    
    # Paramètres d'affichage
    show_delay = fields.Integer(string='Délai avant affichage (secondes)', default=3,
        help='Nombre de secondes avant que le popup apparaisse')
    hide_duration = fields.Integer(string='Masquer pendant (jours)', default=7,
        help='Nombre de jours pendant lesquels le popup reste masqué après fermeture')
    
    # Pages où afficher
    display_mode = fields.Selection([
        ('all', 'Toutes les pages'),
        ('shop', 'Pages boutique uniquement'),
        ('product', 'Pages produits uniquement'),
        ('specific', 'Pages spécifiques'),
    ], string='Afficher sur', default='shop')
    specific_urls = fields.Text(string='URLs spécifiques',
        help='Une URL par ligne (ex: /shop, /shop/category/boxes)')
    
    # Style
    background_image = fields.Binary(string='Image de fond')
    background_color = fields.Char(string='Couleur de fond', default='#C91E18')
    text_color = fields.Char(string='Couleur du texte', default='#ffffff')
    
    # Statistiques
    view_count = fields.Integer(string='Nombre d\'affichages', default=0, readonly=True)
    click_count = fields.Integer(string='Nombre de clics', default=0, readonly=True)

    @api.model
    def get_active_popup(self):
        """Retourne le popup actif"""
        popup = self.search([('active', '=', True)], limit=1)
        if popup:
            return {
                'id': popup.id,
                'title': popup.title,
                'subtitle': popup.subtitle,
                'button_text': popup.button_text,
                'button_url': popup.button_url,
                'button_target': popup.button_target,
                'show_secondary_button': popup.show_secondary_button,
                'secondary_button_text': popup.secondary_button_text,
                'secondary_button_url': popup.secondary_button_url,
                'show_delay': popup.show_delay * 1000,  # Convertir en millisecondes
                'hide_duration': popup.hide_duration,
                'display_mode': popup.display_mode,
                'specific_urls': popup.specific_urls.split('\n') if popup.specific_urls else [],
                'background_color': popup.background_color or '#C91E18',
                'text_color': popup.text_color or '#ffffff',
            }
        return None

    def increment_view(self):
        """Incrémente le compteur d'affichages"""
        for record in self:
            record.sudo().write({'view_count': record.view_count + 1})

    def increment_click(self):
        """Incrémente le compteur de clics"""
        for record in self:
            record.sudo().write({'click_count': record.click_count + 1})
