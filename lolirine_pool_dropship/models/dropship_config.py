# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DropshipConfig(models.Model):
    """Configuration globale du module dropshipping"""
    _name = 'dropship.config'
    _description = 'Configuration Dropshipping'
    _rec_name = 'name'

    name = fields.Char(string='Nom', required=True, default='Configuration principale')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Société', 
                                  default=lambda self: self.env.company)
    
    # === CRITÈRES DE SÉLECTION ===
    selection_priority = fields.Selection([
        ('margin', 'Marge la plus élevée'),
        ('delay', 'Délai le plus court'),
        ('reliability', 'Fiabilité fournisseur'),
        ('priority', 'Fournisseur prioritaire'),
    ], string='Critère principal', default='margin', required=True)
    
    # Pondérations des critères (sur 100)
    weight_margin = fields.Integer(string='Poids Marge (%)', default=40)
    weight_delay = fields.Integer(string='Poids Délai (%)', default=25)
    weight_reliability = fields.Integer(string='Poids Fiabilité (%)', default=20)
    weight_shipping = fields.Integer(string='Poids Frais livraison (%)', default=15)
    
    # === RÈGLES DE MARGE ===
    min_margin_percent = fields.Float(string='Marge minimum (%)', default=15.0,
                                       help="Marge minimum requise pour valider une commande")
    target_margin_percent = fields.Float(string='Marge cible (%)', default=25.0)
    
    # Bonus/Malus
    bonus_fast_delivery = fields.Float(string='Bonus délai rapide (%)', default=5.0,
                                        help="Bonus si délai < délai moyen")
    bonus_priority_supplier = fields.Float(string='Bonus fournisseur prioritaire (%)', default=3.0)
    malus_low_reliability = fields.Float(string='Malus faible fiabilité (%)', default=5.0,
                                          help="Malus si score fiabilité < 70%")
    
    # === AUTOMATISATION ===
    auto_select_supplier = fields.Boolean(string='Sélection automatique', default=True,
                                          help="Sélectionner automatiquement le meilleur fournisseur")
    auto_create_po = fields.Boolean(string='Création auto BC fournisseur', default=True,
                                    help="Créer automatiquement la commande fournisseur")
    auto_send_po = fields.Boolean(string='Envoi auto BC fournisseur', default=False,
                                  help="Envoyer automatiquement le BC au fournisseur")
    
    # === NOTIFICATIONS ===
    notify_low_margin = fields.Boolean(string='Alerte marge basse', default=True)
    notify_no_supplier = fields.Boolean(string='Alerte aucun fournisseur', default=True)
    notification_user_ids = fields.Many2many('res.users', string='Utilisateurs à notifier')
    
    # === DROPSHIPPING ===
    use_neutral_packaging = fields.Boolean(string='Emballage neutre', default=True,
                                           help="Demander un emballage neutre aux fournisseurs")
    include_packing_slip = fields.Boolean(string='Inclure bon de livraison', default=False)
    default_shipping_instructions = fields.Text(string='Instructions expédition par défaut')
    
    # === RÈGLES DE MARGE SPÉCIFIQUES ===
    margin_rule_ids = fields.One2many('dropship.margin.rule', 'config_id', string='Règles de marge')

    @api.constrains('weight_margin', 'weight_delay', 'weight_reliability', 'weight_shipping')
    def _check_weights_total(self):
        for record in self:
            total = (record.weight_margin + record.weight_delay + 
                    record.weight_reliability + record.weight_shipping)
            if total != 100:
                raise models.ValidationError(
                    f"La somme des pondérations doit être égale à 100% (actuellement {total}%)"
                )

    @api.model
    def get_config(self, company_id=None):
        """Récupère la configuration active pour une société"""
        company_id = company_id or self.env.company.id
        config = self.search([
            ('company_id', '=', company_id),
            ('active', '=', True)
        ], limit=1)
        if not config:
            config = self.create({
                'name': 'Configuration principale',
                'company_id': company_id,
            })
        return config


class DropshipMarginRule(models.Model):
    """Règles de marge spécifiques par catégorie/produit"""
    _name = 'dropship.margin.rule'
    _description = 'Règle de marge dropshipping'
    _order = 'sequence, id'

    name = fields.Char(string='Nom', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    config_id = fields.Many2one('dropship.config', string='Configuration', ondelete='cascade')
    
    # Conditions d'application
    apply_on = fields.Selection([
        ('all', 'Tous les produits'),
        ('category', 'Catégorie de produits'),
        ('product', 'Produit spécifique'),
        ('supplier', 'Fournisseur spécifique'),
    ], string="S'applique sur", default='all', required=True)
    
    category_id = fields.Many2one('product.category', string='Catégorie')
    product_id = fields.Many2one('product.product', string='Produit')
    supplier_id = fields.Many2one('res.partner', string='Fournisseur',
                                  domain=[('supplier_rank', '>', 0)])
    
    # Règle
    rule_type = fields.Selection([
        ('min_margin', 'Marge minimum'),
        ('fixed_margin', 'Marge fixe'),
        ('margin_range', 'Plage de marge'),
    ], string='Type de règle', default='min_margin', required=True)
    
    min_margin = fields.Float(string='Marge minimum (%)')
    max_margin = fields.Float(string='Marge maximum (%)')
    fixed_margin = fields.Float(string='Marge fixe (%)')
    
    # Actions
    action_below_min = fields.Selection([
        ('block', 'Bloquer la commande'),
        ('alert', 'Alerter seulement'),
        ('auto_adjust', 'Ajuster le prix automatiquement'),
    ], string='Action si marge insuffisante', default='alert')

    def check_margin(self, product, supplier, calculated_margin):
        """Vérifie si la marge calculée respecte la règle"""
        self.ensure_one()
        result = {
            'valid': True,
            'message': '',
            'adjusted_margin': calculated_margin
        }
        
        if self.rule_type == 'min_margin':
            if calculated_margin < self.min_margin:
                result['valid'] = False
                result['message'] = f"Marge ({calculated_margin:.1f}%) < minimum ({self.min_margin:.1f}%)"
        
        elif self.rule_type == 'fixed_margin':
            if abs(calculated_margin - self.fixed_margin) > 0.1:
                result['adjusted_margin'] = self.fixed_margin
                result['message'] = f"Marge ajustée à {self.fixed_margin:.1f}%"
        
        elif self.rule_type == 'margin_range':
            if calculated_margin < self.min_margin:
                result['valid'] = False
                result['message'] = f"Marge ({calculated_margin:.1f}%) < minimum ({self.min_margin:.1f}%)"
            elif calculated_margin > self.max_margin:
                result['adjusted_margin'] = self.max_margin
                result['message'] = f"Marge plafonnée à {self.max_margin:.1f}%"
        
        return result
