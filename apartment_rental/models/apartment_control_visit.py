# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import date


class ApartmentControlVisit(models.Model):
    _name = 'apartment.control.visit'
    _description = 'Visite de contrôle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

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
        domain="[('property_id', '=', property_id), ('state', '=', 'active')]",
        tracking=True,
    )
    tenant_id = fields.Many2one(
        'apartment.tenant',
        string='Locataire',
        related='lease_id.tenant_id',
        store=True,
    )
    
    # Planification
    date = fields.Date(
        string='Date prévue',
        required=True,
        tracking=True,
    )
    time_scheduled = fields.Float(string='Heure prévue')
    duration_planned = fields.Float(
        string='Durée prévue (h)',
        default=1.0,
    )
    
    # Exécution
    date_done = fields.Datetime(string='Date/heure effective')
    duration_actual = fields.Float(string='Durée effective (h)')
    conducted_by = fields.Many2one(
        'res.users',
        string='Réalisée par',
        default=lambda self: self.env.user,
    )
    
    # Présences
    tenant_present = fields.Boolean(string='Locataire présent')
    tenant_notified = fields.Boolean(string='Locataire prévenu')
    notification_date = fields.Date(string='Date de notification')
    notification_method = fields.Selection([
        ('email', 'Email'),
        ('letter', 'Courrier'),
        ('sms', 'SMS'),
        ('phone', 'Téléphone'),
        ('in_person', 'En personne'),
    ], string='Moyen de notification')
    
    # Type de visite
    visit_type = fields.Selection([
        ('routine', 'Contrôle de routine'),
        ('complaint', 'Suite à plainte'),
        ('maintenance', 'Vérification maintenance'),
        ('pre_exit', 'Pré-état de sortie'),
        ('emergency', 'Urgence'),
        ('other', 'Autre'),
    ], string='Type de visite', default='routine', tracking=True)
    
    # État général constaté
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
    
    # Points de contrôle
    check_heating = fields.Boolean(string='Vérifier chauffage')
    heating_ok = fields.Boolean(string='Chauffage OK')
    heating_notes = fields.Text(string='Notes chauffage')
    
    check_plumbing = fields.Boolean(string='Vérifier plomberie')
    plumbing_ok = fields.Boolean(string='Plomberie OK')
    plumbing_notes = fields.Text(string='Notes plomberie')
    
    check_electricity = fields.Boolean(string='Vérifier électricité')
    electricity_ok = fields.Boolean(string='Électricité OK')
    electricity_notes = fields.Text(string='Notes électricité')
    
    check_ventilation = fields.Boolean(string='Vérifier ventilation')
    ventilation_ok = fields.Boolean(string='Ventilation OK')
    ventilation_notes = fields.Text(string='Notes ventilation')
    
    check_smoke_detectors = fields.Boolean(string='Vérifier détecteurs fumée')
    smoke_detectors_ok = fields.Boolean(string='Détecteurs OK')
    smoke_detectors_notes = fields.Text(string='Notes détecteurs')
    
    check_windows = fields.Boolean(string='Vérifier fenêtres')
    windows_ok = fields.Boolean(string='Fenêtres OK')
    windows_notes = fields.Text(string='Notes fenêtres')
    
    check_doors = fields.Boolean(string='Vérifier portes')
    doors_ok = fields.Boolean(string='Portes OK')
    doors_notes = fields.Text(string='Notes portes')
    
    check_humidity = fields.Boolean(string='Vérifier humidité')
    humidity_ok = fields.Boolean(string='Humidité OK')
    humidity_level = fields.Float(string='Taux d\'humidité (%)')
    humidity_notes = fields.Text(string='Notes humidité')
    
    # Observations
    observations = fields.Html(string='Observations générales')
    anomalies = fields.Html(string='Anomalies constatées')
    recommendations = fields.Html(string='Recommandations')
    
    # Actions requises
    action_required = fields.Boolean(
        string='Action requise',
        compute='_compute_action_required',
        store=True,
    )
    urgent_action = fields.Boolean(string='Action urgente')
    action_description = fields.Text(string='Description des actions')
    action_deadline = fields.Date(string='Délai pour action')
    
    # Suivi
    followup_needed = fields.Boolean(string='Suivi nécessaire')
    followup_date = fields.Date(string='Date de suivi')
    followup_notes = fields.Text(string='Notes de suivi')
    
    # Photos
    photo_ids = fields.One2many(
        'apartment.control.visit.photo',
        'visit_id',
        string='Photos',
    )
    photo_count = fields.Integer(
        string='Nombre de photos',
        compute='_compute_photo_count',
    )
    
    # Interventions liées
    intervention_ids = fields.One2many(
        'apartment.intervention',
        'control_visit_id',
        string='Interventions créées',
    )
    
    # État
    state = fields.Selection([
        ('planned', 'Planifiée'),
        ('notified', 'Locataire notifié'),
        ('done', 'Effectuée'),
        ('cancelled', 'Annulée'),
    ], string='Statut', default='planned', tracking=True)
    
    # Notes
    notes = fields.Text(string='Notes internes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('apartment.control.visit') or _('Nouveau')
        return super().create(vals_list)

    def _compute_photo_count(self):
        for record in self:
            record.photo_count = len(record.photo_ids)

    @api.depends(
        'heating_ok', 'plumbing_ok', 'electricity_ok', 'ventilation_ok',
        'smoke_detectors_ok', 'windows_ok', 'doors_ok', 'humidity_ok'
    )
    def _compute_action_required(self):
        for record in self:
            checks = [
                (record.check_heating, record.heating_ok),
                (record.check_plumbing, record.plumbing_ok),
                (record.check_electricity, record.electricity_ok),
                (record.check_ventilation, record.ventilation_ok),
                (record.check_smoke_detectors, record.smoke_detectors_ok),
                (record.check_windows, record.windows_ok),
                (record.check_doors, record.doors_ok),
                (record.check_humidity, record.humidity_ok),
            ]
            record.action_required = any(
                checked and not ok for checked, ok in checks
            )

    @api.onchange('property_id')
    def _onchange_property_id(self):
        if self.property_id:
            current_lease = self.property_id.current_lease_id
            if current_lease:
                self.lease_id = current_lease.id

    def action_notify_tenant(self):
        """Notifier le locataire de la visite"""
        for record in self:
            if not record.tenant_id:
                raise UserError(_('Aucun locataire associé à cette visite.'))
            
            # Envoyer l'email
            template = self.env.ref('apartment_rental.mail_template_control_visit_notification', raise_if_not_found=False)
            if template:
                template.send_mail(record.id, force_send=True)
            
            record.write({
                'state': 'notified',
                'tenant_notified': True,
                'notification_date': date.today(),
                'notification_method': 'email',
            })

    def action_mark_done(self):
        """Marquer la visite comme effectuée"""
        for record in self:
            record.write({
                'state': 'done',
                'date_done': fields.Datetime.now(),
            })

    def action_cancel(self):
        """Annuler la visite"""
        for record in self:
            record.state = 'cancelled'

    def action_schedule_followup(self):
        """Planifier une visite de suivi"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Planifier suivi'),
            'res_model': 'apartment.control.visit',
            'view_mode': 'form',
            'context': {
                'default_property_id': self.property_id.id,
                'default_lease_id': self.lease_id.id,
                'default_visit_type': 'routine',
                'default_date': self.followup_date or (date.today() + relativedelta(months=1)),
            },
            'target': 'current',
        }

    def action_create_intervention(self):
        """Créer une intervention suite à la visite"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Créer intervention'),
            'res_model': 'apartment.intervention',
            'view_mode': 'form',
            'context': {
                'default_property_id': self.property_id.id,
                'default_control_visit_id': self.id,
                'default_description': self.anomalies or '',
            },
            'target': 'current',
        }

    def action_view_photos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Photos'),
            'res_model': 'apartment.control.visit.photo',
            'view_mode': 'kanban,list,form',
            'domain': [('visit_id', '=', self.id)],
            'context': {'default_visit_id': self.id},
        }

    @api.model
    def _cron_remind_visits(self):
        """Rappel pour les visites à venir"""
        tomorrow = date.today() + relativedelta(days=1)
        visits = self.search([
            ('state', 'in', ['planned', 'notified']),
            ('date', '=', tomorrow),
        ])
        
        for visit in visits:
            visit.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Visite de contrôle demain'),
                note=_('Visite de contrôle prévue demain pour %s') % visit.property_id.name,
                user_id=visit.conducted_by.id or self.env.user.id,
            )


class ApartmentControlVisitPhoto(models.Model):
    _name = 'apartment.control.visit.photo'
    _description = 'Photo de visite de contrôle'
    _order = 'sequence, create_date'

    visit_id = fields.Many2one(
        'apartment.control.visit',
        string='Visite',
        required=True,
        ondelete='cascade',
    )
    
    name = fields.Char(string='Description', required=True)
    sequence = fields.Integer(default=10)
    
    image = fields.Image(
        string='Photo',
        required=True,
        max_width=1920,
        max_height=1920,
    )
    image_thumbnail = fields.Image(
        string='Miniature',
        related='image',
        max_width=256,
        max_height=256,
        store=True,
    )
    
    # Catégorie
    photo_type = fields.Selection([
        ('general', 'Vue générale'),
        ('anomaly', 'Anomalie'),
        ('damage', 'Dégât'),
        ('maintenance', 'Maintenance'),
        ('other', 'Autre'),
    ], string='Type', default='general')
    
    room_type_id = fields.Many2one(
        'apartment.room.type',
        string='Pièce',
    )
    
    notes = fields.Text(string='Notes')
    is_anomaly = fields.Boolean(string='Montre une anomalie')
