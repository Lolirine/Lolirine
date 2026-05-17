# -*- coding: utf-8 -*-
"""
scraper_scp
===========
Scraping ciblé du site SCP Europe / SCP Pool.

SCP a un site B2B (scpeurope.com) qui nécessite login pour le catalogue
détaillé, mais le site B2C (scppool.com) et les pages publiques produit
sont accessibles. On utilise :
  https://www.scppool.com/search?q={query}
ou la version localisée :
  https://www.scpeurope.com/.../search?q={query}

Si login requis → fallback DDG site:scpeurope.com.
"""
import logging
from urllib.parse import quote, urljoin

from .scraper_base import ScraperBase

_logger = logging.getLogger(__name__)


class ScraperSCP(ScraperBase):
    """Scraper spécifique SCP Europe."""

    name = "scp"
    domain = "scpeurope.com"
    candidate_bases = [
        "https://www.scpeurope.com",
        "https://www.scppool.com",
    ]

    def search(self, product, max_results=5):
        from bs4 import BeautifulSoup

        query = self._normalize_query(product)
        if not query:
            return []

        results = []
        seen_urls = set()

        for base_url in self.candidate_bases:
            if len(results) >= max_results:
                break

            search_url = f"{base_url}/search?q={quote(query)}"
            try:
                resp = self._get(search_url)
                if resp.status_code != 200:
                    continue
            except Exception as e:
                _logger.debug("SCP search failed (%s): %s", base_url, e)
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Sélecteurs typiques de fiches produit
            product_links = []
            for a in soup.select(
                'a.product-card, a.product-item-link, a.product-tile, '
                'a.search-result__title, a[data-product-link]'
            ):
                href = a.get('href', '')
                if href:
                    full = urljoin(base_url, href)
                    if full not in product_links:
                        product_links.append(full)
                if len(product_links) >= 3:
                    break

            # Scraper chaque fiche
            for page_url in product_links:
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
                        if img_url in seen_urls:
                            continue
                        seen_urls.add(img_url)
                        downloaded = self._download_image(img_url)
                        if not downloaded:
                            continue
                        results.append({
                            'image_url': img_url,
                            'source_url': page_url,
                            'source_name': 'SCP Europe',
                            'image_data': downloaded['image_data'],
                            'width': downloaded['width'],
                            'height': downloaded['height'],
                        })
                        if len(results) >= max_results:
                            break
                except Exception as e:
                    _logger.debug("SCP page scrape failed %s: %s", page_url, e)

        return results
