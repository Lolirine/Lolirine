# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StorageBox(models.Model):
    _name = 'storage.box'
    _description = 'Box de stockage'
    _order = 'floor_id, name'

    name = fields.Char(string='Numéro de box', required=True, index=True)
    floor_id = fields.Many2one('storage.floor', string='Étage', required=True)
    
    # Lien vers le produit (pour les abonnements)
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Produit lié',
        domain="[('is_storage_box', '=', True)]",
        help="Produit e-commerce lié à ce box pour les abonnements"
    )
    
    # Dimensions
    width = fields.Float(string='Largeur (cm)', required=True)
    depth = fields.Float(string='Profondeur (cm)', required=True)
    height = fields.Float(string='Hauteur (cm)', required=True)
    volume = fields.Float(string='Volume (m³)', compute='_compute_volume', store=True)
    surface = fields.Float(string='Surface (m²)', compute='_compute_surface', store=True)
    
    # Informations commerciales
    price_monthly = fields.Float(string='Prix mensuel (€)', required=True)
    registration_fee = fields.Float(string='Frais de dossier (€)', default=15.0)
    deposit_months = fields.Integer(string='Caution (mois)', default=2)
    deposit_amount = fields.Float(string='Montant caution (€)', compute='_compute_deposit')
    
    # Statut
    status = fields.Selection([
        ('disponible', 'Disponible'),
        ('occupe', 'Occupé'),
        ('maintenance', 'Maintenance'),
        ('nettoyage', 'Nettoyage'),
        ('reserve', 'Réservé'),
        ('bientot_dispo', 'Bientôt disponible'),
        ('inspection', 'En inspection'),
        ('technique', 'Technique'),
    ], string='Statut', required=True, default='disponible')
    
    # Date de disponibilité
    date_available = fields.Date(string='Disponible à partir du',
                                  help="Date à laquelle le box sera à nouveau disponible")
    
    # Position sur le plan
    position_x = fields.Float(string='Position X')
    position_y = fields.Float(string='Position Y')
    grid_row = fields.Integer(string='Ligne grille')
    grid_col = fields.Integer(string='Colonne grille')
    aisle = fields.Selection([
        ('left', 'Allée gauche'),
        ('right', 'Allée droite'),
    ], string='Allée', default='left', required=True,
       help="Choisissez dans quelle allée placer le box sur le plan")
    
    # Relations - Réservations internes
    reservation_ids = fields.One2many('box.reservation', 'box_id', string='Réservations')
    current_reservation_id = fields.Many2one('box.reservation', string='Réservation actuelle',
                                             compute='_compute_current_reservation', store=True)
    
    # Client actuel (depuis réservation OU abonnement)
    current_customer_name = fields.Char(
        string='Client actuel',
        compute='_compute_current_customer',
        store=True,
        help="Nom du client occupant actuellement le box"
    )
    current_partner_id = fields.Many2one(
        'res.partner',
        string='Client (contact)',
        compute='_compute_current_customer',
        store=True,
        help="Contact du client occupant le box"
    )
    current_subscription_id = fields.Many2one(
        'sale.order',
        string='Abonnement actif',
        compute='_compute_current_customer',
        store=True,
        help="Abonnement actif pour ce box"
    )
    
    # Informations supplémentaires
    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes internes')
    active = fields.Boolean(string='Actif', default=True)
    
    @api.depends('width', 'depth', 'height')
    def _compute_volume(self):
        for box in self:
            box.volume = (box.width * box.depth * box.height) / 1000000 if box.width and box.depth and box.height else 0
    
    @api.depends('width', 'depth')
    def _compute_surface(self):
        for box in self:
            box.surface = (box.width * box.depth) / 10000 if box.width and box.depth else 0
    
    @api.depends('price_monthly', 'deposit_months')
    def _compute_deposit(self):
        for box in self:
            box.deposit_amount = box.price_monthly * box.deposit_months
    
    @api.depends('reservation_ids', 'reservation_ids.state')
    def _compute_current_reservation(self):
        for box in self:
            current = box.reservation_ids.filtered(
                lambda r: r.state in ['confirmed', 'ongoing'] and r.active
            )
            box.current_reservation_id = current[0] if current else False
    
    @api.depends('product_tmpl_id', 'reservation_ids', 'reservation_ids.state', 
                 'reservation_ids.customer_name', 'reservation_ids.partner_id')
    def _compute_current_customer(self):
        """Récupère le client actuel depuis l'abonnement actif ou la réservation"""
        SaleOrder = self.env['sale.order']
        ProductProduct = self.env['product.product']
        
        for box in self:
            customer_name = False
            partner = False
            subscription = False
            
            # 1. D'abord chercher un abonnement actif via le produit lié
            if box.product_tmpl_id:
                # Récupérer les variantes (product.product) du template
                product_variants = ProductProduct.search([
                    ('product_tmpl_id', '=', box.product_tmpl_id.id)
                ])
                
                if product_variants:
                    # Chercher les abonnements actifs qui contiennent ce produit
                    active_subscriptions = SaleOrder.search([
                        ('is_subscription', '=', True),
                        ('subscription_state', '=', '3_progress'),
                        ('order_line.product_id', 'in', product_variants.ids),
                    ], limit=1, order='date_order desc')
                    
                    if active_subscriptions:
                        subscription = active_subscriptions[0]
                        partner = subscription.partner_id
                        customer_name = partner.name if partner else False
            
            # 2. Si pas d'abonnement, chercher dans les réservations internes
            if not customer_name:
                current_reservation = box.reservation_ids.filtered(
                    lambda r: r.state in ['confirmed', 'ongoing'] and r.active
                )
                if current_reservation:
                    reservation = current_reservation[0]
                    customer_name = reservation.customer_name
                    partner = reservation.partner_id
            
            box.current_customer_name = customer_name
            box.current_partner_id = partner.id if partner else False
            box.current_subscription_id = subscription.id if subscription else False
    
    def action_refresh_customer(self):
        """Force le recalcul des informations client"""
        self._compute_current_customer()
        return True
    
    def action_link_product_by_name(self):
        """Lie automatiquement le produit en cherchant par nom"""
        ProductTemplate = self.env['product.template']
        for box in self:
            if not box.product_tmpl_id:
                # Chercher un produit avec un nom similaire
                product = ProductTemplate.search([
                    ('is_storage_box', '=', True),
                    '|',
                    ('name', 'ilike', box.name),
                    ('default_code', '=', box.name),
                ], limit=1)
                if product:
                    box.product_tmpl_id = product.id
        return True
    
    def get_status_color(self):
        """Retourne la couleur associée au statut depuis la configuration"""
        StatusColor = self.env['storage.status.color'].sudo()
        return StatusColor.get_color_for_status(self.status)
    
    def action_make_available(self):
        self.status = 'disponible'
    
    def action_make_occupied(self):
        self.status = 'occupe'
    
    def action_make_maintenance(self):
        self.status = 'maintenance'

    def action_mark_as_personal(self):
        """Bouton : marque la box comme usage personnel + statut 'inspection'."""
        for box in self:
            if box.current_subscription_id:
                raise UserError(_(
                    "Impossible : la box %(box)s est sous contrat (%(sub)s pour %(client)s).\n"
                    "Vous devez d'abord clôturer le contrat avant de la marquer comme personnelle."
                ) % {
                    'box': box.name,
                    'sub': box.current_subscription_id.name,
                    'client': box.current_customer_name or '',
                })
            box.write({
                'is_personal_use': True,
                'status': 'inspection',
            })
            box.message_post(
                body=_("Box marquée comme usage personnel — statut mis à 'En inspection'.")
            )
        return True

    def action_unmark_as_personal(self):
        """Bouton : retire le statut personnel + remet en disponible."""
        for box in self:
            box.write({
                'is_personal_use': False,
                'status': 'disponible',
            })
            box.message_post(
                body=_("Box remise en exploitation — statut mis à 'Disponible'.")
            )
        return True
        
    def action_view_on_website(self):
        """Ouvre la page du plan interactif sur le site web"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/storage/plan',
            'target': 'new',
        }
    
    def action_view_current_subscription(self):
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
    
    def action_view_customer(self):
        """Ouvre la fiche du client actuel"""
        self.ensure_one()
        if self.current_partner_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Client',
                'res_model': 'res.partner',
                'res_id': self.current_partner_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False
    
    def get_box_details(self):
        """Retourne les détails du box pour l'affichage web"""
        self.ensure_one()
        date_available_str = ''
        if self.date_available:
            date_available_str = self.date_available.strftime('%d/%m/%Y')
        
        status_color = self.get_status_color()
        
        return {
            'id': self.id,
            'name': self.name,
            'width': self.width,
            'depth': self.depth,
            'height': self.height,
            'volume': round(self.volume, 1),
            'surface': round(self.surface, 1),
            'price_monthly': self.price_monthly,
            'registration_fee': self.registration_fee,
            'deposit_months': self.deposit_months,
            'deposit_amount': self.deposit_amount,
            'status': self.status,
            'status_label': dict(self._fields['status'].selection).get(self.status),
            'status_color': status_color,
            'floor': self.floor_id.name,
            'description': self.description or '',
            'aisle': self.aisle or 'left',
            'date_available': date_available_str,
            'current_customer': self.current_customer_name or '',
        }
    
    @api.model
    def get_export_data(self):
        """Retourne les données pour l'export XLSX"""
        boxes = self.search([])
        data = []
        for box in boxes:
            data.append({
                'name': box.name,
                'floor': box.floor_id.name if box.floor_id else '',
                'floor_code': box.floor_id.code if box.floor_id else '',
                'width': box.width,
                'depth': box.depth,
                'height': box.height,
                'volume': box.volume,
                'surface': box.surface,
                'price_monthly': box.price_monthly,
                'registration_fee': box.registration_fee,
                'deposit_months': box.deposit_months,
                'status': box.status,
                'date_available': box.date_available.strftime('%Y-%m-%d') if box.date_available else '',
                'aisle': box.aisle,
                'description': box.description or '',
                'active': box.active,
                'current_customer': box.current_customer_name or '',
            })
        return data
    
    @api.model
    def import_from_xlsx_data(self, data_rows):
        """Importe les boxes depuis les données XLSX"""
        Floor = self.env['storage.floor']
        created = 0
        updated = 0
        errors = []
        
        for row_num, row in enumerate(data_rows, start=2):
            try:
                name = row.get('name', '').strip()
                if not name:
                    continue
                
                floor_name = row.get('floor', '').strip()
                floor_code = row.get('floor_code', '').strip()
                floor = False
                if floor_name:
                    floor = Floor.search([('name', '=', floor_name)], limit=1)
                    if not floor and floor_code:
                        floor = Floor.create({
                            'name': floor_name,
                            'code': floor_code,
                        })
                
                box = self.search([('name', '=', name)], limit=1)
                
                vals = {
                    'name': name,
                    'width': float(row.get('width', 0) or 0),
                    'depth': float(row.get('depth', 0) or 0),
                    'height': float(row.get('height', 0) or 0),
                    'price_monthly': float(row.get('price_monthly', 0) or 0),
                    'registration_fee': float(row.get('registration_fee', 15) or 15),
                    'deposit_months': int(row.get('deposit_months', 2) or 2),
                    'status': row.get('status', 'disponible') or 'disponible',
                    'aisle': row.get('aisle', 'left') or 'left',
                    'description': row.get('description', ''),
                    'active': row.get('active', True),
                }
                
                if floor:
                    vals['floor_id'] = floor.id
                
                date_str = row.get('date_available', '')
                if date_str:
                    try:
                        from datetime import datetime
                        vals['date_available'] = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except:
                        pass
                
                if box:
                    box.write(vals)
                    updated += 1
                else:
                    if not floor:
                        errors.append(f"Ligne {row_num}: Étage requis pour le box {name}")
                        continue
                    self.create(vals)
                    created += 1
                    
            except Exception as e:
                errors.append(f"Ligne {row_num}: {str(e)}")
        
        return {
            'created': created,
            'updated': updated,
            'errors': errors,
        }
    
    @api.model
    def cron_refresh_customers(self):
        """Tâche planifiée pour rafraîchir les informations clients"""
        boxes = self.search([('product_tmpl_id', '!=', False)])
        boxes._compute_current_customer()
        return True
