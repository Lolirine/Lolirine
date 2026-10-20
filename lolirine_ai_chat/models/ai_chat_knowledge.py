import logging
import re
import unicodedata

import requests
from lxml import etree, html as lxml_html

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

MOTS_VIDES = {
    'avec', 'sans', 'pour', 'dans', 'mais', 'plus', 'moins', 'tres', 'est', 'sont', 'les', 'des',
    'une', 'un', 'le', 'la', 'de', 'du', 'et', 'ou', 'en', 'au', 'aux', 'ce', 'cet', 'cette', 'ces',
    'que', 'qui', 'quoi', 'quel', 'quelle', 'quels', 'quelles', 'comment', 'combien', 'pourquoi',
    'votre', 'vos', 'notre', 'nos', 'mon', 'mes', 'ton', 'tes', 'son', 'ses', 'leur', 'leurs',
    'faut', 'faire', 'peux', 'peut', 'puis', 'avez', 'avoir', 'etre', 'bonjour', 'merci', 'svp',
    'piscine', 'piscines', 'what', 'have', 'does', 'with', 'from', 'this', 'that', 'voor', 'met',
    'een', 'het', 'van', 'zijn', 'hebben', 'kunnen',
}
# Pages qui n'apportent rien au chatbot (panier, compte, formulaires techniques)
URLS_EXCLUES = ('/shop/cart', '/shop/checkout', '/shop/payment', '/my', '/web', '/odoo', '/shop/wishlist')
TAILLE_PAGE = 4000


def normaliser(texte):
    """Minuscules sans accents : « Électrolyseur » → « electrolyseur »."""
    texte = unicodedata.normalize('NFKD', texte or '')
    return ''.join(c for c in texte if not unicodedata.combining(c)).lower()


def mots_cles(texte):
    return [m for m in re.findall(r'[a-z0-9]{3,}', normaliser(texte)) if m not in MOTS_VIDES]


