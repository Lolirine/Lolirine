import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _name = 'res.users'
    _inherit = ['res.users', 'lolirine.notify.mixin']

    @api.model_create_multi
    def create(self, vals_list):
        """Notifie lors de la création d'un utilisateur portail via le site."""
        users = super().create(vals_list)

        portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
        if not portal_group:
            return users

        for user in users:
            is_portal = portal_group in user.groups_id
            # Éviter de notifier pour les utilisateurs créés manuellement en back-office
            # (on vérifie que ce n'est pas un admin qui crée depuis le backend)
            if is_portal and not self.env.context.get('no_notify'):
                try:
                    partner = user.partner_id
                    self._lolirine_notify(
                        event_type='signup',
                        title=_("Nouvelle inscription portail"),
                        message=_(
                            "%(name)s (%(email)s) vient de s'inscrire sur le site garde-meuble.",
                            name=partner.name or user.login,
                            email=user.login,
                        ),
                        partner=partner,
                        url=f'/odoo/contacts/{partner.id}',
                        activity_summary=_("Nouveau client – à contacter"),
                        activity_note=_(
                            "<p>L'utilisateur <strong>%(name)s</strong> "
                            "(<a href='mailto:%(email)s'>%(email)s</a>) "
                            "vient de créer un compte sur le portail.</p>"
                            "<p>Pensez à le contacter pour lui présenter nos offres.</p>",
                            name=partner.name or user.login,
                            email=user.login,
                        ),
                        activity_deadline_days=1,
                    )
                except Exception as e:
                    _logger.error("Notification signup failed for user %s: %s", user.id, e)

        return users
