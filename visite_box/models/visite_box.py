# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import base64


class VisiteBox(models.Model):
    _name = 'visite.box'
    _description = 'Visite de box / Parcours client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_visite desc, id desc'
    _rec_name = 'display_name'

    # =====================
    # Champs principaux
    # =====================
    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau')
    )
    display_name = fields.Char(
        string='Nom affiché',
        compute='_compute_display_name',
        store=True
    )
    
    # Relation avec le client
    partner_id = fields.Many2one(
        'res.partner',
        string='Client / Prospect',
        required=True,
        tracking=True,
        index=True
    )
    partner_phone = fields.Char(
        related='partner_id.phone',
        string='Téléphone',
        readonly=False
    )
    partner_mobile = fields.Char(
        related='partner_id.mobile',
        string='Mobile',
        readonly=False
    )
    partner_email = fields.Char(
        related='partner_id.email',
        string='Email',
        readonly=False
    )
    
    # Box intéressantes
    box_ids = fields.Many2many(
        'storage.box',
        'visite_box_storage_box_rel',
        'visite_id',
        'box_id',
        string='Box intéressantes'
    )
    box_selected_id = fields.Many2one(
        'storage.box',
        string='Box choisie',
        domain="[('id', 'in', box_ids)]",
        tracking=True
    )
    
    # =====================
    # Planification
    # =====================
    date_visite = fields.Datetime(
        string='Date et heure de visite',
        required=True,
        tracking=True,
        default=fields.Datetime.now
    )
    date_visite_fin = fields.Datetime(
        string='Fin de visite',
        compute='_compute_date_visite_fin',
        store=True
    )
    duree_visite = fields.Float(
        string='Durée (heures)',
        default=0.5,
        help='Durée estimée de la visite en heures'
    )
    creneau_id = fields.Many2one(
        'visite.creneau',
        string='Créneau horaire',
        help='Créneau horaire prédéfini'
    )
    user_id = fields.Many2one(
        'res.users',
        string='Commercial assigné',
        default=lambda self: self.env.user,
        tracking=True
    )
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Événement calendrier',
        readonly=True,
        copy=False
    )
    
    # =====================
    # Statut et pipeline
    # =====================
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('scheduled', 'Planifiée'),
        ('confirmed', 'Confirmée'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée'),
        ('converted', 'Convertie'),
        ('cancelled', 'Annulée'),
    ], string='État', default='draft', tracking=True, group_expand='_group_expand_states')
    
    kanban_state = fields.Selection([
        ('normal', 'Normal'),
        ('blocked', 'Bloqué'),
        ('done', 'Prêt')
    ], string='État Kanban', default='normal')
    
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Faible'),
        ('2', 'Élevée'),
        ('3', 'Très élevée')
    ], string='Priorité', default='0')
    
    # =====================
    # Check-list de visite
    # =====================
    checklist_ids = fields.One2many(
        'visite.checklist.line',
        'visite_id',
        string='Check-list'
    )
    checklist_progress = fields.Float(
        string='Progression check-list',
        compute='_compute_checklist_progress',
        store=True
    )
    
    # =====================
    # Besoins du client
    # =====================
    besoin_description = fields.Text(
        string='Description du besoin',
        help='Décrivez le besoin du client'
    )
    volume_estime = fields.Float(
        string='Volume estimé (m³)',
        help='Volume de stockage estimé en mètres cubes'
    )
    surface_estimee = fields.Float(
        string='Surface estimée (m²)',
        compute='_compute_surface_estimee',
        store=True,
        readonly=False
    )
    duree_prevue = fields.Selection([
        ('1', '1 mois'),
        ('3', '3 mois'),
        ('6', '6 mois'),
        ('12', '1 an'),
        ('24', '2 ans'),
        ('indefini', 'Indéterminée'),
    ], string='Durée de stockage prévue', default='6')
    
    type_stockage = fields.Selection([
        ('particulier', 'Particulier'),
        ('professionnel', 'Professionnel'),
        ('demenagement', 'Déménagement'),
        ('travaux', 'Travaux'),
        ('succession', 'Succession'),
        ('autre', 'Autre'),
    ], string='Type de stockage', default='particulier')
    
    objets_sensibles = fields.Boolean(
        string='Objets sensibles',
        help='Meubles fragiles, électronique, documents...'
    )
    objets_sensibles_detail = fields.Text(
        string='Détail objets sensibles'
    )
    acces_frequence = fields.Selection([
        ('rare', 'Rare (moins d\'1 fois/mois)'),
        ('mensuel', 'Mensuel'),
        ('hebdo', 'Hebdomadaire'),
        ('quotidien', 'Quotidien'),
    ], string='Fréquence d\'accès souhaitée', default='mensuel')
    
    # =====================
    # Objections et notes
    # =====================
    objection_ids = fields.Many2many(
        'visite.objection',
        string='Objections relevées'
    )
    objection_notes = fields.Text(
        string='Notes sur les objections'
    )
    notes_internes = fields.Text(
        string='Notes internes'
    )
    notes_client = fields.Text(
        string='Notes pour le client'
    )
    
    # =====================
    # Signature électronique
    # =====================
    signature = fields.Binary(
        string='Signature du client',
        attachment=True
    )
    signature_date = fields.Datetime(
        string='Date de signature'
    )
    consent_rgpd = fields.Boolean(
        string='Consentement RGPD',
        help='Le client consent au traitement de ses données'
    )
    consent_marketing = fields.Boolean(
        string='Consentement marketing',
        help='Le client accepte de recevoir des communications marketing'
    )
    
    # =====================
    # Conversion
    # =====================
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Devis/Commande',
        readonly=True,
        copy=False
    )
    subscription_id = fields.Many2one(
        'sale.order',
        string='Abonnement',
        readonly=True,
        copy=False,
        domain="[('is_subscription', '=', True)]"
    )
    
    # =====================
    # Rappels
    # =====================
    rappel_envoye = fields.Boolean(
        string='Rappel envoyé',
        default=False,
        copy=False
    )
    confirmation_envoyee = fields.Boolean(
        string='Confirmation envoyée',
        default=False,
        copy=False
    )
    
    # =====================
    # Source et origine
    # =====================
    source_id = fields.Many2one(
        'utm.source',
        string='Source'
    )
    medium_id = fields.Many2one(
        'utm.medium',
        string='Medium'
    )
    campaign_id = fields.Many2one(
        'utm.campaign',
        string='Campagne'
    )
    
    # =====================
    # Computed fields
    # =====================
    @api.depends('name', 'partner_id.name', 'date_visite')
    def _compute_display_name(self):
        for record in self:
            if record.partner_id and record.date_visite:
                date_str = fields.Datetime.context_timestamp(
                    record, record.date_visite
                ).strftime('%d/%m/%Y %H:%M')
                record.display_name = f"{record.name} - {record.partner_id.name} ({date_str})"
            else:
                record.display_name = record.name
    
    @api.depends('date_visite', 'duree_visite')
    def _compute_date_visite_fin(self):
        for record in self:
            if record.date_visite and record.duree_visite:
                record.date_visite_fin = record.date_visite + timedelta(hours=record.duree_visite)
            else:
                record.date_visite_fin = record.date_visite
    
    @api.depends('checklist_ids', 'checklist_ids.is_done')
    def _compute_checklist_progress(self):
        for record in self:
            if record.checklist_ids:
                done = len(record.checklist_ids.filtered('is_done'))
                total = len(record.checklist_ids)
                record.checklist_progress = (done / total) * 100 if total else 0
            else:
                record.checklist_progress = 0
    
    @api.depends('volume_estime')
    def _compute_surface_estimee(self):
        for record in self:
            # Estimation: hauteur moyenne de 2.5m
            if record.volume_estime:
                record.surface_estimee = record.volume_estime / 2.5
            else:
                record.surface_estimee = 0
    
    def _group_expand_states(self, states, domain, order):
        """Affiche tous les états dans la vue Kanban"""
        return [key for key, val in type(self).state.selection]
    
    # =====================
    # CRUD overrides
    # =====================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('visite.box') or _('Nouveau')
        records = super().create(vals_list)
        # Créer la check-list par défaut
        records._create_default_checklist()
        return records
    
    def write(self, vals):
        res = super().write(vals)
        # Si la date change, mettre à jour l'événement calendrier
        if 'date_visite' in vals or 'duree_visite' in vals:
            for record in self:
                if record.calendar_event_id:
                    record.calendar_event_id.write({
                        'start': record.date_visite,
                        'stop': record.date_visite_fin,
                    })
        return res
    
    # =====================
    # Actions de workflow
    # =====================
    def action_schedule(self):
        """Planifier la visite"""
        for record in self:
            if not record.date_visite:
                raise UserError(_("Veuillez définir une date de visite."))
            record.state = 'scheduled'
            record._create_calendar_event()
            record._send_confirmation()
    
    def action_confirm(self):
        """Confirmer la visite"""
        self.write({'state': 'confirmed'})
    
    def action_start(self):
        """Démarrer la visite"""
        self.write({'state': 'in_progress'})
    
    def action_done(self):
        """Terminer la visite"""
        for record in self:
            if not record.signature and record.consent_rgpd:
                raise UserError(_("La signature du client est requise pour valider la visite."))
            record.state = 'done'
    
    def action_cancel(self):
        """Annuler la visite"""
        for record in self:
            if record.calendar_event_id:
                record.calendar_event_id.unlink()
            record.state = 'cancelled'
    
    def action_reset_draft(self):
        """Remettre en brouillon"""
        self.write({
            'state': 'draft',
            'rappel_envoye': False,
            'confirmation_envoyee': False,
        })
    
    # =====================
    # Actions métier
    # =====================
    def action_convert_to_quotation(self):
        """Ouvrir le wizard de conversion en devis"""
        self.ensure_one()
        if self.state not in ('done', 'in_progress'):
            raise UserError(_("La visite doit être terminée ou en cours pour être convertie."))
        
        return {
            'name': _('Convertir en devis'),
            'type': 'ir.actions.act_window',
            'res_model': 'visite.to.quotation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_visite_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_box_id': self.box_selected_id.id or (self.box_ids[0].id if self.box_ids else False),
                'default_duree_prevue': self.duree_prevue,
            }
        }
    
    def action_view_quotation(self):
        """Voir le devis associé"""
        self.ensure_one()
        if self.sale_order_id:
            return {
                'name': _('Devis'),
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': self.sale_order_id.id,
            }
    
    def action_send_reminder(self):
        """Envoyer un rappel manuellement"""
        self.ensure_one()
        template = self.env.ref('visite_box.mail_template_visite_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.rappel_envoye = True
            self.message_post(body=_("Rappel de visite envoyé au client."))
    
    def action_send_sms_reminder(self):
        """Envoyer un rappel SMS"""
        self.ensure_one()
        if not self.partner_mobile:
            raise UserError(_("Le client n'a pas de numéro de mobile."))
        
        body = _(
            "Rappel: Votre visite chez Lolirine est prévue le %(date)s. "
            "À bientôt!"
        ) % {'date': fields.Datetime.context_timestamp(self, self.date_visite).strftime('%d/%m/%Y à %H:%M')}
        
        self.env['sms.sms'].create({
            'number': self.partner_mobile,
            'body': body,
        }).send()
        
        self.message_post(body=_("Rappel SMS envoyé au client."))
    
    def action_sign(self):
        """Action pour ouvrir la vue de signature"""
        self.ensure_one()
        return {
            'name': _('Signature client'),
            'type': 'ir.actions.act_window',
            'res_model': 'visite.box',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'views': [(self.env.ref('visite_box.visite_box_view_form_signature').id, 'form')],
        }
    
    def action_save_signature(self):
        """Sauvegarder la signature et les consentements"""
        self.ensure_one()
        if self.signature:
            self.signature_date = fields.Datetime.now()
            self.message_post(body=_("Fiche de visite signée par le client."))
        return {'type': 'ir.actions.act_window_close'}
    
    # =====================
    # Méthodes privées
    # =====================
    def _create_default_checklist(self):
        """Créer la check-list par défaut pour les nouvelles visites"""
        checklist_template = self.env['visite.checklist.template'].search([], limit=1)
        if checklist_template:
            for record in self:
                for item in checklist_template.item_ids:
                    self.env['visite.checklist.line'].create({
                        'visite_id': record.id,
                        'name': item.name,
                        'sequence': item.sequence,
                        'is_required': item.is_required,
                    })
    
    def _create_calendar_event(self):
        """Créer un événement dans le calendrier"""
        self.ensure_one()
        if self.calendar_event_id:
            return
        
        event = self.env['calendar.event'].create({
            'name': f"Visite - {self.partner_id.name}",
            'start': self.date_visite,
            'stop': self.date_visite_fin,
            'user_id': self.user_id.id,
            'partner_ids': [(4, self.partner_id.id), (4, self.user_id.partner_id.id)],
            'description': f"""
Visite planifiée pour: {self.partner_id.name}
Téléphone: {self.partner_phone or 'N/A'}
Mobile: {self.partner_mobile or 'N/A'}
Besoin: {self.besoin_description or 'Non spécifié'}
Volume estimé: {self.volume_estime} m³
            """.strip(),
        })
        self.calendar_event_id = event.id
    
    def _send_confirmation(self):
        """Envoyer l'email de confirmation"""
        template = self.env.ref('visite_box.mail_template_visite_confirmation', raise_if_not_found=False)
        if template and not self.confirmation_envoyee:
            template.send_mail(self.id, force_send=True)
            self.confirmation_envoyee = True
            self.message_post(body=_("Email de confirmation envoyé au client."))
    
    @api.model
    def _cron_send_reminders(self):
        """Envoi automatique des rappels 24h avant la visite"""
        tomorrow_start = datetime.now() + timedelta(days=1)
        tomorrow_end = tomorrow_start + timedelta(hours=24)
        
        visites = self.search([
            ('state', 'in', ['scheduled', 'confirmed']),
            ('date_visite', '>=', tomorrow_start),
            ('date_visite', '<=', tomorrow_end),
            ('rappel_envoye', '=', False),
        ])
        
        template = self.env.ref('visite_box.mail_template_visite_reminder', raise_if_not_found=False)
        for visite in visites:
            if template:
                template.send_mail(visite.id, force_send=True)
            visite.rappel_envoye = True
            visite.message_post(body=_("Rappel automatique envoyé au client."))


class VisiteObjection(models.Model):
    """Objections fréquentes lors des visites"""
    _name = 'visite.objection'
    _description = 'Objection de visite'
    _order = 'sequence, id'

    name = fields.Char(string='Objection', required=True)
    sequence = fields.Integer(string='Séquence', default=10)
    reponse_suggeree = fields.Text(string='Réponse suggérée')
    active = fields.Boolean(default=True)
