# -*- coding: utf-8 -*-
import re
from collections import defaultdict

from odoo import api, fields, models, tools, _

ISSUE_TYPES = [
    ('meta_desc_missing', 'Méta-description absente'),
    ('meta_desc_short', 'Méta-description trop courte (< 70 car.)'),
    ('meta_desc_long', 'Méta-description trop longue (> 160 car.)'),
    ('meta_desc_dup', 'Méta-description en doublon'),
    ('title_long', 'Titre Google trop long (> 65 car. avec le nom du site)'),
    ('title_dup', 'Titre en doublon'),
    ('content_thin', 'Contenu trop court (< 300 caractères)'),
    ('no_image', 'Pas d\'image'),
    ('no_category', 'Produit hors catégorie boutique'),
    ('slug_code', 'URL commençant par un code fournisseur'),
    ('untranslated', 'Méta non traduite (NL/EN)'),
    ('category_empty', 'Catégorie publiée sans texte de présentation'),
]
SEVERITY = {
    'meta_desc_missing': 'high', 'title_dup': 'high', 'content_thin': 'high',
    'no_image': 'high', 'no_category': 'medium', 'meta_desc_dup': 'medium',
    'title_long': 'medium', 'meta_desc_short': 'medium', 'category_empty': 'medium',
    'meta_desc_long': 'low', 'slug_code': 'low', 'untranslated': 'low',
}
SLUG_CODE_RE = re.compile(r'^(pool|scp|sc|fl|flu|ast|kb)-?[a-z]{0,3}\d{2,}', re.I)


def _text(html):
    return re.sub(r'\s+', ' ', tools.html2plaintext(html or '')).strip() if html else ''


