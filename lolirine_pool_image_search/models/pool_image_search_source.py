# -*- coding: utf-8 -*-
"""
pool_image_search_source
========================
Registre des sources de scraping ciblées.

Chaque source définit :
- Un nom et un domaine
- Une stratégie (direct_search, ddg_site, brand_lookup)
- Un priority score (plus bas = essayé en premier)
- Un quota quotidien max (anti-burn)
- Un statut actif/inactif
"""
from odoo import fields, models


class PoolImageSearchSource(models.Model):
    _name = 'pool.image.search.source'
    _description = 'Source de scraping d\'images produits'
    _order = 'priority, name'

    name = fields.Char(string='Nom', required=True)
    domain = fields.Char(string='Domaine', required=True,
                        help="Ex: fluidra.com, pentair.com")
    strategy = fields.Selection([
        ('direct_search', 'Recherche directe sur le site'),
        ('ddg_site', 'DuckDuckGo site:domain (fallback)'),
        ('brand_lookup', 'Recherche par SKU sur fiche marque'),
    ], string='Stratégie', required=True, default='ddg_site')

    search_url_template = fields.Char(
        string='Template URL de recherche',
        help="Utilise {query} et {ref} comme placeholders. Ex: "
             "https://www.fluidra.com/search?q={query}"
    )

    priority = fields.Integer(string='Priorité', default=50,
                             help="Plus bas = essayé en premier")
    active = fields.Boolean(string='Actif', default=True)

    daily_quota = fields.Integer(string='Quota quotidien max', default=500)
    requests_today = fields.Integer(string='Requêtes aujourd\'hui', default=0)
    last_reset_date = fields.Date(string='Dernier reset')

    success_rate = fields.Float(string='Taux de succès (%)', readonly=True,
                               help="Mis à jour automatiquement")
    total_requests = fields.Integer(string='Total requêtes', readonly=True)
    total_success = fields.Integer(string='Total succès', readonly=True)

    notes = fields.Text(string='Notes')

    def increment_counter(self, success=True):
        """Incrémente les compteurs après une requête."""
        today = fields.Date.context_today(self)
        for src in self:
            if src.last_reset_date != today:
                src.requests_today = 0
                src.last_reset_date = today
            src.requests_today += 1
            src.total_requests += 1
            if success:
                src.total_success += 1
            if src.total_requests:
                src.success_rate = 100.0 * src.total_success / src.total_requests

    def is_available(self):
        """Vérifie si la source peut encore servir aujourd'hui."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.last_reset_date != today:
            return self.active
        return self.active and self.requests_today < self.daily_quota
