"""Alerte interne à chaque nouvelle inscription à une liste de diffusion (newsletter).

Un e-mail est envoyé à l'adresse du paramètre
lolirine_pool_buypanel.newsletter_alerte_email (défaut : info@lolirinepoolstore.be ;
vide = pas d'alerte).
"""
import logging

from markupsafe import Markup, escape

from odoo import api, models

_logger = logging.getLogger(__name__)


class MailingSubscription(models.Model):
    _inherit = 'mailing.subscription'

    @api.model_create_multi
    def create(self, vals_list):
        abonnements = super().create(vals_list)
        if self.env.context.get('install_mode') or self.env.context.get('import_file'):
            return abonnements
        try:
            abonnements.sudo()._lolirine_alerte_inscription()
        except Exception:
            _logger.exception("Newsletter : alerte d'inscription non envoyée")
        return abonnements

    def _lolirine_alerte_inscription(self):
        destinataire = self.env['ir.config_parameter'].sudo().get_param(
            'lolirine_pool_buypanel.newsletter_alerte_email', 'info@lolirinepoolstore.be')
        if not destinataire:
            return
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for abo in self:
            email = abo.contact_id.email or ''
            if not email or abo.opt_out:
                continue
            total = self.search_count([('list_id', '=', abo.list_id.id), ('opt_out', '=', False)])
            corps = Markup(
                "<p>Nouvelle inscription à la liste « %s » : <strong>%s</strong>.</p>"
                "<p>La liste compte maintenant %s abonné(s).</p>"
                "<p><a href=\"%s/odoo/action-lolirine_contact_form.action_abonnes_newsletter\">"
                "Voir les abonnés</a></p>"
            ) % (escape(abo.list_id.name or ''), escape(email), total, escape(base))
            self.env['mail.mail'].sudo().create({
                'subject': "Nouvel abonné newsletter : %s" % email,
                'email_from': 'Lolirine Pool Store <info@lolirinepoolstore.be>',
                'email_to': destinataire,
                'body_html': corps,
                'auto_delete': True,
            })
