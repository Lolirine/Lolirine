# -*- coding: utf-8 -*-
"""
scraper_orchestrator
====================
Orchestre les scrapers par priorité, calcule un score de confiance global,
et retourne les meilleurs candidats par produit.

Score (0–100) = somme pondérée de :
- Qualité résolution (30 pts)  : 500=10 / 800=20 / 1200+=30
- Source fiable (25 pts)       : Fluidra/SCP direct = 25, autre = 10–20
- Ratio packshot (15 pts)      : ratio 0.8–1.25 = 15
- Présence ref dans URL (15 pts): SKU exact dans source_url = 15
- Détection fond clair (10 pts): histogramme du fond uniforme = 10
- Détection texte parasite (5 pts) : faible variance = 5
"""
import logging
import re

_logger = logging.getLogger(__name__)


class ScraperOrchestrator:
    """Orchestre les scrapers actifs et score les résultats."""

    def __init__(self, env):
        self.env = env
        self._scrapers = None

    def _get_scrapers(self):
        """Instancie les scrapers actifs depuis pool.image.search.source."""
        if self._scrapers is not None:
            return self._scrapers

        from .scraper_fluidra import ScraperFluidra
        from .scraper_scp import ScraperSCP
        from .scraper_ddg import ScraperDuckDuckGo

        SCRAPER_REGISTRY = {
            'fluidra.com': ScraperFluidra,
            'scpeurope.com': ScraperSCP,
            'duckduckgo': ScraperDuckDuckGo,
        }

        sources = self.env['pool.image.search.source'].search(
            [('active', '=', True)], order='priority'
        )
        scrapers = []
        for src in sources:
            klass = None
            if src.strategy == 'direct_search':
                klass = SCRAPER_REGISTRY.get(src.domain)
            elif src.strategy == 'ddg_site':
                klass = ScraperDuckDuckGo
            elif src.strategy == 'brand_lookup':
                klass = ScraperDuckDuckGo  # fallback DDG pour les marques
            if klass and src.is_available():
                scrapers.append(klass(self.env, source_record=src))

        # Fallback minimal si aucune source configurée
        if not scrapers:
            scrapers = [ScraperDuckDuckGo(self.env)]

        self._scrapers = scrapers
        return scrapers

    def find_images(self, product, max_results=5):
        """Lance les scrapers en cascade jusqu'à obtenir max_results."""
        all_results = []
        seen_hashes = set()

        # Routing supplier-aware : on commence par le scraper du fournisseur du produit
        scrapers = self._get_scrapers_ordered_for(product)

        supplier_ref = getattr(product, 'x_pool_supplier_ref', '') or ''
        supplier_id = getattr(product, 'x_pool_supplier_id', None)
        sup_name = supplier_id.name if supplier_id else 'unknown'
        _logger.info(
            "[%s] supplier=%s ref=%s -> scraping with %d scrapers",
            product.default_code or product.id,
            sup_name, supplier_ref,
            len(scrapers),
        )

        for scraper in scrapers:
            if len(all_results) >= max_results:
                break
            try:
                results = scraper.search(product, max_results=max_results)
            except Exception as e:
                _logger.warning("Scraper %s failed: %s", scraper.name, e)
                if scraper.source_record:
                    scraper.source_record.increment_counter(success=False)
                continue

            if scraper.source_record:
                scraper.source_record.increment_counter(success=bool(results))

            _logger.info(
                "[%s] scraper=%s -> %d raw results",
                product.default_code or product.id, scraper.name, len(results),
            )

            for r in results:
                url = r.get('image_url')
                if url in seen_hashes:
                    continue
                seen_hashes.add(url)
                r['score'] = self._score_candidate(product, r, scraper.name)
                all_results.append(r)

        all_results.sort(key=lambda x: -x.get('score', 0))
        return all_results[:max_results * 2]

    def _get_scrapers_ordered_for(self, product):
        """Réordonne les scrapers selon le fournisseur du produit."""
        from .scraper_fluidra import ScraperFluidra
        from .scraper_scp import ScraperSCP

        sup = getattr(product, 'x_pool_supplier_id', None)
        sup_name = (sup.name.lower() if sup and sup.name else '')

        scrapers = self._get_scrapers()
        if 'fluidra' in sup_name or 'sibo' in sup_name:
            head = [s for s in scrapers if isinstance(s, ScraperFluidra)]
            tail = [s for s in scrapers if not isinstance(s, ScraperFluidra)]
            return head + tail
        if 'scp' in sup_name:
            head = [s for s in scrapers if isinstance(s, ScraperSCP)]
            tail = [s for s in scrapers if not isinstance(s, ScraperSCP)]
            return head + tail
        return scrapers

    def _score_candidate(self, product, candidate, scraper_name):
        """Calcule le score de confiance 0–100."""
        score = 0.0

        # 1. Résolution (30 pts)
        w = candidate.get('width', 0)
        h = candidate.get('height', 0)
        min_dim = min(w, h) if w and h else 0
        if min_dim >= 1200:
            score += 30
        elif min_dim >= 800:
            score += 22
        elif min_dim >= 600:
            score += 15
        elif min_dim >= 400:
            score += 8

        # 2. Source fiable (25 pts)
        trusted = {
            'fluidra': 25, 'scp': 25,
            'pentair.com': 22, 'hayward': 22, 'zodiac': 22,
            'astralpool': 22, 'bwt': 22,
        }
        source_url = (candidate.get('source_url') or '').lower()
        source_name = (candidate.get('source_name') or '').lower()
        src_score = 10  # défaut
        for key, pts in trusted.items():
            if key in source_url or key in source_name:
                src_score = max(src_score, pts)
                break
        score += src_score

        # 3. Ratio packshot (15 pts)
        if w and h:
            ratio = w / float(h)
            if 0.8 <= ratio <= 1.25:
                score += 15
            elif 0.6 <= ratio <= 1.6:
                score += 8

        # 4. Référence dans URL (15 pts) - priorité à la ref supplier
        ref = (getattr(product, 'x_pool_supplier_ref', '') or '').strip()
        if not ref:
            ref = (product.default_code or '').strip()
        if ref and len(ref) >= 4:
            url_lower = (candidate.get('source_url', '') + candidate.get('image_url', '')).lower()
            # Recherche tolérante (sans tirets / espaces)
            ref_clean = re.sub(r'[\s\-_]', '', ref.lower())
            url_clean = re.sub(r'[\s\-_]', '', url_lower)
            if ref_clean in url_clean:
                score += 15
            elif ref.lower() in url_lower:
                score += 12

        # 5–6. Pénalité images obviousement parasites (en négatif)
        bad_patterns = ('thumb', 'icon', 'logo', 'sprite', 'placeholder', 'avatar')
        if any(p in (candidate.get('image_url') or '').lower() for p in bad_patterns):
            score -= 20

        # Bonus si image_url contient un mot-clé produit du nom
        name_words = re.findall(r'\b\w{4,}\b', (product.name or '').lower())
        url_lower_full = (candidate.get('image_url') or '').lower()
        matches = sum(1 for w in name_words if w in url_lower_full)
        if matches >= 2:
            score += 10
        elif matches >= 1:
            score += 5

        return max(0.0, min(100.0, score))
