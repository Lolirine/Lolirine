# -*- coding: utf-8 -*-

import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


# États d'abonnement actifs en Odoo 19
# (les états passifs comme 1_draft, 2_renewal, 6_churn, 7_upsell sont exclus)
ACTIVE_SUBSCRIPTION_STATES = ['3_progress', '4_paused', '5_renewed']


class StorageIndexation(models.Model):
    """Modèle principal pour gérer les événements d'indexation"""
    _name = 'storage.indexation'
    _description = 'Indexation des abonnements de stockage'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau')
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('computed', 'Calculé'),
        ('confirmed', 'Confirmé'),
        ('notified', 'Clients notifiés'),
        ('applied', 'Appliqué'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', tracking=True)

    date = fields.Date(
        string="Date d'indexation",
        required=True,
        default=fields.Date.today,
        tracking=True,
        help="Date à laquelle l'indexation prend effet"
    )
    application_date = fields.Date(
        string="Date d'application",
        help="Date effective d'application des nouveaux prix"
    )

    # Indices
    base_index_id = fields.Many2one(
        'storage.price.index',
        string='Indice de base',
        tracking=True,
        help="Indice de référence (généralement celui du contrat initial)"
    )
    new_index_id = fields.Many2one(
        'storage.price.index',
        string='Nouvel indice',
        required=True,
        tracking=True,
        help="Nouvel indice pour le calcul de l'indexation"
    )

    index_type = fields.Selection([
        ('health', 'Indice Santé Belge'),
        ('cpi', 'Indice des Prix à la Consommation (CPI)'),
        ('custom', 'Indice Personnalisé'),
    ], string="Type d'indice", required=True, default='health')

    # Résultats du calcul
    indexation_rate = fields.Float(
        string="Taux d'indexation",
        digits=(16, 2),
        compute='_compute_indexation_rate',
        store=True,
        help="Taux d'indexation calculé entre l'indice de base et le nouvel indice (en pourcentage, ex: 3.38 = 3,38%)",
    )

    # Lignes d'indexation
    line_ids = fields.One2many(
        'storage.indexation.line',
        'indexation_id',
        string="Lignes d'indexation"
    )

    # Statistiques
    subscription_count = fields.Integer(
        string="Nombre d'abonnements",
        compute='_compute_statistics',
        store=True
    )
    total_old_amount = fields.Monetary(
        string='Montant total actuel',
        compute='_compute_statistics',
        store=True,
        currency_field='currency_id'
    )
    total_new_amount = fields.Monetary(
        string='Nouveau montant total',
        compute='_compute_statistics',
        store=True,
        currency_field='currency_id'
    )
    total_increase = fields.Monetary(
        string='Augmentation totale',
        compute='_compute_statistics',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id
    )
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company
    )

    notes = fields.Text(string='Notes internes')
    notification_sent = fields.Boolean(
        string='Notifications envoyées',
        default=False
    )
    notification_date = fields.Datetime(
        string="Date d'envoi des notifications"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'storage.indexation'
                ) or _('Nouveau')
        return super().create(vals_list)

    @api.depends('base_index_id.value', 'new_index_id.value')
    def _compute_indexation_rate(self):
        for record in self:
            if record.base_index_id and record.new_index_id and record.base_index_id.value:
                rate = ((record.new_index_id.value - record.base_index_id.value)
                        / record.base_index_id.value) * 100
                record.indexation_rate = rate
            else:
                record.indexation_rate = 0.0

    @api.depends('line_ids.old_price', 'line_ids.new_price')
    def _compute_statistics(self):
        for record in self:
            lines = record.line_ids
            record.subscription_count = len(lines)
            record.total_old_amount = sum(lines.mapped('old_price'))
            record.total_new_amount = sum(lines.mapped('new_price'))
            record.total_increase = record.total_new_amount - record.total_old_amount

    def action_compute_indexation(self):
        """Calcule l'indexation pour tous les abonnements éligibles.

        Critères de sélection :
        - Abonnement actif (subscription_state dans ACTIVE_SUBSCRIPTION_STATES)
        - Société courante
        - Lignes récurrentes uniquement (pas les frais ponctuels)
        """
        self.ensure_one()

        if not self.new_index_id:
            raise UserError(_("Veuillez sélectionner le nouvel indice avant de calculer"))

        # Supprimer les anciennes lignes
        self.line_ids.unlink()

        Subscription = self.env['sale.order'].sudo()

        # Recherche stricte : seulement les abonnements réellement actifs
        subscriptions = Subscription.search([
            ('is_subscription', '=', True),
            ('subscription_state', 'in', ACTIVE_SUBSCRIPTION_STATES),
            ('company_id', '=', self.company_id.id),
        ])

        _logger.info(
            "Indexation %s : %d abonnement(s) actif(s) trouvé(s) pour société %s",
            self.name, len(subscriptions), self.company_id.name
        )

        lines_data = []
        skipped_no_base = 0
        skipped_no_recurring = 0

        for sub in subscriptions:
            # Vérifier si l'indexation est activée sur l'abonnement
            if hasattr(sub, 'indexation_enabled') and not sub.indexation_enabled:
                continue

            # Récupérer l'indice de base du contrat
            contract_date = sub.date_order.date() if sub.date_order else sub.create_date.date()

            # Utiliser l'indice de base de l'abonnement s'il existe
            if hasattr(sub, 'base_index_id') and sub.base_index_id:
                base_index = sub.base_index_id
            else:
                base_index = self.env['storage.price.index'].get_base_index(
                    contract_date,
                    self.index_type
                )

            if not base_index:
                _logger.warning(
                    "Pas d'indice de base pour l'abonnement %s (date %s)",
                    sub.name, contract_date
                )
                skipped_no_base += 1
                continue

            # Calculer pour chaque ligne récurrente de l'abonnement
            for line in sub.order_line:
                # Détecter si la ligne est récurrente
                is_recurring = self._is_line_recurring(line, sub)

                if not is_recurring:
                    skipped_no_recurring += 1
                    continue

                old_price = line.price_unit

                # Formule belge d'indexation : Nouveau = Ancien × (Nouvel indice / Indice base)
                if base_index.value:
                    new_price = old_price * (self.new_index_id.value / base_index.value)
                    new_price = round(new_price, 2)
                else:
                    new_price = old_price

                lines_data.append({
                    'indexation_id': self.id,
                    'subscription_id': sub.id,
                    'subscription_line_id': line.id,
                    'partner_id': sub.partner_id.id,
                    'product_id': line.product_id.id,
                    'base_index_id': base_index.id,
                    'old_price': old_price,
                    'new_price': new_price,
                    'quantity': line.product_uom_qty,
                })

        # Créer les lignes
        if lines_data:
            self.env['storage.indexation.line'].create(lines_data)

        # Mettre à jour l'indice de base global si non défini
        if not self.base_index_id and lines_data:
            first_base = lines_data[0].get('base_index_id')
            if first_base:
                self.base_index_id = first_base

        self.state = 'computed'

        # Message de résumé enrichi
        msg_parts = [_("%d ligne(s) d'indexation calculée(s)") % len(lines_data)]
        if skipped_no_base:
            msg_parts.append(_("%d abonnement(s) sans indice de base") % skipped_no_base)
        if skipped_no_recurring:
            msg_parts.append(_("%d ligne(s) non récurrente(s) ignorée(s)") % skipped_no_recurring)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Calcul terminé'),
                'message': ' | '.join(msg_parts),
                'type': 'success',
                'sticky': False,
            }
        }

    def _is_line_recurring(self, line, sub):
        """Détermine si une ligne d'abonnement est récurrente (donc indexable).

        En Odoo 19, on s'appuie principalement sur :
        - line.recurring_invoice (sur le produit)
        - le fait que la commande est un abonnement (sub.is_subscription)

        Args:
            line: sale.order.line
            sub: sale.order parent

        Returns:
            bool: True si la ligne est récurrente et indexable
        """
        # Ignorer les lignes section / note
        if line.display_type in ('line_section', 'line_note'):
            return False

        # Pas de produit = ignore
        if not line.product_id:
            return False

        # Champ recurring_invoice sur le produit (standard Odoo subscription)
        if hasattr(line.product_id, 'recurring_invoice'):
            return line.product_id.recurring_invoice

        # Fallback : si l'abonnement est un subscription, considérer comme récurrent
        return sub.is_subscription

    def action_confirm(self):
        """Confirme l'indexation (validation avant application)"""
        self.ensure_one()
        if self.state != 'computed':
            raise UserError(_("L'indexation doit d'abord être calculée"))
        if not self.line_ids:
            raise UserError(_("Aucune ligne d'indexation à confirmer"))

        self.state = 'confirmed'
        return True

    def action_send_notifications(self):
        """Envoie les notifications aux clients"""
        self.ensure_one()
        if self.state not in ('confirmed', 'computed'):
            raise UserError(_(
                "L'indexation doit être confirmée avant l'envoi des notifications"
            ))

        template = self.env.ref(
            'storage_indexation.email_template_indexation_notification',
            raise_if_not_found=False
        )

        if not template:
            raise UserError(_("Template d'email d'indexation non trouvé"))

        partners_notified = set()

        for line in self.line_ids:
            if line.partner_id.id not in partners_notified:
                template.with_context(
                    line=line,
                    indexation=self
                ).send_mail(line.id, force_send=True)

                partners_notified.add(line.partner_id.id)
                line.notification_sent = True
                line.notification_date = fields.Datetime.now()

        self.write({
            'state': 'notified',
            'notification_sent': True,
            'notification_date': fields.Datetime.now(),
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Notifications envoyées'),
                'message': _('%d client(s) notifié(s)') % len(partners_notified),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_apply_indexation(self):
        """Applique l'indexation aux abonnements"""
        self.ensure_one()
        if self.state not in ('confirmed', 'notified'):
            raise UserError(_(
                "L'indexation doit être confirmée ou notifiée avant application"
            ))

        applied_count = 0
        for line in self.line_ids:
            if line.subscription_line_id:
                line.subscription_line_id.sudo().write({
                    'price_unit': line.new_price,
                })
                line.applied = True
                line.application_date = fields.Datetime.now()
                applied_count += 1

        self.write({
            'state': 'applied',
            'application_date': fields.Date.today(),
        })

        # Log dans le chatter
        self.message_post(
            body=_("Indexation appliquée : %d abonnement(s) mis à jour") % applied_count,
            message_type='notification'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Indexation appliquée'),
                'message': _("Les prix ont été mis à jour pour %d ligne(s)") % applied_count,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_cancel(self):
        """Annule l'indexation"""
        self.ensure_one()
        if self.state == 'applied':
            raise UserError(_("Une indexation appliquée ne peut pas être annulée"))
        self.state = 'cancelled'
        return True

    def action_reset_to_draft(self):
        """Remet l'indexation en brouillon"""
        self.ensure_one()
        if self.state == 'applied':
            raise UserError(_(
                "Une indexation appliquée ne peut pas être remise en brouillon"
            ))
        self.line_ids.unlink()
        self.state = 'draft'
        return True

    def action_print_summary(self):
        """Imprime le résumé de l'indexation"""
        self.ensure_one()
        return self.env.ref(
            'storage_indexation.action_report_indexation_summary'
        ).report_action(self)

    @api.model
    def _cron_check_pending_indexations(self):
        """CRON : Vérifie les indexations en attente et envoie des rappels."""
        _logger.info("CRON: Vérification des indexations en attente...")

        # Indexations confirmées mais non appliquées depuis plus de 30 jours
        threshold_date = date.today() - timedelta(days=30)
        pending = self.search([
            ('state', 'in', ('confirmed', 'notified')),
            ('date', '<=', threshold_date),
        ])

        for indexation in pending:
            indexation.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_("Indexation en attente d'application"),
                note=_(
                    "L'indexation %s est en attente depuis plus de 30 jours."
                ) % indexation.name
            )

        return True


class StorageIndexationLine(models.Model):
    """Lignes de détail d'une indexation"""
    _name = 'storage.indexation.line'
    _description = "Ligne d'indexation"
    _order = 'partner_id, id'

    indexation_id = fields.Many2one(
        'storage.indexation',
        string='Indexation',
        required=True,
        ondelete='cascade'
    )

    subscription_id = fields.Many2one(
        'sale.order',
        string='Abonnement',
        required=True
    )
    subscription_line_id = fields.Many2one(
        'sale.order.line',
        string="Ligne d'abonnement"
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Produit/Unité'
    )

    base_index_id = fields.Many2one(
        'storage.price.index',
        string='Indice de base'
    )
    base_index_value = fields.Float(
        related='base_index_id.value',
        string='Valeur indice base'
    )
    new_index_value = fields.Float(
        related='indexation_id.new_index_id.value',
        string='Valeur nouvel indice'
    )

    old_price = fields.Monetary(
        string='Ancien prix',
        currency_field='currency_id'
    )
    new_price = fields.Monetary(
        string='Nouveau prix',
        currency_field='currency_id'
    )
    price_increase = fields.Monetary(
        string='Augmentation',
        compute='_compute_price_increase',
        store=True,
        currency_field='currency_id'
    )
    increase_percentage = fields.Float(
        string='% Augmentation',
        compute='_compute_price_increase',
        store=True,
        digits=(5, 2)
    )

    quantity = fields.Float(
        string='Quantité',
        default=1.0
    )
    total_old = fields.Monetary(
        string='Total ancien',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    total_new = fields.Monetary(
        string='Total nouveau',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        related='indexation_id.currency_id'
    )

    applied = fields.Boolean(
        string='Appliqué',
        default=False
    )
    application_date = fields.Datetime(string="Date d'application")

    notification_sent = fields.Boolean(
        string='Notification envoyée',
        default=False
    )
    notification_date = fields.Datetime(string='Date notification')

    notes = fields.Text(string='Notes')

    @api.depends('old_price', 'new_price')
    def _compute_price_increase(self):
        for line in self:
            line.price_increase = line.new_price - line.old_price
            if line.old_price:
                line.increase_percentage = (
                    (line.new_price - line.old_price) / line.old_price
                ) * 100
            else:
                line.increase_percentage = 0.0

    @api.depends('old_price', 'new_price', 'quantity')
    def _compute_totals(self):
        for line in self:
            line.total_old = line.old_price * line.quantity
            line.total_new = line.new_price * line.quantity

    def action_view_subscription(self):
        """Ouvre la vue de l'abonnement"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_send_individual_notification(self):
        """Envoie une notification individuelle"""
        self.ensure_one()
        template = self.env.ref(
            'storage_indexation.email_template_indexation_notification',
            raise_if_not_found=False
        )

        if template:
            template.send_mail(self.id, force_send=True)
            self.write({
                'notification_sent': True,
                'notification_date': fields.Datetime.now(),
            })

        return True
