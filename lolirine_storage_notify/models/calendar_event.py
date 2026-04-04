import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _name = 'calendar.event'
    _inherit = ['calendar.event', 'lolirine.notify.mixin']

    @api.model_create_multi
    def create(self, vals_list):
        """Notifie à chaque création d'un rendez-vous."""
        events = super().create(vals_list)

        for event in events:
            # On notifie si le créateur n'est pas un admin (= vient du portail / site)
            # OU si le contexte force la notification
            force = self.env.context.get('lolirine_notify_rdv', False)
            is_portal_origin = self.env.context.get('website_id') or \
                               self.env.context.get('from_portal') or \
                               force

            if not is_portal_origin:
                # Vérifier si l'organisateur est un utilisateur portail
                organizer = event.user_id
                portal_grp = self.env.ref('base.group_portal', raise_if_not_found=False)
                if not organizer or not portal_grp or portal_grp not in organizer.groups_id:
                    continue

            try:
                # Récupérer le partenaire principal (premier attendee externe)
                partner = None
                for att in event.attendee_ids:
                    if att.partner_id and att.partner_id != self.env.user.partner_id:
                        partner = att.partner_id
                        break
                if not partner and event.partner_ids:
                    partner = event.partner_ids[0]

                start_str = event.start.strftime('%d/%m/%Y à %H:%M') if event.start else '?'
                name = partner.name if partner else _("Inconnu")

                self._lolirine_notify(
                    event_type='rdv',
                    title=_("Nouvelle demande de rendez-vous"),
                    message=_(
                        "%(name)s a demandé un RDV : « %(event)s » le %(date)s.",
                        name=name,
                        event=event.name or _("Sans titre"),
                        date=start_str,
                    ),
                    partner=partner,
                    url=f'/odoo/calendar/{event.id}',
                    activity_summary=_("RDV à confirmer"),
                    activity_note=_(
                        "<p>Nouvelle demande de rendez-vous :<br/>"
                        "<strong>%(event)s</strong><br/>"
                        "Demandé par : %(name)s<br/>"
                        "Date souhaitée : %(date)s</p>",
                        event=event.name or _("Sans titre"),
                        name=name,
                        date=start_str,
                    ),
                    activity_deadline_days=0,  # Aujourd'hui
                )
            except Exception as e:
                _logger.error("Notification RDV failed for event %s: %s", event.id, e)

        return events
