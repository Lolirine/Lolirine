# -*- coding: utf-8 -*-
"""
scraper_fluidra
===============
Scraping ciblé du site Fluidra (et fluidrapro).

Fluidra n'expose pas d'API publique mais le site B2C a une recherche
fonctionnelle. On utilise l'URL :
  https://www.fluidra.com/search?q={query}

Pour les fiches produit, on parse les images via og:image et le
sélecteur de gallery produit.
"""
import logging
from urllib.parse import quote, urljoin

from .scraper_base import ScraperBase

_logger = logging.getLogger(__name__)


class ScraperFluidra(ScraperBase):
    """Scraper spécifique Fluidra."""

    name = "fluidra"
    domain = "fluidra.com"
    base_url = "https://www.fluidra.com"

    def search(self, product, max_results=5):
        from bs4 import BeautifulSoup

        query = self._normalize_query(product)
        if not query:
            return []

        results = []
        seen_urls = set()

        # 1. Recherche sur le site
        search_url = f"{self.base_url}/search?q={quote(query)}"
        try:
            resp = self._get(search_url)
            if resp.status_code != 200:
                return []
        except Exception as e:
            _logger.debug("Fluidra search failed: %s", e)
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 2. Récupérer les URLs des fiches produit dans les résultats
        product_links = []
        for a in soup.select('a.product-card__link, a.search-result__link, a.product-tile'):
            href = a.get('href', '')
            if href:
                full = urljoin(self.base_url, href)
                if full not in product_links:
                    product_links.append(full)
            if len(product_links) >= 3:
                break

        # Fallback : tous les liens de la page contenant /product/ ou /producto/
        if not product_links:
            for a in soup.find_all('a', href=True):
                href = a['href']
                if any(p in href for p in ('/product/', '/producto/', '/produits/', '/products/')):
                    full = urljoin(self.base_url, href)
                    if full not in product_links:
                        product_links.append(full)
                if len(product_links) >= 3:
                    break

        # 3. Scraper chaque fiche
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
                        'source_name': 'Fluidra',
                        'image_data': downloaded['image_data'],
                        'width': downloaded['width'],
                        'height': downloaded['height'],
                    })
                    if len(results) >= max_results:
                        break
            except Exception as e:
                _logger.debug("Fluidra page scrape failed %s: %s", page_url, e)

        return results
