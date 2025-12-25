# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ApartmentIntervention(models.Model):
    _name = 'apartment.intervention'
    _description = 'Intervention / Réparation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_planned desc, priority desc'

    name = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default=lambda self: _('Nouveau'),
    )
    active = fields.Boolean(default=True)
    
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
        domain="[('property_id', '=', property_id)]",
    )
    control_visit_id = fields.Many2one(
        'apartment.control.visit',
        string='Visite de contrôle',
        help='Si l\'intervention fait suite à une visite de contrôle',
    )
    
    # Description
    title = fields.Char(string='Titre', required=True, tracking=True)
    description = fields.Html(string='Description détaillée')
    
    # Type et priorité
    intervention_type = fields.Selection([
        ('repair', 'Réparation'),
        ('maintenance', 'Maintenance'),
        ('improvement', 'Amélioration'),
        ('emergency', 'Urgence'),
        ('inspection', 'Inspection'),
        ('other', 'Autre'),
    ], string='Type', default='repair', tracking=True)
    
    priority = fields.Selection([
        ('0', 'Basse'),
        ('1', 'Normale'),
        ('2', 'Haute'),
        ('3', 'Urgente'),
    ], string='Priorité', default='1', tracking=True)
    
    # Catégorie
    category = fields.Selection([
        ('plumbing', 'Plomberie'),
        ('electricity', 'Électricité'),
        ('heating', 'Chauffage'),
        ('locksmith', 'Serrurerie'),
        ('carpentry', 'Menuiserie'),
        ('painting', 'Peinture'),
        ('appliance', 'Électroménager'),
        ('roof', 'Toiture'),
        ('facade', 'Façade'),
        ('garden', 'Jardin'),
        ('cleaning', 'Nettoyage'),
        ('pest', 'Nuisibles'),
        ('other', 'Autre'),
    ], string='Catégorie', tracking=True)
    
    # Localisation
    room_type_id = fields.Many2one(
        'apartment.room.type',
        string='Pièce',
    )
    location_detail = fields.Char(string='Localisation précise')
    
    # Planification
    date_reported = fields.Date(
        string='Date de signalement',
        default=fields.Date.today,
    )
    reported_by = fields.Selection([
        ('tenant', 'Locataire'),
        ('landlord', 'Bailleur'),
        ('visit', 'Visite de contrôle'),
        ('other', 'Autre'),
    ], string='Signalé par', default='tenant')
    
    date_planned = fields.Date(string='Date prévue', tracking=True)
    time_planned = fields.Float(string='Heure prévue')
    
    date_done = fields.Datetime(string='Date d\'exécution', tracking=True)
    duration = fields.Float(string='Durée (heures)')
    
    # Intervenant
    contractor_id = fields.Many2one(
        'res.partner',
        string='Intervenant/Entreprise',
        domain="[('is_company', '=', True)]",
    )
    contractor_contact = fields.Char(string='Contact intervenant')
    contractor_phone = fields.Char(string='Tél. intervenant')
    
    # Devis et factures
    quote_amount = fields.Float(string='Montant devis (€)')
    quote_date = fields.Date(string='Date devis')
    quote_valid_until = fields.Date(string='Devis valide jusqu\'au')
    quote_approved = fields.Boolean(string='Devis approuvé')
    quote_approved_date = fields.Date(string='Date approbation')
    
    invoice_amount = fields.Float(string='Montant facture (€)', tracking=True)
    invoice_date = fields.Date(string='Date facture')
    invoice_reference = fields.Char(string='Réf. facture')
    invoice_paid = fields.Boolean(string='Facture payée')
    
    # Imputation
    charge_to = fields.Selection([
        ('landlord', 'Bailleur'),
        ('tenant', 'Locataire'),
        ('shared', 'Partagé'),
        ('insurance', 'Assurance'),
    ], string='À charge de', default='landlord', tracking=True)
    tenant_share = fields.Float(
        string='Part locataire (%)',
        default=0.0,
        help='Pourcentage à charge du locataire si partagé',
    )
    
    # Photos
    photo_before = fields.Image(
        string='Photo avant',
        max_width=1920,
        max_height=1920,
    )
    photo_after = fields.Image(
        string='Photo après',
        max_width=1920,
        max_height=1920,
    )
    
    # Documents
    document_ids = fields.One2many(
        'apartment.document',
        'intervention_id',
        string='Documents',
    )
    
    # État
    state = fields.Selection([
        ('draft', 'Signalé'),
        ('planned', 'Planifié'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
        ('cancelled', 'Annulé'),
    ], string='Statut', default='draft', tracking=True)
    
    # Résultat
    work_done = fields.Html(string='Travaux effectués')
    warranty_until = fields.Date(string='Garantie jusqu\'au')
    
    # Notes
    notes = fields.Text(string='Notes internes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('apartment.intervention') or _('Nouveau')
        return super().create(vals_list)

    def action_plan(self):
        """Planifier l'intervention"""
        for record in self:
            if not record.date_planned:
                raise UserError(_('Veuillez définir une date prévue.'))
            record.state = 'planned'

    def action_start(self):
        """Démarrer l'intervention"""
        for record in self:
            record.state = 'in_progress'

    def action_done(self):
        """Terminer l'intervention"""
        for record in self:
            record.write({
                'state': 'done',
                'date_done': fields.Datetime.now(),
            })

    def action_cancel(self):
        """Annuler l'intervention"""
        for record in self:
            record.state = 'cancelled'

    def action_reset_draft(self):
        """Remettre en brouillon"""
        for record in self:
            record.state = 'draft'

    def action_approve_quote(self):
        """Approuver le devis"""
        for record in self:
            record.write({
                'quote_approved': True,
                'quote_approved_date': fields.Date.today(),
            })

    def action_notify_tenant(self):
        """Notifier le locataire de l'intervention"""
        for record in self:
            if not record.lease_id or not record.lease_id.tenant_id:
                raise UserError(_('Aucun locataire associé à cette intervention.'))
            
            template = self.env.ref('apartment_rental.mail_template_intervention_notification', raise_if_not_found=False)
            if template:
                template.send_mail(record.id, force_send=True)
