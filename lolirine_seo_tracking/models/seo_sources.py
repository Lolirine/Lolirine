# -*- coding: utf-8 -*-
"""Classification des sources de trafic (pur Python, sans ORM, testable seul).

classify(referrer, landing_url, site_hosts) -> dict(source_type, source_name,
search_query, referrer_host)
"""
import re
from urllib.parse import urlsplit, parse_qs

SOURCE_TYPES = [
    ('organic', 'Moteur de recherche'),
    ('ai', 'Assistant IA'),
    ('social', 'Réseau social'),
    ('email', 'E-mail'),
    ('paid', 'Publicité'),
    ('referral', 'Site référent'),
    ('direct', 'Direct / inconnu'),
    ('internal', 'Navigation interne'),
]

# (motif d'hôte, nom affiché, paramètre de requête éventuel)
SEARCH_ENGINES = [
    (r'(^|\.)google\.[a-z.]+$', 'Google', 'q'),
    (r'^com\.google\.android\.googlequicksearchbox$', 'Google', None),
    (r'(^|\.)bing\.com$', 'Bing', 'q'),
    (r'(^|\.)search\.yahoo\.[a-z.]+$', 'Yahoo', 'p'),
    (r'(^|\.)yahoo\.[a-z.]+$', 'Yahoo', 'p'),
    (r'(^|\.)duckduckgo\.com$', 'DuckDuckGo', 'q'),
    (r'(^|\.)ecosia\.org$', 'Ecosia', 'q'),
    (r'(^|\.)qwant\.com$', 'Qwant', 'q'),
    (r'(^|\.)search\.brave\.com$', 'Brave Search', 'q'),
    (r'(^|\.)startpage\.com$', 'Startpage', 'query'),
    (r'(^|\.)yandex\.[a-z.]+$', 'Yandex', 'text'),
    (r'(^|\.)ya\.ru$', 'Yandex', 'text'),
    (r'(^|\.)baidu\.com$', 'Baidu', 'wd'),
    (r'(^|\.)lilo\.org$', 'Lilo', 'q'),
    (r'(^|\.)search\.aol\.[a-z.]+$', 'AOL', 'q'),
    (r'(^|\.)ask\.com$', 'Ask', 'q'),
    (r'(^|\.)seznam\.cz$', 'Seznam', 'q'),
    (r'(^|\.)naver\.com$', 'Naver', 'query'),
    (r'(^|\.)petalsearch\.com$', 'Petal Search', 'query'),
    (r'(^|\.)mojeek\.com$', 'Mojeek', 'q'),
]

AI_ASSISTANTS = [
    (r'(^|\.)chatgpt\.com$', 'ChatGPT'),
    (r'(^|\.)chat\.openai\.com$', 'ChatGPT'),
    (r'(^|\.)perplexity\.ai$', 'Perplexity'),
    (r'(^|\.)gemini\.google\.com$', 'Gemini'),
    (r'(^|\.)bard\.google\.com$', 'Gemini'),
    (r'(^|\.)copilot\.microsoft\.com$', 'Copilot'),
    (r'(^|\.)claude\.ai$', 'Claude'),
    (r'(^|\.)chat\.mistral\.ai$', 'Le Chat (Mistral)'),
    (r'(^|\.)you\.com$', 'You.com'),
    (r'(^|\.)phind\.com$', 'Phind'),
    (r'(^|\.)deepseek\.com$', 'DeepSeek'),
    (r'(^|\.)meta\.ai$', 'Meta AI'),
    (r'(^|\.)grok\.com$', 'Grok'),
]

SOCIALS = [
    (r'(^|\.)facebook\.com$', 'Facebook'),
    (r'(^|\.)fb\.me$', 'Facebook'),
    (r'(^|\.)instagram\.com$', 'Instagram'),
    (r'(^|\.)linkedin\.com$', 'LinkedIn'),
    (r'(^|\.)lnkd\.in$', 'LinkedIn'),
    (r'(^|\.)youtube\.com$', 'YouTube'),
    (r'(^|\.)youtu\.be$', 'YouTube'),
    (r'(^|\.)tiktok\.com$', 'TikTok'),
    (r'(^|\.)pinterest\.[a-z.]+$', 'Pinterest'),
    (r'(^|\.)pin\.it$', 'Pinterest'),
    (r'(^|\.)(twitter|x)\.com$', 'X / Twitter'),
    (r'^t\.co$', 'X / Twitter'),
    (r'(^|\.)reddit\.com$', 'Reddit'),
    (r'(^|\.)whatsapp\.com$', 'WhatsApp'),
    (r'^wa\.me$', 'WhatsApp'),
    (r'(^|\.)threads\.net$', 'Threads'),
    (r'(^|\.)snapchat\.com$', 'Snapchat'),
]

