import logging
import re
from odoo import models, api, _

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _name = 'mail.message'
    _inherit = ['mail.message', 'lolirine.notify.mixin']

    @api.model_create_multi
    def create(self, vals_list):
        """Notifie quand un utilisateur portail envoie un message via le chatter portail."""
        messages = super().create(vals_list)

        # Toute la logique de notification est dans un try/except global
        # pour ne JAMAIS bloquer une opération Odoo (upload, création, etc.)
        try:
            self._check_and_notify_portal_messages(messages)
        except Exception as e:
            _logger.error("lolirine_notify mail_message hook error (non-bloquant): %s", e)

        return messages

    def _check_and_notify_portal_messages(self, messages):
        portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
        if not portal_group:
            return

        for msg in messages:
            try:
                author = msg.author_id
                if not author:
                    continue

                # Seulement les types de messages visibles (pas les logs système)
                if msg.message_type not in ('comment', 'email'):
                    continue

                author_user = self.env['res.users'].sudo().search(
                    [('partner_id', '=', author.id)], limit=1
                )
                if not author_user:
                    continue

                # Éviter les messages de l'admin courant
                if author_user.id == self.env.user.id:
                    continue

                # Vérification portail via SQL (groups_id supprimé en Odoo 19)
                self.env.cr.execute("""
                    SELECT 1 FROM res_groups_users_rel
                    WHERE gid = %s AND uid = %s
                    LIMIT 1
                """, [portal_group.id, author_user.id])
                if not self.env.cr.fetchone():
                    continue

                record_url = '/web'
                if msg.model and msg.res_id:
                    record_url = f'/odoo/{msg.model.replace(".", "-")}/{msg.res_id}'

                body_clean = re.sub(r'<[^>]+>', '', msg.body or '').strip()[:200]

                self._lolirine_notify(
                    event_type='message',
                    title=_("Message portail reçu"),
                    message=_(
                        "%(name)s : %(body)s",
                        name=author.name,
                        body=body_clean or _("(sans texte)"),
                    ),
                    partner=author,
                    url=record_url,
                    activity_summary=_("Répondre au message"),
                    activity_note=_(
                        "<p>Message de <strong>%(name)s</strong> :</p>"
                        "<blockquote>%(body)s</blockquote>",
                        name=author.name,
                        body=body_clean,
                    ),
                    activity_deadline_days=0,
                )
            except Exception as e:
                _logger.error(
                    "lolirine_notify: échec notification msg %s: %s",
                    msg.id if msg else '?', e
                )
