import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)

# Types de messages à intercepter venant du portail
PORTAL_MESSAGE_SUBTYPES = {
    'mail.mt_comment',
    'mail.mt_note',
}


class MailMessage(models.Model):
    _name = 'mail.message'
    _inherit = ['mail.message', 'lolirine.notify.mixin']

    @api.model_create_multi
    def create(self, vals_list):
        """Notifie quand un utilisateur portail envoie un message via le chatter portail."""
        messages = super().create(vals_list)

        portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
        if not portal_group:
            return messages

        for msg in messages:
            # Seulement messages d'utilisateurs portail, depuis le portail
            author = msg.author_id
            if not author:
                continue

            author_user = self.env['res.users'].sudo().search(
                [('partner_id', '=', author.id)], limit=1
            )
            if not author_user or portal_group not in author_user.groups_id:
                continue

            # Éviter les messages système / tracking
            if msg.message_type not in ('comment', 'email'):
                continue

            # Éviter les messages sortants (envoyés par l'admin au client)
            if author_user == self.env.user and not self.env.context.get('lolirine_notify_portal_msg'):
                continue

            try:
                record_url = '/web'
                if msg.model and msg.res_id:
                    record_url = f'/odoo/{msg.model.replace(".", "-")}/{msg.res_id}'

                body_text = msg.body or ''
                # Nettoyer le HTML pour l'affichage
                import re
                body_clean = re.sub(r'<[^>]+>', '', body_text).strip()[:200]

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
                        "<p>Message reçu de <strong>%(name)s</strong> :</p>"
                        "<blockquote>%(body)s</blockquote>",
                        name=author.name,
                        body=body_clean,
                    ),
                    activity_deadline_days=0,
                )
            except Exception as e:
                _logger.error("Notification mail.message failed for msg %s: %s", msg.id, e)

        return messages
