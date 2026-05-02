# -*- coding: utf-8 -*-

import base64
import logging
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GARDE_MEUBLE_JOURNAL_ID = 9
ANOMALY_TOLERANCE = 0.05  # tolérance en euros pour comparaisons


class LolirineInvoiceAuditWizard(models.TransientModel):
    _name = 'lolirine.invoice.audit.wizard'
    _description = "Audit mensuel de la facturation des abonnements"

    @api.model
    def _default_target_date(self):
        today = fields.Date.today()
        if today.day >= 20:
            return today.replace(day=20)
        return (today - relativedelta(months=1)).replace(day=20)

    @api.model
    def _default_journal(self):
        journal = self.env['account.journal'].browse(GARDE_MEUBLE_JOURNAL_ID)
        return journal if journal.exists() else self.env['account.journal']

    target_date = fields.Date(
        string="Date du cycle",
        default=_default_target_date,
        required=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string="Journal",
        default=_default_journal,
        required=True,
        domain="[('type', '=', 'sale')]",
    )
    detect_anomalies = fields.Boolean(
        string="Détecter les anomalies",
        default=True,
        help="Compare chaque facture avec son contrat source (prix, quantités, total)",
    )

    audit_line_ids = fields.One2many(
        'lolirine.invoice.audit.line',
        'wizard_id',
        string="Résultats",
    )

    has_results = fields.Boolean(compute='_compute_stats')
    total_subs = fields.Integer(string="Abonnements actifs", compute='_compute_stats')
    total_ok = fields.Integer(string="OK", compute='_compute_stats')
    total_not_sent = fields.Integer(string="Non envoyées", compute='_compute_stats')
    total_missing = fields.Integer(string="Manquantes", compute='_compute_stats')
    total_legit_skip = fields.Integer(string="Cycle décalé", compute='_compute_stats')
    total_no_email = fields.Integer(string="Sans email", compute='_compute_stats')
    total_draft = fields.Integer(string="Brouillons", compute='_compute_stats')
    total_cancelled = fields.Integer(string="Annulées seules", compute='_compute_stats')
    total_anomalies = fields.Integer(string="🚨 Anomalies", compute='_compute_stats')
    total_amount = fields.Float(string="Total facturé (TTC)", compute='_compute_stats')

    @api.depends('audit_line_ids', 'audit_line_ids.status', 'audit_line_ids.is_anomaly')
    def _compute_stats(self):
        for wiz in self:
            lines = wiz.audit_line_ids
            wiz.has_results = bool(lines)
            wiz.total_subs = len(lines)
            wiz.total_ok = len(lines.filtered(lambda l: l.status == 'ok'))
            wiz.total_not_sent = len(lines.filtered(lambda l: l.status == 'not_sent'))
            wiz.total_missing = len(lines.filtered(lambda l: l.status == 'missing'))
            wiz.total_legit_skip = len(lines.filtered(lambda l: l.status == 'legitimate_skip'))
            wiz.total_no_email = len(lines.filtered(lambda l: l.status == 'no_email'))
            wiz.total_draft = len(lines.filtered(lambda l: l.status == 'draft'))
            wiz.total_cancelled = len(lines.filtered(lambda l: l.status == 'cancelled_only'))
            wiz.total_anomalies = len(lines.filtered(lambda l: l.is_anomaly))
            wiz.total_amount = sum(lines.mapped('amount'))

    # ==================== ACTION : LANCER L'AUDIT ====================

    def action_run_audit(self):
        self.ensure_one()
        self.audit_line_ids.unlink()

        active_subs = self.env['sale.order'].search([
            ('is_subscription', '=', True),
            ('state', '=', 'sale'),
            ('subscription_state', 'in', ['3_progress', '4_paused', '5_renewed']),
            ('start_date', '<=', self.target_date),
            '|',
                ('end_date', '=', False),
                ('end_date', '>=', self.target_date),
        ])

        all_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '=', self.target_date),
            ('journal_id', '=', self.journal_id.id),
        ])
        invoices_by_origin = {}
        for inv in all_invoices:
            if inv.invoice_origin:
                invoices_by_origin.setdefault(inv.invoice_origin, self.env['account.move'])
                invoices_by_origin[inv.invoice_origin] |= inv

        line_vals_list = []
        for so in active_subs:
            invs = invoices_by_origin.get(so.name, self.env['account.move'])
            posted = invs.filtered(lambda i: i.state == 'posted')
            cancelled = invs.filtered(lambda i: i.state == 'cancel')
            drafts = invs.filtered(lambda i: i.state == 'draft')

            is_legit_skip = (
                so.next_invoice_date
                and so.next_invoice_date > self.target_date
                and not posted
                and not drafts
            )

            vals = {
                'wizard_id': self.id,
                'subscription_id': so.id,
                'partner_id': so.partner_id.id,
                'amount': 0.0,
                'expected_amount': so.amount_total,
                'is_anomaly': False,
                'anomaly_details': '',
            }

            if posted:
                inv = posted[0]
                vals['invoice_id'] = inv.id
                vals['amount'] = inv.amount_total
                sent = bool(inv.is_move_sent) if 'is_move_sent' in inv._fields else False
                if not so.partner_id.email:
                    vals['status'] = 'no_email'
                    vals['notes'] = "Partner sans email : envoi impossible"
                elif sent:
                    vals['status'] = 'ok'
                    vals['notes'] = ""
                else:
                    vals['status'] = 'not_sent'
                    vals['notes'] = "À envoyer"

                # Détection d'anomalies sur facture postée
                if self.detect_anomalies:
                    is_anomaly, details = self._detect_anomalies(inv, so)
                    vals['is_anomaly'] = is_anomaly
                    vals['anomaly_details'] = details

            elif drafts:
                vals['invoice_id'] = drafts[0].id
                vals['amount'] = drafts[0].amount_total
                vals['status'] = 'draft'
                vals['notes'] = "Brouillon non posté"
            elif is_legit_skip:
                vals['status'] = 'legitimate_skip'
                vals['notes'] = "Prochaine facturation : %s" % so.next_invoice_date.strftime('%d/%m/%Y')
            elif cancelled:
                vals['status'] = 'cancelled_only'
                vals['notes'] = "Que des annulées : %s" % ', '.join(cancelled.mapped('name'))
            else:
                next_inv = so.next_invoice_date.strftime('%d/%m/%Y') if so.next_invoice_date else '—'
                vals['status'] = 'missing'
                vals['notes'] = "Aucune facture | next_invoice_date : %s" % next_inv

            line_vals_list.append((0, 0, vals))

        self.audit_line_ids = line_vals_list
        return self._reload()

    # ==================== DÉTECTION D'ANOMALIES ====================

    def _detect_anomalies(self, invoice, so):
        """
        Compare la facture postée avec son contrat source.
        Retourne (is_anomaly: bool, details: str).
        """
        if not invoice or not so or invoice.state != 'posted':
            return False, ''

        anomalies = []

        # Détection : facture initiale avec frais de dossier (cycle 1)
        # On exclut alors la comparaison de total mais on garde celle des prix unitaires
        has_initial_fees = any(
            'FRAIS' in (l.product_id.default_code or '').upper()
            for l in invoice.invoice_line_ids
        )

        # 1. Comparaison ligne à ligne (prix + quantité)
        for inv_line in invoice.invoice_line_ids:
            if not inv_line.product_id or inv_line.display_type:
                continue

            # Skip frais de dossier (one-shot)
            if 'FRAIS' in (inv_line.product_id.default_code or '').upper():
                continue

            so_lines = inv_line.sale_line_ids
            if not so_lines:
                anomalies.append(
                    "Ligne sans SO : %s (%.2f€)" % (
                        inv_line.product_id.name or inv_line.name,
                        inv_line.price_subtotal,
                    )
                )
                continue

            for sl in so_lines:
                # Prix unitaire
                if abs(inv_line.price_unit - sl.price_unit) > ANOMALY_TOLERANCE:
                    anomalies.append(
                        "Prix divergent %s : SO=%.2f€ INV=%.2f€ (Δ=%+.2f€)" % (
                            inv_line.product_id.default_code or inv_line.product_id.name,
                            sl.price_unit,
                            inv_line.price_unit,
                            inv_line.price_unit - sl.price_unit,
                        )
                    )
                # Quantité (pour les box uniquement, pas les frais)
                if abs(inv_line.quantity - sl.product_uom_qty) > ANOMALY_TOLERANCE:
                    anomalies.append(
                        "Qté divergente %s : SO=%g INV=%g" % (
                            inv_line.product_id.default_code or inv_line.product_id.name,
                            sl.product_uom_qty,
                            inv_line.quantity,
                        )
                    )

        # 2. Comparaison du total (sauf si frais de dossier sur la facture)
        if not has_initial_fees:
            expected_total = so.amount_total
            actual_total = invoice.amount_total
            if abs(actual_total - expected_total) > ANOMALY_TOLERANCE:
                anomalies.append(
                    "Total divergent : SO=%.2f€ INV=%.2f€ (Δ=%+.2f€)" % (
                        expected_total,
                        actual_total,
                        actual_total - expected_total,
                    )
                )

        # 3. Lignes en SO mais pas en facture (sauf frais)
        invoiced_products = invoice.invoice_line_ids.mapped('product_id')
        for sl in so.order_line:
            if not sl.product_id or sl.display_type:
                continue
            if 'FRAIS' in (sl.product_id.default_code or '').upper():
                continue
            if sl.product_id not in invoiced_products:
                anomalies.append(
                    "Ligne SO non facturée : %s (%.2f€)" % (
                        sl.product_id.default_code or sl.product_id.name,
                        sl.price_subtotal,
                    )
                )

        return bool(anomalies), ' | '.join(anomalies)

    # ==================== ENVOI GROUPÉ ====================

    def action_send_selected(self):
        self.ensure_one()
        selected = self.audit_line_ids.filtered(
            lambda l: l.selected and l.status == 'not_sent' and l.invoice_id and l.partner_id.email
        )
        if not selected:
            raise UserError(_("Aucune ligne sélectionnée à envoyer."))

        sent_ok = 0
        sent_ko = 0
        for line in selected:
            success, msg = self._send_invoice_lolirine(line.invoice_id)
            if success:
                line.status = 'ok'
                line.notes = "Envoyée via wizard"
                line.selected = False
                sent_ok += 1
            else:
                line.notes = "Erreur : %s" % msg
                sent_ko += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Envoi groupé terminé"),
                'message': _("%(ok)s envoyée(s), %(ko)s en erreur") % {'ok': sent_ok, 'ko': sent_ko},
                'type': 'success' if sent_ko == 0 else 'warning',
                'sticky': sent_ko > 0,
                'next': self._reload(),
            },
        }

    def action_select_all_not_sent(self):
        self.ensure_one()
        for line in self.audit_line_ids:
            line.selected = (line.status == 'not_sent')
        return self._reload()

    def action_unselect_all(self):
        self.ensure_one()
        self.audit_line_ids.write({'selected': False})
        return self._reload()

    def action_filter_anomalies(self):
        """Ouvre une nouvelle fenêtre filtrée sur les anomalies uniquement."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Anomalies détectées"),
            'res_model': 'lolirine.invoice.audit.line',
            'view_mode': 'list,form',
            'domain': [('wizard_id', '=', self.id), ('is_anomaly', '=', True)],
            'target': 'current',
        }

    # ==================== HELPERS ====================

    def _reload(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.invoice.audit.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def _send_invoice_lolirine(self, invoice):
        if invoice.state != 'posted':
            return False, "Facture non postée"
        if not invoice.partner_id.email:
            return False, "Partner sans email"

        report = self.env.ref(
            'lolirine_invoice.action_report_invoice_lolirine',
            raise_if_not_found=False,
        )
        if not report:
            return False, "Template Lolirine introuvable"

        try:
            pdf_content, _ext = report._render_qweb_pdf(report.id, [invoice.id])
            attachment = self.env['ir.attachment'].create({
                'name': "%s.pdf" % invoice.name.replace('/', '_'),
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'account.move',
                'res_id': invoice.id,
                'mimetype': 'application/pdf',
            })

            mail = self.env['mail.mail'].create({
                'subject': "Votre facture %s - Lolirine Garde-Meubles" % invoice.name,
                'body_html': self._render_invoice_email_body(invoice),
                'email_from': 'Srl Lolirine <gardemeublelolirine@gmail.com>',
                'email_to': invoice.partner_id.email,
                'recipient_ids': [(6, 0, [invoice.partner_id.id])],
                'attachment_ids': [(6, 0, [attachment.id])],
                'auto_delete': False,
                'model': 'account.move',
                'res_id': invoice.id,
            })
            mail.send()

            if mail.state != 'sent':
                return False, "Envoi mail.mail KO : state=%s" % mail.state

            if 'is_move_sent' in invoice._fields:
                invoice.is_move_sent = True

            invoice.message_post(
                body=("<p>Facture envoyée via wizard d'audit à <strong>%s</strong>.</p>"
                      % invoice.partner_id.email),
                subtype_xmlid='mail.mt_note',
            )
            return True, "OK"

        except Exception as e:
            _logger.exception("Wizard audit : erreur envoi %s", invoice.name)
            return False, str(e)[:200]

    def _render_invoice_email_body(self, invoice):
        return """
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
    <p>Bonjour %(partner)s,</p>
    <p>Veuillez trouver en pièce jointe votre facture mensuelle.</p>
    <table style="margin: 20px 0; border-collapse: collapse; width: 100%%; max-width: 400px;">
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Numéro de facture</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">%(name)s</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date de facturation</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">%(date)s</td>
        </tr>
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date d'échéance</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">%(due)s</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant total</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>%(total).2f &euro;</strong></td>
        </tr>
    </table>
    <p><strong>Modalit&eacute;s de paiement :</strong></p>
    <ul>
        <li>Communication structur&eacute;e : %(ref)s</li>
        <li>Compte bancaire : BE07 7320 5208 0866 - CBC</li>
    </ul>
    <p>Cordialement,<br/>
    <strong>Lolirine Garde-Meubles</strong><br/>
    Feron Rodney<br/>
    T&eacute;l. : 0497/44 41 46</p>
