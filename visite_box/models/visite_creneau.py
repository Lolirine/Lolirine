# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VisiteCreneau(models.Model):
    """Créneaux horaires disponibles pour les visites"""
    _name = 'visite.creneau'
    _description = 'Créneau horaire de visite'
    _order = 'jour_semaine, heure_debut'

    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True
    )
    jour_semaine = fields.Selection([
        ('0', 'Lundi'),
        ('1', 'Mardi'),
        ('2', 'Mercredi'),
        ('3', 'Jeudi'),
        ('4', 'Vendredi'),
        ('5', 'Samedi'),
        ('6', 'Dimanche'),
    ], string='Jour', required=True)
    heure_debut = fields.Float(
        string='Heure de début',
        required=True,
        help='Format: 9.5 = 9h30'
    )
    heure_fin = fields.Float(
        string='Heure de fin',
        required=True,
        help='Format: 17.0 = 17h00'
    )
    duree = fields.Float(
        string='Durée (heures)',
        compute='_compute_duree',
        store=True
    )
    max_visites = fields.Integer(
        string='Max visites simultanées',
        default=1,
        help='Nombre maximum de visites pouvant être planifiées sur ce créneau'
    )
    user_id = fields.Many2one(
        'res.users',
        string='Commercial assigné',
        help='Laisser vide pour tous les commerciaux'
    )
    active = fields.Boolean(default=True)
    
    # Compteur de visites
    visite_count = fields.Integer(
        string='Nombre de visites',
        compute='_compute_visite_count'
    )

    @api.depends('jour_semaine', 'heure_debut', 'heure_fin')
    def _compute_name(self):
        jours = dict(self._fields['jour_semaine'].selection)
        for record in self:
            if record.jour_semaine:
                jour = jours.get(record.jour_semaine, '')
                h_debut = self._float_to_time(record.heure_debut)
                h_fin = self._float_to_time(record.heure_fin)
                record.name = f"{jour} {h_debut} - {h_fin}"
            else:
                record.name = "Nouveau créneau"

    @api.depends('heure_debut', 'heure_fin')
    def _compute_duree(self):
        for record in self:
            record.duree = record.heure_fin - record.heure_debut

    def _compute_visite_count(self):
        for record in self:
            record.visite_count = self.env['visite.box'].search_count([
                ('creneau_id', '=', record.id),
                ('state', 'not in', ['cancelled', 'converted']),
            ])

    @api.constrains('heure_debut', 'heure_fin')
    def _check_heures(self):
        for record in self:
            if record.heure_debut >= record.heure_fin:
                raise ValidationError(_("L'heure de fin doit être supérieure à l'heure de début."))
            if record.heure_debut < 0 or record.heure_debut > 24:
                raise ValidationError(_("L'heure de début doit être comprise entre 0 et 24."))
            if record.heure_fin < 0 or record.heure_fin > 24:
                raise ValidationError(_("L'heure de fin doit être comprise entre 0 et 24."))

    @staticmethod
    def _float_to_time(float_time):
        """Convertit un float en format horaire HH:MM"""
        hours = int(float_time)
        minutes = int((float_time - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    def action_view_visites(self):
        """Voir les visites de ce créneau"""
        self.ensure_one()
        return {
            'name': _('Visites'),
            'type': 'ir.actions.act_window',
            'res_model': 'visite.box',
            'view_mode': 'tree,form',
            'domain': [('creneau_id', '=', self.id)],
            'context': {'default_creneau_id': self.id},
        }
