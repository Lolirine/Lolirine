# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # =============================================
    # CHAMPS ENVOI AUTOMATIQUE
    # =============================================
    
    auto_send_invoice = fields.Boolean(
        string="Envoi Email automatique",
        default=False,
        help="Si coché, la facture sera envoyée automatiquement par email à la date de facturation"
    )
    
    auto_send_peppol = fields.Boolean(
        string="Envoi Peppol automatique",
        default=False,
        help="Si coché, la facture sera envoyée automatiquement via Peppol après confirmation"
    )
    
    peppol_sent = fields.Boolean(
        string="Envoyée via Peppol",
        default=False,
        copy=False,
    )
    
    peppol_sent_date = fields.Datetime(
        string="Date envoi Peppol",
        copy=False
    )

    # =============================================
    # CHAMPS ENVOI DIFFÉRÉ
    # =============================================
    
    email_scheduled_date = fields.Date(
        string="Date d'envoi email prévue",
        copy=False,
        help="Date à laquelle l'email sera envoyé automatiquement. Par défaut = date de facturation."
    )
    
    email_pending = fields.Boolean(
        string="Email en attente",
        default=False,
        copy=False,
        help="Facture en attente d'envoi automatique (le cron l'enverra à la date prévue)"
    )
    
    email_sent_date = fields.Datetime(
        string="Date envoi email",
        copy=False,
        readonly=True
    )

    # =============================================
    # CHAMPS TAGS ET NOTES
    # =============================================
    
    invoice_tag_ids = fields.Many2many(
        'lolirine.invoice.tag',
        string="Tags",
        help="Tags pour catégoriser les factures"
    )
    
    internal_note = fields.Text(
        string="Note interne",
        help="Note visible uniquement en interne"
    )
    
    internal_note_important = fields.Boolean(
        string="Note importante",
        default=False
    )

    # =============================================
    # CHAMPS RELANCES
    # =============================================
    
    reminder_ids = fields.One2many(
        'lolirine.invoice.reminder',
        'invoice_id',
        string="Relances"
    )
    
    reminder_count = fields.Integer(
        string="Nombre de relances",
        compute='_compute_reminder_count'
    )
    
    last_reminder_date = fields.Date(
        string="Dernière relance",
        compute='_compute_reminder_info',
        store=True
    )
    
    last_reminder_type = fields.Selection(
        selection=[
            ('email', 'Email'),
            ('sms', 'SMS'),
            ('phone', 'Téléphone'),
            ('mail', 'Courrier'),
        ],
        string="Type dernière relance",
        compute='_compute_reminder_info',
        store=True
    )
    
    next_reminder_date = fields.Date(
        string="Prochaine relance",
        compute='_compute_next_reminder'
    )

    # =============================================
    # CHAMPS RETARD ET PÉNALITÉS
    # =============================================
    
    days_until_due = fields.Integer(
        string="Jours avant échéance",
        compute='_compute_overdue_info'
    )
    
    days_overdue = fields.Integer(
        string="Jours de retard",
        compute='_compute_overdue_info'
    )
    
    is_overdue = fields.Boolean(
        string="En retard",
        compute='_compute_overdue_info',
        store=True
    )
    
    overdue_level = fields.Selection(
        selection=[
            ('ok', 'OK'),
            ('warning', 'Attention'),
            ('danger', 'Urgent'),
            ('critical', 'Critique'),
        ],
        string="Niveau de retard",
        compute='_compute_overdue_info'
    )
    
    penalty_rate = fields.Float(
        string="Taux de pénalité (%)",
        default=10.0
    )
    
    penalty_amount = fields.Monetary(
        string="Montant pénalités",
        compute='_compute_penalty'
    )
    
    total_with_penalty = fields.Monetary(
        string="Total avec pénalités",
        compute='_compute_penalty'
    )

    # =============================================
    # CHAMPS STATISTIQUES CLIENT
    # =============================================
    
    partner_invoice_count = fields.Integer(
        string="Factures du client",
        compute='_compute_partner_stats'
    )
    
    partner_unpaid_count = fields.Integer(
        string="Impayées du client",
        compute='_compute_partner_stats'
    )

    # =============================================
    # OVERRIDE ACTION_POST - ENVOI DIFFÉRÉ
    # =============================================
    
    def action_post(self):
        """
