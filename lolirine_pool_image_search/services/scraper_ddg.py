# -*- coding: utf-8 -*-
"""
scraper_ddg
===========
Recherche via DuckDuckGo HTML (pas d'API key, robuste, gratuit).

Mode `ddg_site` : restreint la recherche à un domaine via `site:domain`.
Récupère les URLs de résultats puis scrape chaque page pour extraire
les images produit (via og:image et selectors produit).

Avantages :
- Aucune clé API
- Couvre tous les sites fournisseurs/marques d'un coup
- Pas de quota strict (mais throttling conseillé)
"""
import logging
import re
from urllib.parse import quote, urlparse

from .scraper_base import ScraperBase

_logger = logging.getLogger(__name__)


class ScraperDuckDuckGo(ScraperBase):
    """Scraper générique DuckDuckGo HTML."""

    name = "duckduckgo"
    base_url = "https://html.duckduckgo.com/html/"

    # Domaines à interroger en priorité (top 5 pour limiter le temps)
    TARGET_DOMAINS = [
        'fluidra.com',
        'scpeurope.com',
        'pentair.com',
        'hayward.com',
        'zodiac-poolcare.com',
    ]

    def search(self, product, max_results=5):
        """Recherche multi-domaines."""
        from bs4 import BeautifulSoup

        query_base = self._normalize_query(product)
        if not query_base:
            return []

        results = []
        seen_image_urls = set()

        # On essaye chaque domaine cible
        for domain in self.TARGET_DOMAINS:
            if len(results) >= max_results:
                break

            query = f"{query_base} site:{domain}"
            try:
                resp = self._get(self.base_url, params={'q': query})
                if resp.status_code != 200:
                    continue
            except Exception as e:
                _logger.debug("DDG search failed for %s: %s", domain, e)
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Extraire les URLs des résultats
            result_urls = []
            for a in soup.select('a.result__a, a.result__url'):
                href = a.get('href', '')
                # DDG utilise parfois des URLs de redirection
                m = re.search(r'uddg=([^&]+)', href)
                if m:
                    from urllib.parse import unquote
                    href = unquote(m.group(1))
                if href.startswith('http'):
                    result_urls.append(href)
                if len(result_urls) >= 3:
                    break

            # Visiter chaque page de résultat et extraire les images
            for page_url in result_urls:
                if len(results) >= max_results:
                    break
                try:
                    page_resp = self._get(page_url)
                    if page_resp.status_code != 200:
                        continue
                    img_urls = self._extract_images_from_html(
                        page_resp.text, page_url, max_results=max_results,
                    )
                    for img_url in img_urls:
                        if img_url in seen_image_urls:
                            continue
                        seen_image_urls.add(img_url)
                        downloaded = self._download_image(img_url)
                        if not downloaded:
                            continue
                        results.append({
                            'image_url': img_url,
                            'source_url': page_url,
                            'source_name': domain,
                            'image_data': downloaded['image_data'],
                            'width': downloaded['width'],
                            'height': downloaded['height'],
                        })
                        if len(results) >= max_results:
                            break
                except Exception as e:
                    _logger.debug("Page scrape failed %s: %s", page_url, e)

        return results
