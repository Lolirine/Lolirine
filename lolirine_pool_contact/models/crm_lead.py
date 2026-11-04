# -*- coding: utf-8 -*-
"""Pistes Pool Store : expéditeur des réponses et devis rattaché au bon site.

Une piste est « Pool Store » quand son équipe a son alias sur le domaine
lolirinepoolstore.be (équipe « Pool Store », alias info@lolirinepoolstore.be).
"""
from email.utils import formataddr

from odoo import models

DOMAINE_POOL = 'lolirinepoolstore.be'
NOM_EXPEDITEUR = 'Lolirine Pool Store'


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def _lolirine_est_pool(self):
        self.ensure_one()
        team = self.team_id
        return bool(team and team.alias_email and team.alias_email.endswith('@' + DOMAINE_POOL))

    def message_post(self, **kwargs):
        """Réponse envoyée par un utilisateur depuis une piste Pool Store :
        expéditeur « Lolirine Pool Store <info@lolirinepoolstore.be> » au lieu
        de l'adresse personnelle de l'utilisateur. Les notes internes et les
        messages entrants ne sont pas concernés."""
        if (len(self) == 1 and not kwargs.get('email_from')
                and kwargs.get('message_type', 'notification') == 'comment'
                and not self.env.user._is_public() and not self.env.user.share
                and self._lolirine_est_pool()):
            kwargs['email_from'] = formataddr((NOM_EXPEDITEUR, self.team_id.alias_email))
        return super().message_post(**kwargs)

    def _prepare_opportunity_quotation_context(self):
        """Devis créé depuis une opportunité Pool Store : rattaché au site Pool Store
        (modèles d'e-mails, tarifs et équipe du site)."""
        ctx = super()._prepare_opportunity_quotation_context()
        if self._lolirine_est_pool() and 'website_id' in self.env['sale.order']._fields:
            site = self.env['website'].sudo().search(
                ['|', ('crm_default_team_id', '=', self.team_id.id), ('salesteam_id', '=', self.team_id.id)], limit=1)
            if site:
                ctx['default_website_id'] = site.id
        return ctx
