# -*- coding: utf-8 -*-
from odoo import api, fields, models

DEFAULT_ALERT_DAYS = 10


class AccountMove(models.Model):
    _inherit = 'account.move'

    lolirine_relance_alert = fields.Boolean(
        string="Relance incoherente",
        default=False,
        copy=False,
        index=True,
        help="Cochee automatiquement lorsque la facture est echue depuis "
             "plusieurs jours sans suivi de relance coherent.",
    )
    lolirine_relance_msg = fields.Char(
        string="Motif d'alerte",
        copy=False,
        help="Liste des anomalies detectees par la surveillance des relances.",
    )

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    def _lolirine_relance_eligible(self):
        """Facture client postee, non soldee et echue."""
        self.ensure_one()
        return (
            self.move_type == 'out_invoice'
            and self.state == 'posted'
            and self.payment_state not in ('paid', 'in_payment', 'reversed')
            and self.amount_residual > 0
            and bool(self.invoice_date_due)
        )

    def _lolirine_last_followup_date(self):
        """Date du dernier courrier de relance envoye au client."""
        self.ensure_one()
        if not self.partner_id:
            return False
        msg = self.env['mail.message'].search([
            ('model', '=', 'res.partner'),
            ('res_id', '=', self.partner_id.id),
            ('message_type', '=', 'notification'),
            '|', ('subject', 'ilike', 'appel'),
                 ('subject', 'ilike', 'demeure'),
        ], order='date desc', limit=1)
        return msg.date.date() if msg and msg.date else False

    def _lolirine_check_relance(self):
        """Recalcule le drapeau d'alerte sur les factures du recordset."""
        ICP = self.env['ir.config_parameter'].sudo()
        try:
            seuil = int(ICP.get_param('lolirine_relance.alert_days',
                                      DEFAULT_ALERT_DAYS))
        except (TypeError, ValueError):
            seuil = DEFAULT_ALERT_DAYS
        today = fields.Date.today()
        SO = self.env['sale.order']

        for mv in self:
            motifs = []
            if mv._lolirine_relance_eligible():
                retard = (today - mv.invoice_date_due).days
                if retard > seuil:

                    last = mv._lolirine_last_followup_date()
                    if not last or last < mv.invoice_date_due:
                        motifs.append(
                            "aucune relance depuis l'echeance (%s j de retard)" % retard)

                    if mv.partner_id.followup_reminder_type == 'manual':
                        motifs.append("suivi client en manuel")

                    if SO.search_count([
                        ('partner_id', '=', mv.partner_id.id),
                        ('subscription_state', '=', '3_progress'),
                    ]):
                        motifs.append("abonnement encore actif")

                    if any('frais de relance' in (line.name or '').lower()
                           for line in mv.invoice_line_ids):
                        motifs.append("facture de frais impayee")

            mv.lolirine_relance_alert = bool(motifs)
            mv.lolirine_relance_msg = " / ".join(motifs) if motifs else False

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_lolirine_relance_watchdog(self):
        """Passage quotidien : recalcule toutes les factures ouvertes."""
        moves = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ('paid', 'in_payment', 'reversed')),
        ])
        moves._lolirine_check_relance()

        # Les factures soldees entre-temps ne doivent plus porter d'alerte
        obsoletes = self.search([
            ('lolirine_relance_alert', '=', True),
            ('id', 'not in', moves.ids),
        ])
        if obsoletes:
            obsoletes.write({
                'lolirine_relance_alert': False,
                'lolirine_relance_msg': False,
            })
        return True

    # ------------------------------------------------------------------
    # Action manuelle
    # ------------------------------------------------------------------
    def action_lolirine_check_relance(self):
        """Bouton / action serveur : recalcul immediat sur la selection."""
        self._lolirine_check_relance()
        return True