WEBMAILS = [
    (r'^mail\.google\.com$', 'Gmail'),
    (r'(^|\.)outlook\.(live|office|office365)\.com$', 'Outlook'),
    (r'^mail\.yahoo\.[a-z.]+$', 'Yahoo Mail'),
    (r'(^|\.)gmx\.[a-z.]+$', 'GMX'),
    (r'(^|\.)proton\.me$', 'Proton Mail'),
    (r'(^|\.)webmail\.', 'Webmail'),
]

PAID_CLICK_IDS = {
    'gclid': 'Google Ads', 'gbraid': 'Google Ads', 'wbraid': 'Google Ads',
    'msclkid': 'Microsoft Ads', 'fbclid': None, 'ttclid': 'TikTok Ads',
    'li_fat_id': 'LinkedIn Ads',
}
PAID_MEDIUMS = {'cpc', 'ppc', 'paid', 'paidsearch', 'paid_search', 'paid-social',
                'paid_social', 'paidsocial', 'cpm', 'display', 'ads'}

BOT_RE = re.compile(
    r'bot|crawl|spider|slurp|facebookexternalhit|bingpreview|mediapartners|'
    r'lighthouse|pagespeed|headless|python-requests|curl|wget|httpclient|'
    r'semrush|ahrefs|mj12|dataforseo|screaming frog|gptbot|chatgpt-user|'
    r'oai-searchbot|perplexitybot|claudebot|claude-user|bytespider|ccbot|'
    r'applebot|petalbot|yandex|baiduspider|duckduckbot|seznambot',
    re.I)

BOT_NAMES = [
    ('googlebot', 'Googlebot'), ('adsbot-google', 'Google Ads bot'),
    ('google-inspectiontool', 'Google Search Console'),
    ('bingbot', 'Bingbot'), ('duckduckbot', 'DuckDuckBot'),
    ('yandex', 'Yandex'), ('baiduspider', 'Baidu'), ('applebot', 'Applebot'),
    ('gptbot', 'OpenAI GPTBot'), ('oai-searchbot', 'OpenAI SearchBot'),
    ('chatgpt-user', 'ChatGPT (utilisateur)'), ('perplexitybot', 'PerplexityBot'),
    ('claudebot', 'ClaudeBot'), ('claude-user', 'Claude (utilisateur)'),
    ('ahrefs', 'Ahrefs'), ('semrush', 'Semrush'), ('mj12', 'Majestic'),
    ('petalbot', 'PetalBot'), ('facebookexternalhit', 'Facebook'),
    ('bytespider', 'ByteDance'), ('ccbot', 'Common Crawl'),
]


def host_of(url):
    if not url:
        return ''
    url = url.strip()
    if url.startswith('android-app://'):
        return url[len('android-app://'):].split('/')[0].lower()
    try:
        host = urlsplit(url).hostname or ''
    except ValueError:
        return ''
    return host.lower()


def _match(host, table):
    for row in table:
        if re.search(row[0], host):
            return row
    return None


def bot_name(user_agent):
    ua = (user_agent or '').lower()
    for needle, name in BOT_NAMES:
        if needle in ua:
            return name
    return 'Autre robot' if BOT_RE.search(ua) else ''


def is_bot(user_agent):
    return bool(BOT_RE.search(user_agent or ''))


def device_of(user_agent):
    ua = (user_agent or '').lower()
    if 'ipad' in ua or 'tablet' in ua or ('android' in ua and 'mobile' not in ua):
        return 'tablet'
    if 'mobi' in ua or 'iphone' in ua or 'android' in ua:
        return 'mobile'
    return 'desktop'


def _first(qs, key):
    val = qs.get(key)
    return (val[0] if val else '').strip()