class AiChatKnowledge(models.Model):
    _name = 'ai.chat.knowledge'
    _description = 'Base de connaissances du chatbot'
    _order = 'sequence, kind, name'

    name = fields.Char(string='Titre', required=True)
    url = fields.Char(string='Lien')
    kind = fields.Selection([
        ('essentiel', 'Essentiel (toujours fourni)'),
        ('page', 'Page du site'),
        ('categorie', 'Catégorie'),
        ('marque', 'Marque'),
        ('faq', 'Question / réponse'),
    ], string='Type', required=True, default='faq')
    content = fields.Text(string='Contenu', required=True)
    keywords = fields.Char(string='Mots-clés', help='Mots supplémentaires qui doivent faire remonter cette fiche.')
    manual = fields.Boolean(
        string='Saisie manuelle', default=True,
        help='Les fiches manuelles ne sont jamais écrasées ni supprimées par la reconstruction automatique.')
    website_id = fields.Many2one('website', string='Site web', ondelete='cascade')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    search_text = fields.Text(compute='_compute_search_text', store=True)

    @api.depends('name', 'keywords', 'content')
    def _compute_search_text(self):
        for rec in self:
            rec.search_text = ' '.join(normaliser(x) for x in (rec.name, rec.keywords, rec.content) if x)

    # ------------------------------------------------------------------ recherche
    @api.model
    def chercher(self, question, website_id=None, limite=4):
        """Fiches les plus pertinentes pour la question + les fiches « essentiel »."""
        dom_site = ['|', ('website_id', '=', False), ('website_id', '=', website_id)] if website_id else []
        essentiels = self.sudo().search([('kind', '=', 'essentiel')] + dom_site)
        mots = list(dict.fromkeys(mots_cles(question)))
        if not mots:
            return essentiels, self.browse()
        dom_mots = ['|'] * (len(mots[:8]) - 1) + [('search_text', 'ilike', m) for m in mots[:8]]
        candidates = self.sudo().search([('kind', '!=', 'essentiel')] + dom_site + dom_mots, limit=200)
        notes = []
        for rec in candidates:
            titre = normaliser(rec.name) + ' ' + normaliser(rec.keywords or '')
            corps = rec.search_text or ''
            note = 0.0
            for m in mots:
                if m in titre:
                    note += 3
                if m in corps:
                    note += 1 + min(corps.count(m), 5) * 0.2
            if rec.kind == 'faq':
                note *= 1.3
            notes.append((note, rec.id))
        notes.sort(reverse=True)
        ids = [i for n, i in notes[:limite] if n >= 2]
        return essentiels, self.browse(ids)

    # ------------------------------------------------------------ reconstruction
    @api.model
    def _cron_reconstruire(self):
        param = self.env['ir.config_parameter'].sudo().get_param('lolirine_ai_chat.website_id', '')
        sites = self.env['website'].sudo().browse(int(param)) if param and param.isdigit() and int(param) else \
            self.env['website'].sudo().search([])
        for site in sites.exists():
            self.reconstruire(site)

    def action_reconstruire(self):
        self._cron_reconstruire()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': 'Base de connaissances', 'type': 'success', 'sticky': False,
                       'message': 'Contenu du site relu : %d fiches automatiques.' % self.search_count([('manual', '=', False)]),
                       'next': {'type': 'ir.actions.act_window_close'}},
        }

    @api.model
    def reconstruire(self, site):
        """Relit le site et remplace toutes les fiches automatiques de ce site."""
        site = site.sudo()
        fiches = []
        fiches += self._fiches_essentielles(site)
        fiches += self._fiches_pages(site)
        fiches += self._fiches_categories(site)
        fiches += self._fiches_marques(site)
        anciennes = self.sudo().with_context(active_test=False).search([('manual', '=', False), ('website_id', '=', site.id)])
        anciennes.unlink()
        for f in fiches:
            f.update({'manual': False, 'website_id': site.id})
        self.sudo().create(fiches)
        _logger.info('AI Chat : base de connaissances du site %s reconstruite (%d fiches)', site.name, len(fiches))
        return len(fiches)

    def _base_url(self, site):
        return (site.domain and ('https://' + site.domain.replace('https://', '').replace('http://', '').rstrip('/'))) \
            or site.get_base_url()

    def _fiches_essentielles(self, site):
        soc = site.company_id
        lignes = ['Boutique en ligne : %s (%s).' % (site.name, self._base_url(site))]
        if soc:
            adresse = ', '.join(x for x in [soc.street, soc.zip and soc.city and '%s %s' % (soc.zip, soc.city),
                                           soc.country_id.name] if x)
            lignes.append('Société : %s%s.' % (soc.name, (' — ' + adresse) if adresse else ''))
            if soc.phone:
                lignes.append('Téléphone : %s.' % soc.phone)
            if soc.email:
                lignes.append('E-mail : %s.' % soc.email)
            if soc.vat:
                lignes.append('TVA : %s.' % soc.vat)
        langues = ', '.join(site.language_ids.mapped('name'))
        if langues:
            lignes.append('Langues du site : %s.' % langues)
        racines = self._categories_site(site).filtered(lambda c: not c.parent_id)
        if racines:
            lignes.append('Grandes familles du catalogue : %s.' % ', '.join(
                '%s (%s/shop/category/%s)' % (c.name, self._base_url(site), c.id) for c in racines))
        return [{'name': 'Informations générales %s' % site.name, 'kind': 'essentiel', 'sequence': 1,
                 'url': self._base_url(site), 'content': '\n'.join(lignes)}]

    # pages -----------------------------------------------------------------
    def _urls_pages(self, site):
        urls = {}
        Page = self.env['website.page'].sudo()
        for p in Page.search(['|', ('website_id', '=', site.id), ('website_id', '=', False), ('is_published', '=', True)]):
            if p.url:
                urls.setdefault(p.url, p.name)
        for m in self.env['website.menu'].sudo().search([('website_id', '=', site.id)]):
            u = (m.url or '').strip()
            if u.startswith('/') and not u.startswith(('/shop/category', '/shop?', '/shop/product')) and u not in ('/', '/shop'):
                urls.setdefault(u.split('#')[0], m.name)
        return {u: n for u, n in urls.items() if u and not u.startswith(URLS_EXCLUES)}

    def _texte_html(self, contenu):
        doc = lxml_html.fromstring(contenu)
        for bad in doc.xpath('//script|//style|//noscript|//header|//footer|//nav|//form'):
            bad.getparent().remove(bad)
        zone = doc.xpath('//main') or doc.xpath('//*[@id="wrap"]') or [doc]
        texte = ' '.join(zone[0].itertext())
        return re.sub(r'\s+', ' ', texte).strip()

    def _texte_arch(self, arch):
        try:
            doc = etree.fromstring(arch.encode('utf-8'))
        except Exception:
            return ''
        for bad in doc.xpath('//script|//style'):
            bad.getparent().remove(bad)
        return re.sub(r'\s+', ' ', ' '.join(doc.itertext())).strip()

    def _fiches_pages(self, site):
        base = self._base_url(site)
        fiches = []
        Page = self.env['website.page'].sudo()
        for url, nom in sorted(self._urls_pages(site).items()):
            texte = ''
            try:
                r = requests.get(base + url, timeout=20, headers={'User-Agent': 'LolirineChatbot/1.0'})
                if r.status_code == 200 and 'html' in r.headers.get('Content-Type', ''):
                    texte = self._texte_html(r.content)
            except Exception as e:
                _logger.info('AI Chat : page %s illisible par HTTP (%s), lecture de la vue', url, e)
            if not texte:
                page = Page.search([('url', '=', url), '|', ('website_id', '=', site.id), ('website_id', '=', False)], limit=1)
                if page and page.view_id:
                    texte = self._texte_arch(page.view_id.with_context(lang=site.default_lang_id.code).arch_db or '')
            if len(texte) < 80:
                continue
            fiches.append({'name': nom or url, 'kind': 'page', 'url': base + url, 'sequence': 20,
                           'content': texte[:TAILLE_PAGE]})
        return fiches

    # catalogue -------------------------------------------------------------
    def _produits_dom(self, site):
        PT = self.env['product.template']
        dom = [('is_published', '=', True), ('sale_ok', '=', True),
               '|', ('website_id', '=', False), ('website_id', '=', site.id)]
        if 'is_pool_product' in PT._fields and site.id == int(self.env['ir.config_parameter'].sudo()
                                                               .get_param('lolirine_ai_chat.website_id', '0') or 0):
            dom.append(('is_pool_product', '=', True))
        return dom

    def _categories_site(self, site):
        PT = self.env['product.template'].sudo()
        ids = set()
        for g in PT._read_group(self._produits_dom(site), ['public_categ_ids'], ['__count']):
            if g[0]:
                ids.add(g[0].id)
        cats = self.env['product.public.category'].sudo().browse(list(ids)).exists()
        tout = cats
        for c in cats:
            tout |= c.parent_id
            p = c.parent_id
            while p:
                tout |= p
                p = p.parent_id
        return tout.filtered(lambda c: not c.website_id or c.website_id == site)

    def _fiches_categories(self, site):
        PT = self.env['product.template'].sudo()
        base = self._base_url(site)
        marque = 'pool_brand_id' in PT._fields
        fiches = []
        for c in self._categories_site(site):
            produits = PT.search(self._produits_dom(site) + [('public_categ_ids', 'child_of', c.id)])
            if not produits:
                continue
            prix = [p for p in produits.mapped('list_price') if p > 0]
            lignes = ['Catégorie « %s » : %d produits.' % (c.display_name, len(produits))]
            if prix:
                lignes.append('Prix catalogue de %.2f à %.2f EUR.' % (min(prix), max(prix)))
            if c.child_id:
                lignes.append('Sous-catégories : %s.' % ', '.join(c.child_id.mapped('name')))
            if marque:
                noms = [m for m in produits.mapped('pool_brand_id.name') if m]
                if noms:
                    lignes.append('Marques : %s.' % ', '.join(sorted(set(noms))[:15]))
            exemples = produits.sorted(lambda p: -p.list_price)[:6]
            lignes.append('Exemples : %s.' % '; '.join(p.name for p in exemples))
            fiches.append({'name': 'Catégorie %s' % c.display_name, 'kind': 'categorie', 'sequence': 30,
                           'url': '%s/shop/category/%s' % (base, c.id), 'keywords': c.name,
                           'content': '\n'.join(lignes)})
        return fiches

    def _fiches_marques(self, site):
        PT = self.env['product.template'].sudo()
        if 'pool_brand_id' not in PT._fields:
            return []
        base = self._base_url(site)
        fiches = []
        for g in PT._read_group(self._produits_dom(site) + [('pool_brand_id', '!=', False)], ['pool_brand_id'], ['__count']):
            brand, nb = g
            produits = PT.search(self._produits_dom(site) + [('pool_brand_id', '=', brand.id)], limit=200)
            cats = sorted(set(produits.mapped('public_categ_ids.name')))[:12]
            fiches.append({'name': 'Marque %s' % brand.name, 'kind': 'marque', 'sequence': 40,
                           'url': '%s/shop?search=%s' % (base, requests.utils.quote(brand.name)),
                           'keywords': brand.name,
                           'content': 'Marque %s : %d produits sur le site. Catégories : %s.' % (
                               brand.name, nb, ', '.join(cats))})
        return fiches
