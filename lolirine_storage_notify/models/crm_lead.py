import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'lolirine.notify.mixin']

    @api.model_create_multi
    def create(self, vals_list):
        """Notifie pour les leads/contacts créés depuis le site web."""
        leads = super().create(vals_list)

        for lead in leads:
            # On ne notifie que pour les leads venant du site (source website)
            # ou s'il y a un website_id dans le contexte
            is_from_website = (
                self.env.context.get('website_id') or
                self.env.context.get('from_website') or
                (lead.source_id and 'website' in (lead.source_id.name or '').lower()) or
                lead.website_id
            )

            if not is_from_website and not self.env.context.get('lolirine_notify_lead'):
                continue

            try:
                partner = lead.partner_id
                name = partner.name if partner else (lead.contact_name or lead.partner_name or _("Inconnu"))
                email = lead.email_from or (partner.email if partner else '')

                self._lolirine_notify(
                    event_type='contact',
                    title=_("Nouveau message / formulaire de contact"),
                    message=_(
                        "%(name)s (%(email)s) : « %(subject)s »",
                        name=name,
                        email=email or _("email non renseigné"),
                        subject=lead.name or _("Sans objet"),
                    ),
                    partner=partner,
                    url=f'/odoo/crm/{lead.id}',
                    activity_summary=_("Répondre au contact"),
                    activity_note=_(
                        "<p>Message reçu via le site :<br/>"
                        "<strong>%(subject)s</strong><br/>"
                        "De : %(name)s (%(email)s)<br/>"
                        "Téléphone : %(phone)s</p>"
                        "<p>%(description)s</p>",
                        subject=lead.name or _("Sans objet"),
                        name=name,
                        email=email or '',
                        phone=lead.phone or lead.mobile or _("non renseigné"),
                        description=lead.description or '',
                    ),
                    activity_deadline_days=1,
                )
            except Exception as e:
                _logger.error("Notification CRM lead failed for lead %s: %s", lead.id, e)

        return leads