def classify(referrer, landing_url, site_hosts):
    """Retourne la source d'une ENTRÉE sur le site."""
    site_hosts = {h.lower() for h in (site_hosts or []) if h}
    try:
        qs = parse_qs(urlsplit(landing_url or '').query)
    except ValueError:
        qs = {}
    utm_source = _first(qs, 'utm_source')
    utm_medium = _first(qs, 'utm_medium').lower()
    utm_campaign = _first(qs, 'utm_campaign')
    ref_host = host_of(referrer)
    res = {
        'referrer_host': ref_host[:128],
        'utm_source': utm_source[:128],
        'utm_medium': utm_medium[:64],
        'utm_campaign': utm_campaign[:128],
        'search_query': '',
        'source_type': 'direct',
        'source_name': '',
    }

    # 1. Publicité (identifiant de clic ou utm_medium payant)
    for key, name in PAID_CLICK_IDS.items():
        if key in qs:
            if key == 'fbclid' and utm_medium not in PAID_MEDIUMS:
                break  # fbclid seul = partage social organique
            res.update(source_type='paid', source_name=name or 'Meta Ads')
            return res
    if utm_medium in PAID_MEDIUMS:
        res.update(source_type='paid', source_name=utm_source or 'Publicité')
        return res

    # 2. Campagnes taguées
    if utm_medium in ('email', 'e-mail', 'newsletter', 'mail'):
        res.update(source_type='email', source_name=utm_source or 'E-mail')
        return res
    if utm_medium in ('social', 'social-network', 'social_media', 'sm'):
        res.update(source_type='social', source_name=utm_source or 'Réseau social')
        return res

    # 3. Référent
    if ref_host and ref_host in site_hosts:
        res['source_type'] = 'internal'
        return res
    if ref_host:
        row = _match(ref_host, AI_ASSISTANTS)
        if row:
            res.update(source_type='ai', source_name=row[1])
            return res
        row = _match(ref_host, WEBMAILS)
        if row:
            res.update(source_type='email', source_name=row[1])
            return res
        row = _match(ref_host, SEARCH_ENGINES)
        if row:
            res.update(source_type='organic', source_name=row[1])
            if row[2]:
                try:
                    rq = parse_qs(urlsplit(referrer).query)
                    res['search_query'] = _first(rq, row[2])[:255]
                except ValueError:
                    pass
            return res
        row = _match(ref_host, SOCIALS)
        if row:
            res.update(source_type='social', source_name=row[1])
            return res
        res.update(source_type='referral',
                   source_name=re.sub(r'^(www|m|l|lm)\.', '', ref_host)[:128])
        return res

    # 4. utm_source sans référent (ChatGPT ajoute utm_source=chatgpt.com)
    if utm_source:
        src = utm_source.lower()
        row = _match(src, AI_ASSISTANTS) or (
            ('', 'ChatGPT') if 'chatgpt' in src else None)
        if row:
            res.update(source_type='ai', source_name=row[1])
            return res
        row = _match(src, SOCIALS)
        if row or src in ('facebook', 'instagram', 'linkedin', 'youtube', 'tiktok'):
            res.update(source_type='social', source_name=row[1] if row else utm_source)
            return res
        res.update(source_type='referral', source_name=utm_source[:128])
    return res


LANG_PREFIX_RE = re.compile(r'^/((?:en|nl|fr|de|es|it)(?:_[A-Z]{2})?)(?=/|$)')


def split_lang(path):
    """'/nl_BE/shop/x' -> ('nl_BE', '/shop/x')"""
    m = LANG_PREFIX_RE.match(path or '/')
    if m:
        rest = path[m.end():] or '/'
        return m.group(1), rest
    return '', path or '/'


PRODUCT_RE = re.compile(r'^/shop/(?!category/|cart|checkout|payment|confirmation|'
                        r'address|wishlist|compare|page/)[^/]*-(\d+)/?$')


def page_type_of(path):
    """Retourne (page_type, product_template_id|None) pour un chemin sans langue."""
    p = (path or '/').rstrip('/') or '/'
    if p == '/':
        return 'home', None
    if p.startswith('/shop/confirmation'):
        return 'confirmation', None
    if p.startswith(('/shop/cart', '/shop/checkout', '/shop/address',
                     '/shop/payment', '/shop/extra_info')):
        return 'checkout', None
    m = PRODUCT_RE.match(p)
    if m:
        return 'product', int(m.group(1))
    if p.startswith(('/shop/category/', '/boutique')):
        return 'category', None
    if p == '/shop' or p.startswith('/shop/page/'):
        return 'shop', None
    if p.startswith('/guides'):
        return 'guide', None
    if p.startswith('/website/search'):
        return 'search', None
    return 'page', None
