# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class ApartmentInventory(models.Model):
    _name = 'apartment.inventory'
    _description = 'État des lieux'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default=lambda self: _('Nouveau'),
    )
    active = fields.Boolean(default=True)
    
    # Type
    inventory_type = fields.Selection([
        ('entry', 'Entrée'),
        ('exit', 'Sortie'),
    ], string='Type', required=True, default='entry', tracking=True)
    
    # Relations
    property_id = fields.Many2one(
        'apartment.property',
        string='Bien',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    lease_id = fields.Many2one(
        'apartment.lease',
        string='Bail',
        ondelete='restrict',
        tracking=True,
    )
    tenant_id = fields.Many2one(
        'apartment.tenant',
        string='Locataire',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    entry_inventory_id = fields.Many2one(
        'apartment.inventory',
        string='État des lieux d\'entrée (référence)',
        domain="[('property_id', '=', property_id), ('inventory_type', '=', 'entry')]",
        help='Pour comparaison avec l\'état d\'entrée',
    )
    
    # Date et participants
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    time_start = fields.Float(string='Heure de début')
    time_end = fields.Float(string='Heure de fin')
    
    conducted_by = fields.Many2one(
        'res.users',
        string='Réalisé par',
        default=lambda self: self.env.user,
    )
    expert_name = fields.Char(string='Expert (si applicable)')
    expert_company = fields.Char(string='Société d\'expertise')
    
    # Présences
    tenant_present = fields.Boolean(string='Locataire présent', default=True)
    landlord_present = fields.Boolean(string='Bailleur présent', default=True)
    other_present = fields.Char(string='Autres personnes présentes')
    
    # Relevés de compteurs
    electricity_reading = fields.Float(string='Compteur électricité')
    gas_reading = fields.Float(string='Compteur gaz')
    water_reading = fields.Float(string='Compteur eau')
    heating_reading = fields.Float(string='Compteur chauffage')
    
    # Clés et accès
    keys_count = fields.Integer(string='Nombre de clés')
    keys_detail = fields.Text(string='Détail des clés')
    remote_count = fields.Integer(string='Télécommandes')
    badge_count = fields.Integer(string='Badges d\'accès')
    mailbox_key = fields.Boolean(string='Clé boîte aux lettres')
    cellar_key = fields.Boolean(string='Clé cave')
    garage_key = fields.Boolean(string='Clé garage')
    
    # État général
    general_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
    ], string='État général', tracking=True)
    cleanliness = fields.Selection([
        ('very_clean', 'Très propre'),
        ('clean', 'Propre'),
        ('acceptable', 'Acceptable'),
        ('dirty', 'Sale'),
        ('very_dirty', 'Très sale'),
    ], string='Propreté')
    
    # Lignes détaillées par pièce
    line_ids = fields.One2many(
        'apartment.inventory.line',
        'inventory_id',
        string='Détail par pièce',
    )
    
    # Photos
    photo_ids = fields.One2many(
        'apartment.inventory.photo',
        'inventory_id',
        string='Photos',
    )
    photo_count = fields.Integer(
        string='Nombre de photos',
        compute='_compute_photo_count',
    )
    
    # Observations
    observations = fields.Html(string='Observations générales')
    damages_noted = fields.Html(string='Dégâts constatés')
    repairs_needed = fields.Html(string='Réparations nécessaires')
    
    # Comparaison (pour sortie)
    comparison_notes = fields.Html(
        string='Comparaison avec l\'entrée',
        help='Notes de comparaison avec l\'état des lieux d\'entrée',
    )
    damages_chargeable = fields.Html(string='Dégâts imputables au locataire')
    estimated_cost = fields.Float(string='Coût estimé des réparations (€)')
    
    # Signatures
    tenant_signature = fields.Binary(string='Signature locataire')
    tenant_signature_date = fields.Datetime(string='Date signature locataire')
    landlord_signature = fields.Binary(string='Signature bailleur')
    landlord_signature_date = fields.Datetime(string='Date signature bailleur')
    
    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('in_progress', 'En cours'),
        ('pending_signature', 'En attente de signature'),
        ('signed', 'Signé'),
        ('disputed', 'Contesté'),
    ], string='Statut', default='draft', tracking=True)
    
    # Notes
    notes = fields.Text(string='Notes internes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                prefix = 'EDL-E' if vals.get('inventory_type') == 'entry' else 'EDL-S'
                vals['name'] = self.env['ir.sequence'].next_by_code('apartment.inventory') or _('Nouveau')
                vals['name'] = prefix + vals['name'][3:] if vals['name'].startswith('EDL') else vals['name']
        return super().create(vals_list)

    def _compute_photo_count(self):
        for record in self:
            record.photo_count = len(record.photo_ids)

    @api.onchange('property_id')
    def _onchange_property_id(self):
        """Pré-remplir les pièces basées sur le bien"""
        if self.property_id and not self.line_ids:
            room_types = self.env['apartment.room.type'].search([])
            lines = []
            for room_type in room_types:
                lines.append((0, 0, {
                    'room_type_id': room_type.id,
                    'name': room_type.name,
                }))
            self.line_ids = lines

    @api.onchange('entry_inventory_id')
    def _onchange_entry_inventory(self):
        """Copier les lignes de l'état d'entrée pour comparaison"""
        if self.entry_inventory_id and self.inventory_type == 'exit':
            lines = []
            for line in self.entry_inventory_id.line_ids:
                lines.append((0, 0, {
                    'room_type_id': line.room_type_id.id,
                    'name': line.name,
                    'entry_condition': line.condition,
                    'entry_notes': line.notes,
                }))
            self.line_ids = lines

    def action_start(self):
        """Démarrer l'état des lieux"""
        for record in self:
            record.state = 'in_progress'

    def action_complete(self):
        """Terminer l'état des lieux"""
        for record in self:
            if not record.line_ids:
                raise UserError(_('Veuillez ajouter au moins une pièce à l\'état des lieux.'))
            record.state = 'pending_signature'

    def action_sign(self):
        """Marquer comme signé"""
        for record in self:
            if not record.tenant_signature or not record.landlord_signature:
                raise UserError(_('Les signatures du locataire et du bailleur sont requises.'))
            record.state = 'signed'
            
            # Lier au bail si c'est un état d'entrée ou de sortie
            if record.lease_id:
                if record.inventory_type == 'entry':
                    record.lease_id.inventory_entry_id = record.id
                else:
                    record.lease_id.inventory_exit_id = record.id

    def action_dispute(self):
        """Marquer comme contesté"""
        for record in self:
            record.state = 'disputed'

    def action_reset_draft(self):
        """Remettre en brouillon"""
        for record in self:
            record.state = 'draft'

    def action_view_photos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Photos'),
            'res_model': 'apartment.inventory.photo',
            'view_mode': 'kanban,list,form',
            'domain': [('inventory_id', '=', self.id)],
            'context': {'default_inventory_id': self.id},
        }

    def action_add_rooms(self):
        """Action pour ajouter des pièces standards"""
        self.ensure_one()
        room_types = self.env['apartment.room.type'].search([])
        existing_rooms = self.line_ids.mapped('room_type_id')
        
        for room_type in room_types:
            if room_type not in existing_rooms:
                self.env['apartment.inventory.line'].create({
                    'inventory_id': self.id,
                    'room_type_id': room_type.id,
                    'name': room_type.name,
                })

    def action_print_report(self):
        """Imprimer le rapport d'état des lieux"""
        return self.env.ref('apartment_rental.action_report_inventory').report_action(self)

    def action_compare_with_entry(self):
        """Comparer avec l'état d'entrée"""
        self.ensure_one()
        if self.inventory_type != 'exit':
            raise UserError(_('Cette action n\'est disponible que pour les états de sortie.'))
        if not self.entry_inventory_id:
            raise UserError(_('Veuillez sélectionner un état des lieux d\'entrée pour la comparaison.'))
        
        # Générer le rapport de comparaison
        comparison = []
        for exit_line in self.line_ids:
            entry_line = self.entry_inventory_id.line_ids.filtered(
                lambda l: l.room_type_id == exit_line.room_type_id
            )
            if entry_line:
                comparison.append({
                    'room': exit_line.name,
                    'entry_condition': entry_line.condition,
                    'exit_condition': exit_line.condition,
                    'entry_notes': entry_line.notes,
                    'exit_notes': exit_line.notes,
                    'degradation': exit_line.condition != entry_line.condition,
                })
        
        return comparison