</div>
""" % {
            'partner': invoice.partner_id.name or '',
            'name': invoice.name or '',
            'date': invoice.invoice_date.strftime('%d/%m/%Y') if invoice.invoice_date else '',
            'due': invoice.invoice_date_due.strftime('%d/%m/%Y') if invoice.invoice_date_due else '',
            'total': invoice.amount_total or 0.0,
            'ref': invoice.payment_reference or 'Voir facture',
        }


class LolirineInvoiceAuditLine(models.TransientModel):
    _name = 'lolirine.invoice.audit.line'
    _description = "Ligne d'audit de facturation"
    _order = 'is_anomaly desc, status, subscription_id'

    wizard_id = fields.Many2one(
        'lolirine.invoice.audit.wizard',
        ondelete='cascade',
        required=True,
        index=True,
    )
    selected = fields.Boolean(string="Sél.", default=False)

    subscription_id = fields.Many2one('sale.order', string="Contrat", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Client", readonly=True)
    partner_email = fields.Char(related='partner_id.email', string="Email", readonly=True)
    invoice_id = fields.Many2one('account.move', string="Facture", readonly=True)
    amount = fields.Float(string="TTC", readonly=True)
    expected_amount = fields.Float(string="TTC attendu (SO)", readonly=True)

    status = fields.Selection([
        ('ok', '✓ OK'),
        ('not_sent', '⚠ Non envoyée'),
        ('missing', '❌ Manquante'),
        ('draft', '📝 Brouillon'),
        ('legitimate_skip', '↷ Cycle décalé'),
        ('cancelled_only', '⊘ Annulées seules'),
        ('no_email', '✉ Sans email'),
    ], string="Statut", readonly=True, index=True)

    notes = fields.Char(string="Notes", readonly=True)

    is_anomaly = fields.Boolean(string="🚨", readonly=True, index=True)
    anomaly_details = fields.Char(string="Détails anomalie", readonly=True)

    def action_open_subscription(self):
        self.ensure_one()
        if not self.subscription_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_send_one(self):
        self.ensure_one()
        if self.status != 'not_sent':
            raise UserError(_("Cette ligne n'est pas en statut 'non envoyée'."))
        if not self.invoice_id or not self.partner_id.email:
            raise UserError(_("Facture manquante ou partner sans email."))

        success, msg = self.wizard_id._send_invoice_lolirine(self.invoice_id)
        if success:
            self.status = 'ok'
            self.notes = "Envoyée via wizard"
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Envoi réussi"),
                    'message': _("%(inv)s envoyée à %(email)s") % {
                        'inv': self.invoice_id.name,
                        'email': self.partner_email,
                    },
                    'type': 'success',
                    'next': self.wizard_id._reload(),
                },
            }
        self.notes = "Erreur : %s" % msg
        raise UserError(_("Erreur d'envoi : %s") % msg)
