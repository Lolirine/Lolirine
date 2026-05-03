# -*- coding: utf-8 -*-
"""Wizard de prévisualisation et envoi des notifications d'indexation.

Ce wizard remplace le mécanisme d'envoi inline existant pour offrir :
- Un aperçu HTML de l'email avant envoi
- Le choix du destinataire de prévisualisation (test sur soi-même possible)
- L'attachement automatique du PDF si le client est une société
- L'envoi groupé avec tracking par ligne d'indexation
"""

import logging
from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LolirineIndexationSendWizard(models.TransientModel):
    """Wizard pour prévisualiser et envoyer les notifications d'indexation."""
    _name = 'lolirine.indexation.send.wizard'
    _description = "Envoi groupé des notifications d'indexation"

    # ========================================================================
    # CONTEXTE
    # ========================================================================

    indexation_id = fields.Many2one(
        'storage.indexation',
        string="Indexation",
        required=True,
        readonly=True,
        default=lambda self: self.env.context.get('active_id')
    )

    # ========================================================================
    # OPTIONS D'ENVOI
    # ========================================================================

    attach_pdf_for_companies = fields.Boolean(
        string="Joindre PDF pour les sociétés",
        default=True,
        help="Si coché : les clients de type 'Société' recevront le PDF "
             "officiel d'indexation en plus de l'email. Les particuliers "
             "ne reçoivent que l'email."
    )

    test_mode = fields.Boolean(
        string="Mode test",
        default=False,
        help="Si coché : tous les emails seront envoyés à l'adresse de test "
             "ci-dessous au lieu des vrais destinataires."
    )

    test_email = fields.Char(
        string="Email de test",
        default=lambda self: self.env.user.email or '',
        help="Adresse à utiliser en mode test"
    )

    # ========================================================================
    # PRÉVISUALISATION
    # ========================================================================

    preview_line_id = fields.Many2one(
        'storage.indexation.line',
        string="Aperçu pour",
        domain="[('indexation_id', '=', indexation_id)]",
        help="Choisir une ligne d'indexation pour voir le rendu de l'email"
    )

    preview_html = fields.Html(
        string="Aperçu de l'email",
        compute='_compute_preview_html',
        sanitize=False
    )

    preview_will_attach_pdf = fields.Boolean(
        string="PDF sera joint",
        compute='_compute_preview_html'
    )

    # ========================================================================
    # SYNTHÈSE
    # ========================================================================

    total_lines = fields.Integer(
        string="Total lignes",
        compute='_compute_stats'
    )
    total_companies = fields.Integer(
        string="Sociétés (PDF + email)",
        compute='_compute_stats'
    )
    total_individuals = fields.Integer(
        string="Particuliers (email seul)",
        compute='_compute_stats'
    )
    total_no_email = fields.Integer(
        string="🚨 Sans email",
        compute='_compute_stats'
    )
    total_already_sent = fields.Integer(
        string="Déjà notifiés",
        compute='_compute_stats'
    )

    # ========================================================================
    # COMPUTES
    # ========================================================================

    @api.depends('indexation_id.line_ids',
                 'indexation_id.line_ids.partner_id',
                 'indexation_id.line_ids.notification_sent')
    def _compute_stats(self):
        for wiz in self:
            lines = wiz.indexation_id.line_ids
            wiz.total_lines = len(lines)
            wiz.total_companies = len(
                lines.filtered(lambda l: l.partner_id.is_company)
            )
            wiz.total_individuals = len(
                lines.filtered(lambda l: not l.partner_id.is_company)
            )
            wiz.total_no_email = len(
                lines.filtered(lambda l: not l.partner_id.email)
            )
            wiz.total_already_sent = len(
                lines.filtered('notification_sent')
            )

    @api.depends('preview_line_id', 'attach_pdf_for_companies')
    def _compute_preview_html(self):
        for wiz in self:
            if not wiz.preview_line_id:
                wiz.preview_html = (
                    "<p style='color: #888; font-style: italic; padding: 20px;'>"
                    "Sélectionnez une ligne d'indexation ci-dessus pour voir "
                    "l'aperçu de l'email."
                    "</p>"
                )
                wiz.preview_will_attach_pdf = False
                continue

            template = wiz._get_email_template()
            if not template:
                wiz.preview_html = (
                    "<p style='color: red;'>Template d'email introuvable. "
                    "Vérifie l'installation du module storage_indexation.</p>"
                )
                wiz.preview_will_attach_pdf = False
                continue

            # Render le body du template pour la ligne sélectionnée
            try:
                body = template._render_field(
                    'body_html', wiz.preview_line_id.ids,
                    compute_lang=True
                )[wiz.preview_line_id.id]
                subject = template._render_field(
                    'subject', wiz.preview_line_id.ids
                )[wiz.preview_line_id.id]
                email_from = template._render_field(
                    'email_from', wiz.preview_line_id.ids
                )[wiz.preview_line_id.id]
            except Exception as e:
                _logger.exception("Erreur rendu template")
                wiz.preview_html = (
                    f"<p style='color: red;'>Erreur de rendu : {e}</p>"
                )
                wiz.preview_will_attach_pdf = False
                continue

            # Décide si PDF joint
            will_attach = (
                wiz.attach_pdf_for_companies
                and wiz.preview_line_id.partner_id.is_company
            )
            wiz.preview_will_attach_pdf = will_attach

            # Encadre l'aperçu avec un en-tête métadonnées
            destinataire = (
                wiz.preview_line_id.partner_id.email or '(aucun email)'
            )
            type_client = (
                "Société" if wiz.preview_line_id.partner_id.is_company
                else "Particulier"
            )
            badge_pdf = (
                "<span style='background: #28a745; color: white; padding: 2px 8px; "
                "border-radius: 3px; font-size: 11px;'>PDF JOINT</span>"
                if will_attach else
                "<span style='background: #6c757d; color: white; padding: 2px 8px; "
                "border-radius: 3px; font-size: 11px;'>EMAIL SEUL</span>"
            )

            metadata = f"""
            <div style="background: #f8f9fa; padding: 15px; border: 1px solid #dee2e6;
                        border-radius: 4px; margin-bottom: 15px; font-size: 13px;">
                <p style="margin: 0 0 5px 0;">
                    <strong>📧 De :</strong> {email_from}
                </p>
                <p style="margin: 0 0 5px 0;">
                    <strong>📨 À :</strong> {destinataire} ({type_client})
                </p>
                <p style="margin: 0 0 5px 0;">
                    <strong>📋 Objet :</strong> {subject}
                </p>
                <p style="margin: 0;">
                    <strong>📎 Pièce jointe :</strong> {badge_pdf}
                </p>
            </div>
            """
            wiz.preview_html = metadata + body

    # ========================================================================
    # ACTIONS
    # ========================================================================

    def action_send_to_self_test(self):
        """Envoie un email de test à l'utilisateur courant pour validation."""
        self.ensure_one()
        if not self.preview_line_id:
            raise UserError(_(
                "Sélectionnez d'abord une ligne d'indexation pour la "
                "prévisualisation."
            ))

        test_email = self.test_email or self.env.user.email
        if not test_email:
            raise UserError(_(
                "Aucune adresse email de test définie. "
                "Renseigne le champ 'Email de test'."
            ))

        template = self._get_email_template()
        if not template:
            raise UserError(_("Template d'email introuvable."))

        # Envoi à l'adresse de test (override de email_to)
        will_attach_pdf = (
            self.attach_pdf_for_companies
            and self.preview_line_id.partner_id.is_company
        )

        attachment_ids = []
        if will_attach_pdf:
            attachment_ids = self._generate_pdf_attachment(self.preview_line_id)

        template.with_context(
            force_email_to=test_email
        ).send_mail(
            self.preview_line_id.id,
            force_send=True,
            email_values={
                'email_to': test_email,
                'partner_ids': [],  # Bypass partners
                'attachment_ids': [(6, 0, attachment_ids)],
            },
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Email de test envoyé"),
                'message': _("Email envoyé à %s") % test_email,
                'type': 'success',
            }
        }

    def action_send_all(self):
        """Envoie les notifications à tous les clients (mode normal ou test)."""
        self.ensure_one()

        lines_to_send = self.indexation_id.line_ids.filtered(
            lambda l: not l.notification_sent and l.partner_id.email
        )

        if not lines_to_send:
            raise UserError(_(
                "Aucune ligne à envoyer. Toutes les lignes sont déjà "
                "notifiées ou n'ont pas d'email destinataire."
            ))

        template = self._get_email_template()
        if not template:
            raise UserError(_("Template d'email introuvable."))

        sent_count = 0
        errors = []

        for line in lines_to_send:
            try:
                # Décide si PDF joint
                will_attach_pdf = (
                    self.attach_pdf_for_companies
                    and line.partner_id.is_company
                )

                attachment_ids = []
                if will_attach_pdf:
                    attachment_ids = self._generate_pdf_attachment(line)

                # Détermination du destinataire
                if self.test_mode:
                    target_email = self.test_email
                    email_values = {
                        'email_to': target_email,
                        'partner_ids': [],
                        'attachment_ids': [(6, 0, attachment_ids)],
                    }
                else:
                    target_email = line.partner_id.email
                    email_values = {
                        'attachment_ids': [(6, 0, attachment_ids)],
                    }

                template.send_mail(
                    line.id,
                    force_send=True,
                    email_values=email_values,
                )

                # Marquer comme notifié seulement en mode normal
                if not self.test_mode:
                    line.write({
                        'notification_sent': True,
                        'notification_date': fields.Datetime.now(),
                    })

                sent_count += 1

            except Exception as e:
                _logger.exception(
                    "Erreur envoi notification ligne %s", line.id
                )
                errors.append(
                    f"{line.partner_id.name} ({line.subscription_id.name}) : {e}"
                )

        # Mise à jour de l'indexation parente si non test
        if not self.test_mode and sent_count:
            unsent = self.indexation_id.line_ids.filtered(
                lambda l: not l.notification_sent
            )
            if not unsent:
                # Tous notifiés
                self.indexation_id.write({
                    'state': 'notified',
                    'notification_sent': True,
                    'notification_date': fields.Datetime.now(),
                })
            self.indexation_id.message_post(
                body=_(
                    "%d notification(s) d'indexation envoyée(s) via wizard."
                ) % sent_count
            )

        # Message de fin
        msg_parts = [
            _("✓ %d notification(s) envoyée(s)") % sent_count
        ]
        if self.test_mode:
            msg_parts.append(_("(MODE TEST — vrais clients non impactés)"))
        if errors:
            msg_parts.append(
                _("⚠ %d erreur(s) : %s") % (len(errors), ' | '.join(errors[:3]))
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Envoi terminé"),
                'message': ' '.join(msg_parts),
                'type': 'success' if not errors else 'warning',
                'sticky': bool(errors),
            }
        }

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _get_email_template(self):
        """Récupère le template email d'indexation."""
        return self.env.ref(
            'storage_indexation.email_template_indexation_notification',
            raise_if_not_found=False
        )

    def _generate_pdf_attachment(self, line):
        """Génère le PDF d'indexation pour une ligne et le retourne en
        attachment_ids list.

        Args:
            line: storage.indexation.line

        Returns:
            list of attachment IDs
        """
        report = self.env.ref(
            'storage_indexation.action_report_indexation_notice',
            raise_if_not_found=False
        )
        if not report:
            _logger.warning(
                "Rapport PDF d'indexation introuvable — envoi sans PDF"
            )
            return []

        try:
            pdf_content, _content_type = report._render_qweb_pdf(
                report.report_name, [line.id]
            )
        except Exception as e:
            _logger.exception("Erreur génération PDF pour ligne %s", line.id)
            return []

        filename = f"Indexation_{line.subscription_id.name or line.id}.pdf".replace('/', '_')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': pdf_content.decode() if isinstance(pdf_content, str)
                     else __import__('base64').b64encode(pdf_content),
            'res_model': 'storage.indexation.line',
            'res_id': line.id,
            'mimetype': 'application/pdf',
        })
        return [attachment.id]
