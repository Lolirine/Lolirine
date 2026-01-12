# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Champ pour identifier si c'est un box de stockage
    is_storage_box = fields.Boolean(
        string="Box de stockage",
        default=False,
        help="Cochez si ce produit est un box de stockage géré par contrat/abonnement"
    )

    # Client/Locataire actuel du box
    current_tenant_id = fields.Many2one(
        'res.partner',
        string="Client actuel",
        domain="[('is_company', '=', False)]",
        help="Le client qui loue actuellement ce box de stockage"
    )

    # Abonnement actuel lié
    current_subscription_id = fields.Many2one(
        'sale.order',
        string="Abonnement actif",
        domain="[('is_subscription', '=', True), ('subscription_state', '=', '3_progress')]",
        help="L'abonnement actif pour ce box"
    )

    # Champ calculé : est-ce que ce box est dans un abonnement actif ?
    is_rented_in_subscription = fields.Boolean(
        string="Loué via abonnement",
        compute='_compute_is_rented_in_subscription',
        store=True,
        help="Indique si ce box est actuellement dans un abonnement actif"
    )

    # Statut de disponibilité du box
    storage_status = fields.Selection([
        ('available', 'Disponible'),
        ('rented', 'Loué'),
        ('reserved', 'Réservé'),
        ('maintenance', 'En maintenance'),
        ('cleaning', 'En nettoyage'),
        ('soon_available', 'Bientôt disponible'),
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

    @api.depends('product_variant_ids.sale_order_line_ids.order_id.state',
                 'product_variant_ids.sale_order_line_ids.order_id.is_subscription',
                 'product_variant_ids.sale_order_line_ids.order_id.subscription_state')
    def _compute_is_rented_in_subscription(self):
        """Calcule si le produit est dans un abonnement actif"""
        for product in self:
            if not product.is_storage_box:
                product.is_rented_in_subscription = False
                continue
            
            # Chercher un abonnement actif contenant ce produit
            active_subscription = self.env['sale.order'].search([
                ('is_subscription', '=', True),
                ('state', '=', 'sale'),
                ('subscription_state', 'in', ['3_progress', '4_paused']),
                ('order_line.product_template_id', '=', product.id),
            ], limit=1)
            
            product.is_rented_in_subscription = bool(active_subscription)

    @api.depends('is_storage_box', 'storage_status', 'storage_appointment_override')
    def _compute_show_appointment_button(self):
        """Calcule si le bouton rendez-vous doit être affiché (box disponible ou bientôt disponible)"""
        config = self.env['ir.config_parameter'].sudo()
        global_enabled = config.get_param('lolirine_storage.enable_appointment_button', 'False') == 'True'

        for product in self:
            show = False
            if product.is_storage_box and product.storage_status in ('available', 'soon_available'):
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
            if product.is_storage_box and product.storage_status not in ('available', 'soon_available'):
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
            'cleaning': 'En nettoyage',
            'soon_available': 'Bientôt disponible',
        }
        for product in self:
            product.storage_status_display = status_labels.get(product.storage_status, '')

    @api.onchange('current_tenant_id')
    def _onchange_current_tenant_id(self):
        """Met à jour le statut quand un client est assigné"""
        for product in self:
            if product.current_tenant_id and product.storage_status == 'available':
                product.storage_status = 'rented'
            elif not product.current_tenant_id and product.storage_status == 'rented':
                product.storage_status = 'available'

    @api.onchange('current_subscription_id')
    def _onchange_current_subscription_id(self):
        """Remplit le client depuis l'abonnement sélectionné"""
        for product in self:
            if product.current_subscription_id:
                product.current_tenant_id = product.current_subscription_id.partner_id

    def action_view_subscription(self):
        """Ouvre l'abonnement actuel"""
        self.ensure_one()
        if self.current_subscription_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Abonnement',
                'res_model': 'sale.order',
                'res_id': self.current_subscription_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False

    def action_view_tenant(self):
        """Ouvre la fiche du client actuel"""
        self.ensure_one()
        if self.current_tenant_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Client',
                'res_model': 'res.partner',
                'res_id': self.current_tenant_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False

    def action_sync_from_subscriptions(self):
        """Synchronise le statut et les liens depuis les abonnements actifs"""
        for product in self.filtered('is_storage_box'):
            # Chercher un abonnement actif
            active_sub = self.env['sale.order'].search([
                ('is_subscription', '=', True),
                ('state', '=', 'sale'),
                ('subscription_state', 'in', ['3_progress', '4_paused']),
                ('order_line.product_template_id', '=', product.id),
            ], limit=1, order='date_order desc')
            
            if active_sub:
                product.write({
                    'storage_status': 'rented',
                    'current_subscription_id': active_sub.id,
                    'current_tenant_id': active_sub.partner_id.id,
                })
            elif product.storage_status == 'rented' and not product.current_tenant_id:
                # Pas d'abonnement actif et pas de locataire manuel → disponible
                product.write({
                    'storage_status': 'available',
                    'current_subscription_id': False,
                })

    def write(self, vals):
        """Override write pour synchroniser le ruban avec le statut"""
        res = super().write(vals)
        if 'storage_status' in vals or 'is_storage_box' in vals:
            self._sync_ribbon_with_status()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Override create pour synchroniser le ruban avec le statut"""
        records = super().create(vals_list)
        records.filtered('is_storage_box')._sync_ribbon_with_status()
        return records

    def _sync_ribbon_with_status(self):
        """Synchronise le ruban (étiquette) du produit avec son statut de stockage"""
        # Mapping statut -> xmlid du ruban
        status_ribbon_mapping = {
            'available': 'lolirine_storage_availability.ribbon_storage_available',
            'rented': 'lolirine_storage_availability.ribbon_storage_rented',
            'reserved': 'lolirine_storage_availability.ribbon_storage_reserved',
            'maintenance': 'lolirine_storage_availability.ribbon_storage_maintenance',
            'cleaning': 'lolirine_storage_availability.ribbon_storage_cleaning',
            'soon_available': 'lolirine_storage_availability.ribbon_storage_soon_available',
        }
        
        for product in self.filtered('is_storage_box'):
            ribbon_xmlid = status_ribbon_mapping.get(product.storage_status)
            if ribbon_xmlid:
                try:
                    ribbon = self.env.ref(ribbon_xmlid, raise_if_not_found=False)
                    if ribbon and product.website_ribbon_id != ribbon:
                        super(ProductTemplate, product).write({'website_ribbon_id': ribbon.id})
                except Exception:
                    pass  # Ignorer si le ruban n'existe pas

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
        self.filtered('is_storage_box').write({
            'storage_status': 'available', 
            'current_tenant_id': False,
            'current_subscription_id': False
        })

    def action_set_rented(self):
        """Marque le box comme loué"""
        self.filtered('is_storage_box').write({'storage_status': 'rented'})

    def action_set_reserved(self):
        """Marque le box comme réservé"""
        self.filtered('is_storage_box').write({'storage_status': 'reserved'})

    def action_set_maintenance(self):
        """Marque le box en maintenance"""
        self.filtered('is_storage_box').write({'storage_status': 'maintenance'})

    def action_set_cleaning(self):
        """Marque le box en nettoyage"""
        self.filtered('is_storage_box').write({'storage_status': 'cleaning'})

    def action_set_soon_available(self):
        """Marque le box comme bientôt disponible"""
        self.filtered('is_storage_box').write({'storage_status': 'soon_available'})

    def action_convert_to_storage_box(self):
        """Convertit le produit en box de stockage"""
        self.write({'is_storage_box': True, 'storage_status': 'available'})


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_view_appointments(self):
        """Délègue au template parent"""
        self.ensure_one()
        return self.product_tmpl_id.action_view_appointments()
