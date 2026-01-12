# -*- coding: utf-8 -*-

from odoo import models, fields, api


class LolirinePopupConfig(models.Model):
    _name = 'lolirine.popup.config'
    _description = 'Configuration du Popup Lolirine'
    _rec_name = 'title'

    active = fields.Boolean(string='Actif', default=True)
    
    # Type de popup
    popup_type = fields.Selection([
        ('standard', 'Standard (message simple)'),
        ('available_boxes', 'Boxes disponibles'),
    ], string='Type de popup', default='standard', required=True,
        help="Standard: message avec bouton. Boxes disponibles: liste des boxes libres.")
    
    # Contenu
    title = fields.Char(string='Titre', required=True, default='Box Disponible')
    subtitle = fields.Text(string='Sous-titre / Message', 
        default='Nous vous invitons à vous diriger vers notre formulaire d\'enregistrement pour introduire vos informations de réservation.')
    
    # Bouton principal (pour popup standard)
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
    
    # Configuration popup boxes disponibles
    max_boxes_display = fields.Integer(string='Nombre max de boxes à afficher', default=5,
        help="Nombre maximum de boxes disponibles à afficher dans le popup")
    boxes_button_text = fields.Char(string='Texte bouton box', default='Réserver',
        help="Texte du bouton affiché pour chaque box")
    boxes_contact_url = fields.Char(string='URL de contact pour les boxes', 
        default='/contact-garde-meubles',
        help="URL vers laquelle rediriger avec les infos du box")
    show_box_price = fields.Boolean(string='Afficher le prix', default=True)
    show_box_size = fields.Boolean(string='Afficher la taille', default=True)
    
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
            result = {
                'id': popup.id,
                'popup_type': popup.popup_type,
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
                # Config boxes disponibles
                'max_boxes_display': popup.max_boxes_display,
                'boxes_button_text': popup.boxes_button_text,
                'boxes_contact_url': popup.boxes_contact_url,
                'show_box_price': popup.show_box_price,
                'show_box_size': popup.show_box_size,
            }
            return result
        return None

    @api.model
    def get_available_boxes(self, limit=5):
        """Retourne la liste des boxes disponibles"""
        ProductTemplate = self.env['product.template'].sudo()
        
        boxes = ProductTemplate.search([
            ('is_storage_box', '=', True),
            ('storage_status', '=', 'available'),
            ('website_published', '=', True),
        ], limit=limit, order='list_price asc')
        
        result = []
        for box in boxes:
            result.append({
                'id': box.id,
                'name': box.name,
                'price': box.list_price,
                'currency': box.currency_id.symbol or '€',
                'image_url': '/web/image/product.template/%s/image_128' % box.id,
                'url': '/shop/product/%s' % box.id,
            })
        
        return result

    def increment_view(self):
        """Incrémente le compteur d'affichages"""
        for record in self:
            record.sudo().write({'view_count': record.view_count + 1})

    def increment_click(self):
        """Incrémente le compteur de clics"""
        for record in self:
            record.sudo().write({'click_count': record.click_count + 1})
