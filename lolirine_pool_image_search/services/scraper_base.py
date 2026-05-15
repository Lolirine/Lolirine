# -*- coding: utf-8 -*-
"""
scraper_base
============
Classe de base pour tous les scrapers de sources.

Chaque scraper concret implémente :
- search(product, max_results) : retourne liste de dicts
  {
    'image_url': str,
    'source_url': str,
    'source_name': str,
    'image_data': bytes,
    'width': int,
    'height': int,
  }
"""
import io
import logging
import re
import time
from urllib.parse import urlparse, urljoin

_logger = logging.getLogger(__name__)


# Hashs perceptuels de logos/icônes connus à blacklister
BLACKLIST_PHASHES = {
    # À enrichir au fil du temps depuis les rejets manuels
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class ScraperBase:
    """Classe de base. À sous-classer pour chaque source."""

    name = "base"
    domain = ""
    min_image_size = 400  # px (min largeur ou hauteur)
    request_timeout = 15  # secondes
    throttle_seconds = 1.0  # délai entre requêtes

    def __init__(self, env, source_record=None):
        self.env = env
        self.source_record = source_record
        self._last_request_time = 0

    def _throttle(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.throttle_seconds:
            time.sleep(self.throttle_seconds - elapsed)
        self._last_request_time = time.time()

    def _get(self, url, **kwargs):
        """GET avec throttling et User-Agent."""
        import requests
        self._throttle()
        headers = kwargs.pop('headers', {})
        headers.setdefault('User-Agent', USER_AGENT)
        headers.setdefault('Accept-Language', 'fr-BE,fr;q=0.9,en;q=0.8')
        return requests.get(url, headers=headers, timeout=self.request_timeout, **kwargs)

    def _download_image(self, url):
        """Télécharge une image. Retourne (bytes, width, height) ou None."""
        from PIL import Image
        try:
            r = self._get(url)
            if r.status_code != 200:
                return None
            content_type = r.headers.get('content-type', '').lower()
            if 'image' not in content_type and not any(
                url.lower().endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif')
            ):
                return None
            if len(r.content) < 5000:  # < 5 KB = probablement une icône
                return None
            img = Image.open(io.BytesIO(r.content))
            w, h = img.size
            if w < self.min_image_size or h < self.min_image_size:
                return None
            return {
                'image_data': r.content,
                'width': w,
                'height': h,
            }
        except Exception as e:
            _logger.debug("Download failed %s: %s", url, e)
            return None

    def _extract_images_from_html(self, html, base_url, max_results=10):
        """Extrait les URLs d'images probables d'une page HTML."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        urls = []
        seen = set()

        # 1. og:image (priorité haute)
        for meta in soup.find_all('meta', property=re.compile(r'og:image')):
            content = meta.get('content')
            if content:
                full = urljoin(base_url, content)
                if full not in seen:
                    urls.append(full)
                    seen.add(full)

        # 2. <link rel="image_src">
        for link in soup.find_all('link', rel='image_src'):
            href = link.get('href')
            if href:
                full = urljoin(base_url, href)
                if full not in seen:
                    urls.append(full)
                    seen.add(full)

        # 3. <img> avec des classes/attributs produit
        product_img_selectors = [
            'img.product-image', 'img.product-photo', 'img.main-image',
            'img.gallery-image', 'img.zoom-image', 'img[itemprop="image"]',
            '.product-gallery img', '.product-media img', '.product-photos img',
            '.fotorama__img', '.swiper-slide img', '.gallery img',
        ]
        for sel in product_img_selectors:
            for img in soup.select(sel):
                src = img.get('data-src') or img.get('data-zoom-image') or img.get('src')
                if src:
                    full = urljoin(base_url, src)
                    if full not in seen:
                        urls.append(full)
                        seen.add(full)

        # 4. Toutes les <img> en fallback (filtré ensuite par taille)
        for img in soup.find_all('img'):
            src = img.get('data-src') or img.get('src')
            if not src or src.startswith('data:'):
                continue
            full = urljoin(base_url, src)
            # Exclure les patterns évidents de logos/icônes
            if any(pat in full.lower() for pat in ('logo', 'icon', 'favicon', 'sprite', 'placeholder')):
                continue
            if full not in seen:
                urls.append(full)
                seen.add(full)
            if len(urls) >= max_results * 3:
                break

        return urls[:max_results * 3]

    def _normalize_query(self, product):
        """Construit la requête de recherche depuis le produit."""
        parts = []
        # Référence prioritaire (default_code = SKU)
        if product.default_code:
            parts.append(product.default_code.strip())
        # Nom du produit nettoyé
        name = product.name or ''
        name = re.sub(r'\s+', ' ', name).strip()
        parts.append(name)
        return ' '.join(parts)

    def search(self, product, max_results=5):
        """À implémenter par les sous-classes."""
        raise NotImplementedError
