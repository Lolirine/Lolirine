# -*- coding: utf-8 -*-
"""
pool_image_search_session
=========================
Une session = une campagne de recherche pour un lot de produits.

Permet de :
- Lancer un batch et suivre la progression
- Garder l'historique des recherches
- Filtrer les candidats par session
- Relancer/réessayer en cas d'échec
"""
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PoolImageSearchSession(models.Model):
    _name = 'pool.image.search.session'
    _description = 'Session de recherche d\'images produits'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(string='Nom', compute='_compute_display_name', store=True)
    name = fields.Char(string='Référence', default='Nouvelle session')
    notes = fields.Text(string='Notes')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('queued', 'En file'),
        ('running', 'En cours'),
        ('done', 'Terminée'),
        ('cancelled', 'Annulée'),
        ('failed', 'Échec'),
    ], string='Statut', default='draft', tracking=True)

    # Produits ciblés
    product_ids = fields.Many2many(
        'product.template',
        'pool_image_search_session_product_rel',
        'session_id', 'product_id',
        string='Produits ciblés',
    )
    product_count = fields.Integer(string='Nb produits', compute='_compute_counts', store=True)

    # Candidats générés
    candidate_ids = fields.One2many(
        'pool.image.search.candidate', 'session_id',
        string='Candidats trouvés'
    )
    candidate_count = fields.Integer(string='Nb candidats', compute='_compute_counts', store=True)
    auto_validated_count = fields.Integer(string='Auto-validés', compute='_compute_counts', store=True)
    pending_count = fields.Integer(string='À valider', compute='_compute_counts', store=True)
    rejected_count = fields.Integer(string='Rejetés', compute='_compute_counts', store=True)

    # Configuration
    max_candidates_per_product = fields.Integer(string='Max candidats/produit', default=5)
    auto_validate_threshold = fields.Float(
        string='Seuil auto-validation (%)', default=90.0,
        help="Si le top-1 a un score >= ce seuil, validation auto"
    )
    enable_bg_removal = fields.Boolean(string='Background removal (rembg)', default=True)
    enable_webp = fields.Boolean(string='Conversion WebP', default=True)
    max_image_size = fields.Integer(string='Taille max (px)', default=1200)
    enable_phash_dedup = fields.Boolean(string='Détection doublons (phash)', default=True)

    # Progression
    progress_done = fields.Integer(string='Produits traités', default=0)
    progress_total = fields.Integer(string='Total produits', default=0)
    progress_percent = fields.Float(string='Progression (%)', compute='_compute_progress')

    start_date = fields.Datetime(string='Début')
    end_date = fields.Datetime(string='Fin')
    duration_seconds = fields.Integer(string='Durée (s)', compute='_compute_duration')

    error_log = fields.Text(string='Log d\'erreurs')

    @api.depends('name', 'create_date')
    def _compute_display_name(self):
        for rec in self:
            if rec.create_date:
                rec.display_name = f"{rec.name or 'Session'} - {rec.create_date.strftime('%Y-%m-%d %H:%M')}"
            else:
                rec.display_name = rec.name or 'Nouvelle session'

    @api.depends('product_ids', 'candidate_ids', 'candidate_ids.state')
    def _compute_counts(self):
        for rec in self:
            rec.product_count = len(rec.product_ids)
            rec.candidate_count = len(rec.candidate_ids)
            rec.auto_validated_count = len(rec.candidate_ids.filtered(
                lambda c: c.state in ('main', 'gallery') and c.auto_validated
            ))
            rec.pending_count = len(rec.candidate_ids.filtered(
                lambda c: c.state == 'pending'
            ))
            rec.rejected_count = len(rec.candidate_ids.filtered(
                lambda c: c.state == 'rejected'
            ))

    @api.depends('progress_done', 'progress_total')
    def _compute_progress(self):
        for rec in self:
            if rec.progress_total:
                rec.progress_percent = 100.0 * rec.progress_done / rec.progress_total
            else:
                rec.progress_percent = 0.0

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                delta = rec.end_date - rec.start_date
                rec.duration_seconds = int(delta.total_seconds())
            else:
                rec.duration_seconds = 0

    # --- Actions ---

    def action_queue(self):
        """Met la session en file d'attente. Le cron la prendra."""
        for session in self:
            if not session.product_ids:
                raise models.ValidationError("Aucun produit sélectionné.")
            session.write({
                'state': 'queued',
                'progress_total': len(session.product_ids),
                'progress_done': 0,
            })
        return True

    def action_run_now(self):
        """Lance la session immédiatement (synchrone, pour test)."""
        self.ensure_one()
        self._run_session()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pool.image.search.session',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        for session in self:
            session.state = 'cancelled'

    def action_view_candidates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Candidats - {self.display_name}',
            'res_model': 'pool.image.search.candidate',
            'view_mode': 'kanban,list,form',
            'domain': [('session_id', '=', self.id)],
            'context': {
                'default_session_id': self.id,
                'search_default_pending': 1,
                'search_default_group_by_product': 1,
            },
        }

    def action_view_products(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Produits - {self.display_name}',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.product_ids.ids)],
        }

    def action_apply_all_main(self):
        """Applique en masse toutes les images marquées 'main' sur les produits."""
        self.ensure_one()
        applied = 0
        for cand in self.candidate_ids.filtered(lambda c: c.state == 'main' and not c.applied):
            try:
                cand.apply_to_product()
                applied += 1
            except Exception as e:
                _logger.error("Apply failed for candidate %s: %s", cand.id, e)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Application terminée',
                'message': f'{applied} image(s) appliquée(s)',
                'type': 'success',
            },
        }

    # --- Cron entry point ---

    @api.model
    def cron_process_queue(self):
        """Cron : prend les sessions queued et les exécute une par une."""
        sessions = self.search([('state', '=', 'queued')], limit=1, order='create_date asc')
        for session in sessions:
            try:
                session._run_session()
            except Exception as e:
                _logger.exception("Cron session %s failed", session.id)
                session.write({
                    'state': 'failed',
                    'error_log': str(e),
                    'end_date': fields.Datetime.now(),
                })

    def _run_session(self):
        """Exécution principale d'une session."""
        from ..services.scraper_orchestrator import ScraperOrchestrator
        from ..services.image_processor import ImageProcessor

        self.ensure_one()
        self.write({
            'state': 'running',
            'start_date': fields.Datetime.now(),
        })

        orchestrator = ScraperOrchestrator(self.env)
        processor = ImageProcessor(
            enable_bg_removal=self.enable_bg_removal,
            enable_webp=self.enable_webp,
            max_size=self.max_image_size,
        )

        errors = []
        for idx, product in enumerate(self.product_ids):
            if self.state == 'cancelled':
                break
            try:
                self._process_product(product, orchestrator, processor)
            except Exception as e:
                _logger.exception("Product %s failed", product.id)
                errors.append(f"{product.display_name}: {e}")
            # Commit incrémental pour ne pas tout perdre en cas d'interruption
            self.progress_done = idx + 1
            if (idx + 1) % 10 == 0:
                self.env.cr.commit()

        self.write({
            'state': 'done' if self.state != 'cancelled' else 'cancelled',
            'end_date': fields.Datetime.now(),
            'error_log': '\n'.join(errors) if errors else False,
        })

    def _process_product(self, product, orchestrator, processor):
        """Traite un produit : scrape, post-process, score, auto-valide si possible."""
        Candidate = self.env['pool.image.search.candidate']

        # 1. Scraping
        raw_candidates = orchestrator.find_images(
            product=product,
            max_results=self.max_candidates_per_product,
        )

        if not raw_candidates:
            _logger.info("No candidates for product %s", product.display_name)
            return

        # 2. Post-processing + scoring
        processed = []
        for raw in raw_candidates:
            try:
                result = processor.process(raw['image_data'])
                if not result:
                    continue
                raw.update(result)
                processed.append(raw)
            except Exception as e:
                _logger.warning("Process failed for %s: %s", raw.get('source_url'), e)

        if not processed:
            return

        # 3. Déduplication par phash si activée
        if self.enable_phash_dedup:
            processed = self._dedupe_by_phash(processed)

        # 4. Création des candidats Odoo
        created = []
        for rank, raw in enumerate(sorted(processed, key=lambda x: -x['score']), start=1):
            cand = Candidate.create({
                'session_id': self.id,
                'product_id': product.id,
                'source_name': raw.get('source_name'),
                'source_url': raw.get('source_url'),
                'image_url': raw.get('image_url'),
                'image_main': raw.get('image_processed'),
                'image_thumb': raw.get('image_thumb'),
                'image_raw': raw.get('image_raw'),
                'image_no_bg': raw.get('image_no_bg'),
                'score': raw['score'],
                'width': raw.get('width'),
                'height': raw.get('height'),
                'phash': raw.get('phash'),
                'rank': rank,
                'state': 'pending',
            })
            created.append(cand)

        # 5. Auto-validation top-1 si seuil atteint
        if created and created[0].score >= self.auto_validate_threshold:
            created[0].write({
                'state': 'main',
                'auto_validated': True,
            })
            try:
                created[0].apply_to_product()
            except Exception as e:
                _logger.warning("Auto-apply failed for %s: %s", created[0].id, e)

    def _dedupe_by_phash(self, candidates, threshold=5):
        """Élimine les candidats trop similaires (hamming distance < threshold)."""
        try:
            import imagehash
        except ImportError:
            return candidates

        kept = []
        for cand in candidates:
            phash = cand.get('phash')
            if not phash:
                kept.append(cand)
                continue
            cand_hash = imagehash.hex_to_hash(phash)
            is_dup = False
            for k in kept:
                if not k.get('phash'):
                    continue
                k_hash = imagehash.hex_to_hash(k['phash'])
                if cand_hash - k_hash < threshold:
                    is_dup = True
                    break
            if not is_dup:
                kept.append(cand)
        return kept
