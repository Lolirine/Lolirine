# -*- coding: utf-8 -*-
"""Données structurées « boutique en ligne » (schema.org) pour les sites suivis.

Remplace, sur ces sites seulement, le bloc Organization générique de
website_sale (nom de la société + logo société) par :
  - OnlineStore : nom et logo du site, réseaux sociaux, adresse de contact,
    téléphone, horaires, société exploitante ;
  - WebSite : nom du site et langue.
Les valeurs d'adresse / téléphone / horaires sont réglables par paramètres
système (lolirine_seo.org_*), avec les valeurs du Pool Store par défaut.
"""
import json

from markupsafe import Markup

from odoo import models

DEFAULTS = {
    'org_street': "Rue Bois d'Esneux 110",
    'org_zip': '5021',
    'org_city': 'Namur',
    'org_country': 'BE',
    'org_phone': '+32 497 44 41 46',
    'org_legal_name': 'Lolirine SRL',
    'org_vat': 'BE0650891279',
    # jours ISO schema.org : ouverture-fermeture ; vide = pas d'horaires publiés
    'org_hours_week': '09:00-18:00',
    'org_hours_saturday': '09:00-16:00',
}


class Website(models.Model):
    _inherit = 'website'

    def _lolirine_seo_tracked(self):
        self.ensure_one()
        return self.id in self.env['lolirine.seo.config'].sudo()._target_website_ids()

    def _lolirine_seo_param(self, key):
        return self.env['ir.config_parameter'].sudo().get_param(
            'lolirine_seo.' + key, DEFAULTS.get(key, '')) or ''

    def _lolirine_seo_org_jsonld(self):
        self.ensure_one()
        base = self.get_base_url().rstrip('/')
        p = self._lolirine_seo_param
        same_as = [u for u in (self.social_facebook, self.social_instagram, self.social_linkedin,
                               self.social_youtube, self.social_tiktok, self.social_twitter) if u]
        hours = []
        for days, key in ((['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], 'org_hours_week'),
                          (['Saturday'], 'org_hours_saturday')):
            span = p(key)
            if span and '-' in span:
                opens, closes = [s.strip() for s in span.split('-', 1)]
                hours.append({'@type': 'OpeningHoursSpecification', 'dayOfWeek': days,
                              'opens': opens, 'closes': closes})
        store = {
            '@type': 'OnlineStore',
            '@id': base + '/#organization',
            'name': self.name,
            'url': base + '/',
            'logo': '%s/web/image/website/%s/logo' % (base, self.id),
        }
        if same_as:
            store['sameAs'] = same_as
        if p('org_phone'):
            store['telephone'] = p('org_phone')
            contact = {'@type': 'ContactPoint', 'telephone': p('org_phone'),
                       'contactType': 'customer service',
                       'availableLanguage': ['French', 'Dutch', 'English'],
                       'areaServed': p('org_country') or 'BE'}
            if hours:
                contact['hoursAvailable'] = hours
            store['contactPoint'] = contact
        if p('org_street'):
            store['address'] = {'@type': 'PostalAddress', 'streetAddress': p('org_street'),
                                'postalCode': p('org_zip'), 'addressLocality': p('org_city'),
                                'addressCountry': p('org_country') or 'BE'}
        if p('org_legal_name'):
            parent = {'@type': 'Organization', 'name': p('org_legal_name')}
            if p('org_vat'):
                parent['vatID'] = p('org_vat')
            store['parentOrganization'] = parent
        lang = (self.default_lang_id.code or 'fr_BE').replace('_', '-')
        graph = {
            '@context': 'https://schema.org',
            '@graph': [store, {
                '@type': 'WebSite', '@id': base + '/#website', 'url': base + '/',
                'name': self.name, 'inLanguage': lang,
                'publisher': {'@id': base + '/#organization'},
            }],
        }
        # « </ » neutralisé pour ne jamais fermer la balise <script> prématurément
        return Markup(json.dumps(graph, ensure_ascii=False).replace('</', '<\\/'))
