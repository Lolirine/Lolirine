# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class ApartmentTenant(models.Model):
    _name = 'apartment.tenant'
    _description = 'Locataire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'res.partner': 'partner_id'}
    _order = 'name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partenaire',
        required=True,
        ondelete='cascade',
    )
    reference = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default=lambda self: _('Nouveau'),
    )
    active = fields.Boolean(default=True)

    # Informations personnelles
    birth_date = fields.Date(string='Date de naissance (locataire)')
    birth_place = fields.Char(string='Lieu de naissance (locataire)')
    nationality_id = fields.Many2one('res.country', string='Nationalité')
    national_id = fields.Char(string='N° registre national')
    id_card_number = fields.Char(string='N° carte d\'identité')
    id_card_expiry = fields.Date(string='Expiration carte d\'identité')

    # Situation professionnelle
    profession = fields.Char(string='Profession')
    employer = fields.Char(string='Employeur')
    monthly_income = fields.Float(string='Revenu mensuel net')
    employment_type = fields.Selection([
        ('cdi', 'CDI'),
        ('cdd', 'CDD'),
        ('interim', 'Intérim'),
        ('independent', 'Indépendant'),
        ('retired', 'Retraité'),
        ('student', 'Étudiant'),
        ('unemployed', 'Sans emploi'),
        ('other', 'Autre'),
    ], string='Type de contrat')

    # Contact d'urgence
    emergency_contact_name = fields.Char(string='Contact d\'urgence')
    emergency_contact_phone = fields.Char(string='Tél. contact d\'urgence')
    emergency_contact_relation = fields.Char(string='Relation')

    # Garant
    guarantor_name = fields.Char(string='Nom du garant')
    guarantor_address = fields.Text(string='Adresse du garant')
    guarantor_phone = fields.Char(string='Tél. garant')
    guarantor_email = fields.Char(string='Email garant')

    # Compte bancaire
    bank_account = fields.Char(string='IBAN')
    bank_name = fields.Char(string='Banque')

    # Relations
    lease_ids = fields.One2many(
        'apartment.lease',
        'tenant_id',
        string='Baux',
    )
    current_lease_id = fields.Many2one(
        'apartment.lease',
        string='Bail en cours',
        compute='_compute_current_lease',
        store=True,
    )
    document_ids = fields.One2many(
        'apartment.document',
        'tenant_id',
        string='Documents',
    )

    # Compteurs
    lease_count = fields.Integer(
        string='Nombre de baux',
        compute='_compute_lease_count',
    )
    document_count = fields.Integer(
        string='Nombre de documents',
        compute='_compute_document_count',
    )

    # Notes
    notes = fields.Text(string='Notes locataire')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('apartment.tenant') or _('Nouveau')
        return super().create(vals_list)

    @api.depends('lease_ids', 'lease_ids.state')
    def _compute_current_lease(self):
        for record in self:
            current = record.lease_ids.filtered(lambda l: l.state == 'active')
            record.current_lease_id = current[:1] if current else False

    def _compute_lease_count(self):
        for record in self:
            record.lease_count = len(record.lease_ids)

    def _compute_document_count(self):
        for record in self:
            record.document_count = len(record.document_ids)

    @api.constrains('national_id')
    def _check_national_id(self):
        for record in self:
            if record.national_id:
                # Vérification basique du numéro de registre national belge
                cleaned = record.national_id.replace('.', '').replace('-', '').replace(' ', '')
                if len(cleaned) != 11 or not cleaned.isdigit():
                    raise ValidationError(_('Le numéro de registre national doit contenir 11 chiffres.'))

    def action_view_leases(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Baux'),
            'res_model': 'apartment.lease',
            'view_mode': 'list,form',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id},
        }

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents'),
            'res_model': 'apartment.document',
            'view_mode': 'list,form',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id},
        }
