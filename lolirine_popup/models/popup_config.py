# -*- coding: utf-8 -*-

from odoo import models, fields, api


class LolirinePopupConfig(models.Model):
    _name = 'lolirine.popup.config'
    _description = 'Configuration du Popup Lolirine'
    _rec_name = 'title'
    _order = 'sequence, id'

    active = fields.Boolean(string='Actif', default=True)
    sequence = fields.Integer(string='Priorité', default=10,
        help="Plus le nombre est petit, plus le popup est prioritaire")
    
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
    
    # Pages où afficher - Mode de sélection
    display_mode = fields.Selection([
        ('all', 'Toutes les pages'),
        ('shop', 'Pages boutique uniquement'),
        ('product', 'Pages produits uniquement'),
        ('categories', 'Catégories de produits spécifiques'),
        ('pages', 'Pages spécifiques'),
        ('urls', 'URLs personnalisées'),
    ], string='Afficher sur', default='shop')
    
    # Sélection de pages spécifiques (Many2many)
    page_ids = fields.Many2many(
        'website.page',
        'lolirine_popup_page_rel',
        'popup_id',
        'page_id',
        string='Pages sélectionnées',
        help="Sélectionnez les pages sur lesquelles afficher ce popup"
    )
    
    # Sélection de catégories de produits (Many2many)
    category_ids = fields.Many2many(
        'product.public.category',
        'lolirine_popup_category_rel',
        'popup_id',
        'category_id',
        string='Catégories de produits',
        help="Sélectionnez les catégories de produits sur lesquelles afficher ce popup"
    )
    
    # URLs personnalisées (ancien système conservé pour flexibilité)
    specific_urls = fields.Text(string='URLs personnalisées',
        help='Une URL par ligne (ex: /shop, /custom-page)')
    
    # Style
    background_image = fields.Binary(string='Image de fond')
    background_color = fields.Char(string='Couleur de fond', default='#C91E18')
    text_color = fields.Char(string='Couleur du texte', default='#ffffff')
    
    # Statistiques
    view_count = fields.Integer(string='Nombre d\'affichages', default=0, readonly=True)
    click_count = fields.Integer(string='Nombre de clics', default=0, readonly=True)
    
    # Champs calculés pour l'affichage
    page_count = fields.Integer(string='Nb pages', compute='_compute_page_count')
    category_count = fields.Integer(string='Nb catégories', compute='_compute_category_count')
    
    @api.depends('page_ids')
    def _compute_page_count(self):
        for record in self:
            record.page_count = len(record.page_ids)
    
    @api.depends('category_ids')
    def _compute_category_count(self):
        for record in self:
            record.category_count = len(record.category_ids)

    def action_activate(self):
        """Active ce popup"""
        self.write({'active': True})
    
    def action_deactivate(self):
        """Désactive ce popup"""
        self.write({'active': False})
    
    def action_duplicate(self):
        """Duplique ce popup"""
        self.ensure_one()
        return self.copy({'title': f"{self.title} (copie)", 'active': False})
    
    def action_reset_stats(self):
        """Remet les statistiques à zéro"""
        self.write({'view_count': 0, 'click_count': 0})

    @api.model
    def get_active_popup(self):
        """Retourne le popup actif le plus prioritaire"""
        popup = self.search([('active', '=', True)], order='sequence, id', limit=1)
        if popup:
            # Construire la liste des URLs selon le mode
            urls_list = []
            if popup.display_mode == 'pages' and popup.page_ids:
                urls_list = [p.url for p in popup.page_ids if p.url]
            elif popup.display_mode == 'categories' and popup.category_ids:
                # URLs des catégories
                for cat in popup.category_ids:
                    urls_list.append(f'/shop/category/{cat.id}')
                    # Ajouter aussi le slug si disponible
                    if hasattr(cat, 'website_slug') and cat.website_slug:
                        urls_list.append(f'/shop/category/{cat.website_slug}')
            elif popup.display_mode == 'urls' and popup.specific_urls:
                urls_list = [u.strip() for u in popup.specific_urls.split('\n') if u.strip()]
            
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
                'specific_urls': urls_list,
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
