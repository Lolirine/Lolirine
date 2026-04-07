from odoo import models, fields, api


class LolirineWishlistConfig(models.Model):
    """
    Singleton de configuration visuelle de la wishlist Pool Store.
    Permet de modifier couleurs et textes depuis le backend
    sans toucher au code.
    """
    _name = 'lolirine.wishlist.config'
    _description = 'Configuration Wishlist Lolirine Pool'
    _rec_name = 'id'

    # ── Couleurs ─────────────────────────────────────────────
    color_primary = fields.Char(
        string='Couleur principale (boutons, accents)',
        default='#1a5fb4',
    )
    color_primary_hover = fields.Char(
        string='Couleur principale au survol',
        default='#1e4d99',
    )
    color_card_bg = fields.Char(
        string='Fond des cartes produit',
        default='#ffffff',
    )
    color_card_border = fields.Char(
        string='Bordure des cartes',
        default='#e5e7eb',
    )
    color_card_border_hover = fields.Char(
        string='Bordure des cartes au survol',
        default='#93c5fd',
    )
    color_summary_bg = fields.Char(
        string='Fond du récapitulatif',
        default='#ffffff',
    )
    color_page_bg = fields.Char(
        string='Fond de la page',
        default='transparent',
    )
    color_stock_green = fields.Char(
        string='Couleur stock disponible',
        default='#22c55e',
    )
    color_stock_orange = fields.Char(
        string='Couleur stock limité',
        default='#f59e0b',
    )

    # ── Textes ───────────────────────────────────────────────
    text_page_title = fields.Char(
        string='Titre de la page',
        default='Ma liste de souhaits',
    )
    text_add_to_cart = fields.Char(
        string='Bouton "Ajouter au panier"',
        default='Ajouter au panier',
    )
    text_in_stock = fields.Char(
        string='Texte "En stock"',
        default='En stock',
    )
    text_low_stock = fields.Char(
        string='Texte "Stock limité"',
        default='Stock limité',
    )
    text_out_of_stock = fields.Char(
        string='Texte "Rupture de stock"',
        default='Sur commande',
    )
    text_add_all = fields.Char(
        string='Bouton "Tout ajouter"',
        default='Tout ajouter au panier',
    )
    text_share = fields.Char(
        string='Bouton "Partager"',
        default='Partager la liste',
    )
    text_shipping_note = fields.Char(
        string='Note livraison (récapitulatif)',
        default='Livraison offerte dès 499 € HT · Retours 30 jours',
    )
    text_expert_phone = fields.Char(
        string='Téléphone expert piscine',
        default='+32 497 44 41 46',
    )
    text_contact_label = fields.Char(
        string='Label bouton contact',
        default='Contacter nos experts',
    )

    @api.model
    def get_config(self):
        """Retourne (et crée si besoin) l'enregistrement singleton."""
        config = self.search([], limit=1)
        if not config:
            config = self.create({})
        return config

    @api.model
    def get_css_vars(self):
        """Génère les variables CSS à injecter dans la page."""
        cfg = self.get_config()
        return f"""
:root {{
    --lw-primary:           {cfg.color_primary};
    --lw-primary-hover:     {cfg.color_primary_hover};
    --lw-card-bg:           {cfg.color_card_bg};
    --lw-card-border:       {cfg.color_card_border};
    --lw-card-border-hover: {cfg.color_card_border_hover};
    --lw-summary-bg:        {cfg.color_summary_bg};
    --lw-page-bg:           {cfg.color_page_bg};
    --lw-stock-green:       {cfg.color_stock_green};
    --lw-stock-orange:      {cfg.color_stock_orange};
}}
"""

    @api.model
    def get_texts(self):
        """Retourne les textes configurables sous forme de dict."""
        cfg = self.get_config()
        return {
            'page_title':    cfg.text_page_title,
            'add_to_cart':   cfg.text_add_to_cart,
            'in_stock':      cfg.text_in_stock,
            'low_stock':     cfg.text_low_stock,
            'out_of_stock':  cfg.text_out_of_stock,
            'add_all':       cfg.text_add_all,
            'share':         cfg.text_share,
            'shipping_note': cfg.text_shipping_note,
            'expert_phone':  cfg.text_expert_phone,
            'contact_label': cfg.text_contact_label,
        }