class LolirineSeoIssue(models.Model):
    _name = 'lolirine.seo.issue'
    _description = 'Problème SEO détecté'
    _order = 'severity_rank, issue_type, name'

    name = fields.Char('Élément', required=True)
    website_id = fields.Many2one('website', 'Site', index=True, ondelete='cascade')
    issue_type = fields.Selection(ISSUE_TYPES, 'Problème', required=True, index=True)
    severity = fields.Selection([('high', 'Élevée'), ('medium', 'Moyenne'), ('low', 'Faible')],
                                'Gravité', required=True, index=True)
    severity_rank = fields.Integer(compute='_compute_rank', store=True)
    res_model = fields.Char('Modèle', required=True, index=True)
    res_id = fields.Integer('ID de l\'élément', required=True, index=True)
    detail = fields.Char('Détail')
    url = fields.Char('URL')
    impressions_28d = fields.Integer('Impressions Google (28 j)',
                                     help="Plus ce chiffre est élevé, plus la correction rapporte.")
    state = fields.Selection([('open', 'À corriger'), ('ignored', 'Ignoré')],
                             default='open', required=True, index=True)

    _issue_uniq = models.Constraint('unique(issue_type, res_model, res_id)',
                                    'Problème déjà enregistré.')

    @api.depends('severity')
    def _compute_rank(self):
        rank = {'high': 1, 'medium': 2, 'low': 3}
        for rec in self:
            rec.severity_rank = rank.get(rec.severity, 9)

    def action_open_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': self.res_model,
            'res_id': self.res_id, 'view_mode': 'form', 'target': 'current',
        }

    def action_open_url(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': self.url or '/', 'target': 'new'}

    def action_ignore(self):
        self.write({'state': 'ignored'})
        return True

    def action_reopen(self):
        self.write({'state': 'open'})
        return True

    # ------------------------------------------------------------------ audit
    @api.model
    def _impressions_by_path(self):
        self.env.cr.execute("""
            SELECT page, SUM(impressions) FROM lolirine_seo_gsc_line
             WHERE date >= CURRENT_DATE - 28 GROUP BY page""")
        res = defaultdict(int)
        for page, impr in self.env.cr.fetchall():
            path = re.sub(r'^https?://[^/]+', '', page or '').split('?')[0].split('#')[0]
            res[path.rstrip('/') or '/'] += impr or 0
        return res

    @api.model
    def _run_audit(self):
        found = {}   # (type, model, id) -> vals
        impressions = self._impressions_by_path()

        def add(website, itype, rec, name, detail='', url=''):
            path = (url or '').rstrip('/') or '/'
            found[(itype, rec._name, rec.id)] = {
                'name': (name or '')[:255], 'website_id': website.id, 'issue_type': itype,
                'severity': SEVERITY[itype], 'res_model': rec._name, 'res_id': rec.id,
                'detail': (detail or '')[:255], 'url': url or False,
                'impressions_28d': impressions.get(path, 0) if url else 0,
            }

        for website in self.env['lolirine.seo.config']._target_websites():
            default_lang = website.default_lang_id.code or 'fr_BE'
            other_langs = [l.code for l in website.language_ids if l.code != default_lang]
            suffix = len(' | ' + (website.name or ''))
            ctx = dict(lang=default_lang, website_id=website.id)

            # ---------------------------------------------------------- produits
            Product = self.env['product.template'].sudo().with_context(**ctx)
            products = Product.search([('website_id', '=', website.id), ('is_published', '=', True),
                                       ('sale_ok', '=', True)])
            titles, descs = defaultdict(list), defaultdict(list)
            for p in products:
                url = p.website_url or ''
                title = (p.website_meta_title or p.name or '').strip()
                desc = (p.website_meta_description or '').strip()
                titles[title.lower()].append(p)
                if desc:
                    descs[desc.lower()].append(p)
                if not desc:
                    add(website, 'meta_desc_missing', p, p.name, '', url)
                elif len(desc) < 70:
                    add(website, 'meta_desc_short', p, p.name, '%s car.' % len(desc), url)
                elif len(desc) > 160:
                    add(website, 'meta_desc_long', p, p.name, '%s car.' % len(desc), url)
                if len(title) + suffix > 65:
                    add(website, 'title_long', p, p.name,
                        '%s car. : %s' % (len(title) + suffix, title[:120]), url)
                content = len(_text(p.description_ecommerce)) + len(_text(p.website_description)) \
                    + len(p.description_sale or '')
                if content < 300:
                    add(website, 'content_thin', p, p.name, '%s car. de texte' % content, url)
                if not p.image_128:
                    add(website, 'no_image', p, p.name, '', url)
                if not p.public_categ_ids:
                    add(website, 'no_category', p, p.name, '', url)
                slug = url.rsplit('/', 1)[-1]
                if SLUG_CODE_RE.match(slug):
                    add(website, 'slug_code', p, p.name, slug[:120], url)
            for group in titles.values():
                if len(group) > 1:
                    for p in group:
                        add(website, 'title_dup', p, p.name,
                            '%s fiches ont ce titre' % len(group), p.website_url)
            for group in descs.values():
                if len(group) > 1:
                    for p in group:
                        add(website, 'meta_desc_dup', p, p.name,
                            '%s fiches partagent cette description' % len(group), p.website_url)
            # Traductions : méta FR présente mais identique (= non traduite) en NL/EN
            for lang in other_langs:
                tr = Product.with_context(lang=lang).browse(products.ids)
                for p, pt in zip(products, tr):
                    if p.website_meta_description and \
                            pt.website_meta_description == p.website_meta_description:
                        key = ('untranslated', p._name, p.id)
                        if key in found:
                            found[key]['detail'] += ', ' + lang
                        else:
                            add(website, 'untranslated', p, p.name, lang, p.website_url)

            # -------------------------------------------------------- catégories
            Categ = self.env['product.public.category'].sudo().with_context(**ctx)
            for c in Categ.search([('website_id', 'in', [False, website.id])]):
                if not c.has_published_products:
                    continue
                url = '/shop/category/%s' % self.env['ir.http']._slug(c)
                if not (c.website_meta_description or '').strip():
                    add(website, 'meta_desc_missing', c, 'Catégorie : %s' % c.name, '', url)
                if len(_text(c.website_description)) < 150:
                    add(website, 'category_empty', c, 'Catégorie : %s' % c.name,
                        'Ajoutez 2-3 paragraphes avec les mots-clés de la catégorie', url)

            # -------------------------------------------------------------- pages
            Page = self.env['website.page'].sudo().with_context(**ctx)
            for pg in Page.search([('website_id', '=', website.id), ('is_published', '=', True)]):
                if pg.url in ('/', '/404') or pg.url.startswith(('/shop', '/my')):
                    continue
                if not (pg.website_meta_description or '').strip():
                    add(website, 'meta_desc_missing', pg, 'Page : %s' % pg.name, '', pg.url)

        # Synchronisation : on garde les « ignorés », on remplace le reste
        existing = self.search([])
        by_key = {(i.issue_type, i.res_model, i.res_id): i for i in existing}
        to_delete = self.browse()
        for key, rec in by_key.items():
            if key not in found:
                to_delete |= rec
        to_delete.unlink()
        create_vals = []
        for key, vals in found.items():
            rec = by_key.get(key)
            if rec:
                vals = dict(vals)
                vals.pop('issue_type'), vals.pop('res_model'), vals.pop('res_id')
                rec.write(vals)
            else:
                create_vals.append(vals)
        for part in tools.split_every(2000, create_vals):
            self.create(list(part))
        self.env['lolirine.seo.config']._set(
            'audit_last', fields.Datetime.now().strftime('%d/%m/%Y %H:%M'))
        return self.search_count([('state', '=', 'open')])
