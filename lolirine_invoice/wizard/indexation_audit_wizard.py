# -*- coding: utf-8 -*-
"""Wizard d'audit indexation annuelle pour les abonnements de stockage.

Ce wizard est PUREMENT INFORMATIF par défaut. Il liste les abonnements
ayant atteint leur anniversaire et calcule le nouveau loyer théorique selon
le dernier indice santé disponible. Aucune indexation n'est appliquée
automatiquement.

Workflow :
    1. Ouvrir le wizard, choisir date de référence + indice cible
    2. Cliquer "Lancer l'audit" → liste des SO éligibles avec calculs
    3. Choisir 0, sélection partielle, ou tout cocher
    4. Cliquer "Créer brouillon d'indexation" → crée un storage.indexation
       en draft (pas encore appliqué)
    5. Suite du processus dans la fiche storage.indexation
       (confirmer → notifier → appliquer)
"""

import logging
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# États d'abonnement actifs en Odoo 19 (cohérent avec storage_indexation.py)
ACTIVE_SUBSCRIPTION_STATES = ['3_progress', '4_paused', '5_renewed']

# Délai minimum depuis start_date pour qu'un SO soit éligible à indexation
MIN_AGE_MONTHS_FOR_INDEXATION = 12

# Délai minimum depuis la dernière indexation appliquée pour pouvoir réindexer
MIN_DELAY_BETWEEN_INDEXATIONS_MONTHS = 12


class LolirineIndexationAuditWizard(models.TransientModel):
    """Wizard d'audit informatif des indexations annuelles à effectuer."""
    _name = 'lolirine.indexation.audit.wizard'
    _description = "Audit indexation annuelle des abonnements"

    # ========================================================================
    # PARAMÈTRES D'AUDIT
    # ========================================================================

    target_date = fields.Date(
        string="Date de référence",
        required=True,
        default=fields.Date.today,
        help="Date à laquelle évaluer l'éligibilité des contrats. "
             "Les contrats dont la date d'anniversaire est <= à cette date "
             "et qui ont au moins 12 mois d'ancienneté seront listés."
    )

    target_index_id = fields.Many2one(
        'storage.price.index',
        string="Indice cible",
        required=True,
        domain="[('index_type', '=', 'health'), ('company_id', '=', company_id)]",
        default=lambda self: self._default_target_index(),
        help="Indice santé à utiliser pour calculer le nouveau loyer. "
             "Par défaut : le plus récent disponible."
    )

    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
        help="Audit limité à cette société (par défaut : Srl Lolirine garde-meuble)."
    )

    include_new_contracts = fields.Boolean(
        string="Afficher aussi les contrats < 12 mois",
        default=False,
        help="Si coché, les contrats trop récents pour être indexés sont "
             "tout de même listés (en lecture seule)."
    )

    # ========================================================================
    # RÉSULTATS DE L'AUDIT
    # ========================================================================

    audit_line_ids = fields.One2many(
        'lolirine.indexation.audit.line',
        'wizard_id',
        string="Lignes d'audit"
    )

    has_results = fields.Boolean(compute='_compute_stats')

    # Synthèse
    total_subscriptions = fields.Integer(
        string="Abonnements analysés",
        compute='_compute_stats'
    )
    total_pending = fields.Integer(
        string="🟢 À indexer",
        compute='_compute_stats'
    )
    total_recently_indexed = fields.Integer(
        string="🔵 Récemment indexés",
        compute='_compute_stats'
    )
    total_new = fields.Integer(
        string="⚪ Trop récents (< 12 mois)",
        compute='_compute_stats'
    )
    total_blocked = fields.Integer(
        string="🚨 Bloqués (erreur)",
        compute='_compute_stats'
    )

    # Montants potentiels
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id'
    )
    total_old_amount = fields.Monetary(
        string="Loyers actuels (mensuel)",
        compute='_compute_stats',
        currency_field='currency_id'
    )
    total_new_amount = fields.Monetary(
        string="Loyers indexés théoriques (mensuel)",
        compute='_compute_stats',
        currency_field='currency_id'
    )
    total_increase = fields.Monetary(
        string="Augmentation potentielle (mensuel)",
        compute='_compute_stats',
        currency_field='currency_id'
    )
    total_increase_yearly = fields.Monetary(
        string="Augmentation potentielle (annuel)",
        compute='_compute_stats',
        currency_field='currency_id'
    )

    # Sélection
    selected_count = fields.Integer(
        string="✓ Sélectionnés pour indexation",
        compute='_compute_selection'
    )
    selected_increase = fields.Monetary(
        string="Augmentation sur sélection (mensuel)",
        compute='_compute_selection',
        currency_field='currency_id'
    )

    # ========================================================================
    # DEFAULTS
    # ========================================================================

    @api.model
    def _default_target_index(self):
        """Récupère l'indice santé le plus récent pour la société courante."""
        return self.env['storage.price.index'].search([
            ('index_type', '=', 'health'),
            ('company_id', '=', self.env.company.id),
        ], order='date desc', limit=1)

    # ========================================================================
    # COMPUTES
    # ========================================================================

    @api.depends('audit_line_ids', 'audit_line_ids.status',
                 'audit_line_ids.old_price', 'audit_line_ids.new_price')
    def _compute_stats(self):
        for wiz in self:
            lines = wiz.audit_line_ids
            wiz.has_results = bool(lines)
            wiz.total_subscriptions = len(lines)
            wiz.total_pending = len(lines.filtered(lambda l: l.status == 'pending'))
            wiz.total_recently_indexed = len(
                lines.filtered(lambda l: l.status == 'recently_indexed')
            )
            wiz.total_new = len(lines.filtered(lambda l: l.status == 'new_contract'))
            wiz.total_blocked = len(
                lines.filtered(lambda l: l.status in ('no_base_index', 'error_calc'))
            )

            # Montants : seulement les lignes pending
            pending = lines.filtered(lambda l: l.status == 'pending')
            wiz.total_old_amount = sum(pending.mapped('old_price'))
            wiz.total_new_amount = sum(pending.mapped('new_price'))
            wiz.total_increase = wiz.total_new_amount - wiz.total_old_amount
            wiz.total_increase_yearly = wiz.total_increase * 12

    @api.depends('audit_line_ids.selected', 'audit_line_ids.old_price',
                 'audit_line_ids.new_price')
    def _compute_selection(self):
        for wiz in self:
            selected = wiz.audit_line_ids.filtered('selected')
            wiz.selected_count = len(selected)
            wiz.selected_increase = sum(
                (l.new_price - l.old_price) for l in selected
            )

    # ========================================================================
    # ACTIONS
    # ========================================================================

    def action_run_audit(self):
        """Lance l'audit : analyse tous les SO actifs et crée les lignes."""
        self.ensure_one()

        if not self.target_index_id:
            raise UserError(_("Veuillez sélectionner un indice cible."))

        # Reset des lignes existantes
        self.audit_line_ids.unlink()

        # Recherche des abonnements actifs de la société
        Subscription = self.env['sale.order'].sudo()
        subscriptions = Subscription.search([
            ('is_subscription', '=', True),
            ('subscription_state', 'in', ACTIVE_SUBSCRIPTION_STATES),
            ('company_id', '=', self.company_id.id),
        ])

        _logger.info(
            "Audit indexation : %d abonnement(s) actif(s) à analyser pour %s",
            len(subscriptions), self.company_id.name
        )

        Index = self.env['storage.price.index']
        Line = self.env['lolirine.indexation.audit.line']
        target_value = self.target_index_id.value

        line_vals_list = []

        for sub in subscriptions:
            # Date de début effective
            start_date = sub.start_date or (
                sub.date_order.date() if sub.date_order else None
            )
            if not start_date:
                _logger.warning(
                    "Abonnement %s sans start_date ni date_order — ignoré",
                    sub.name
                )
                continue

            # Calcul de l'âge en mois
            age_months = self._compute_age_in_months(start_date, self.target_date)

            # Récupération de la dernière indexation appliquée pour ce SO
            last_indexation_line = self.env['storage.indexation.line'].search([
                ('subscription_id', '=', sub.id),
                ('applied', '=', True),
            ], order='application_date desc', limit=1)

            last_indexation_date = (
                last_indexation_line.application_date.date()
                if last_indexation_line and last_indexation_line.application_date
                else None
            )

            # Détermination du statut et de la date de référence pour l'indice base
            reference_date = last_indexation_date or start_date

            if age_months < MIN_AGE_MONTHS_FOR_INDEXATION:
                status = 'new_contract'
                if not self.include_new_contracts:
                    continue  # Skip silencieusement
            elif last_indexation_date:
                # Vérifier si dernière indexation < 12 mois
                months_since_last = self._compute_age_in_months(
                    last_indexation_date, self.target_date
                )
                if months_since_last < MIN_DELAY_BETWEEN_INDEXATIONS_MONTHS:
                    status = 'recently_indexed'
                else:
                    status = 'pending'
            else:
                status = 'pending'

            # Récupération de l'indice de base (à la date de référence)
            base_index = Index.with_company(self.company_id).get_index_for_date(
                reference_date, 'health'
            )

            # Pour chaque ligne récurrente du SO
            for sol in sub.order_line:
                if sol.display_type in ('line_section', 'line_note'):
                    continue
                if not sol.product_id:
                    continue
                # Filtrer aux lignes récurrentes (vraies lignes d'abonnement).
                # NE PAS utiliser sub.is_subscription comme fallback : sinon les
                # frais de dossier (recurring_invoice=False) seraient considérés
                # comme récurrents juste parce qu'ils sont sur un SO d'abonnement.
                if 'recurring_invoice' in sol.product_id._fields:
                    is_recurring = bool(sol.product_id.recurring_invoice)
                elif hasattr(sol, 'temporal_type'):
                    is_recurring = sol.temporal_type == 'subscription'
                elif hasattr(sol, 'recurrence_id') and sol.recurrence_id:
                    is_recurring = True
                else:
                    # Par défaut, exclure (sécurité contre les faux positifs)
                    is_recurring = False
                if not is_recurring:
                    continue

                old_price = sol.price_unit
                new_price = old_price
                line_status = status
                error_msg = ''

                if status == 'pending':
                    # Calcul de l'indexation
                    if not base_index:
                        line_status = 'no_base_index'
                        error_msg = _(
                            "Aucun indice trouvé pour la date %s"
                        ) % reference_date.strftime('%d/%m/%Y')
                    elif not base_index.value:
                        line_status = 'error_calc'
                        error_msg = _("Indice de base à 0 — calcul impossible")
                    else:
                        try:
                            new_price = round(
                                old_price * target_value / base_index.value,
                                2
                            )
                        except Exception as e:
                            line_status = 'error_calc'
                            error_msg = str(e)

                # Création de la ligne d'audit
                line_vals_list.append({
                    'wizard_id': self.id,
                    'subscription_id': sub.id,
                    'subscription_line_id': sol.id,
                    'partner_id': sub.partner_id.id,
                    'product_id': sol.product_id.id,
                    'start_date': start_date,
                    'age_months': age_months,
                    'last_indexation_date': last_indexation_date,
                    'base_index_id': base_index.id if base_index else False,
                    'base_index_value': base_index.value if base_index else 0.0,
                    'target_index_id': self.target_index_id.id,
                    'target_index_value': target_value,
                    'old_price': old_price,
                    'new_price': new_price,
                    'quantity': sol.product_uom_qty or 1.0,
                    'status': line_status,
                    'error_msg': error_msg,
                    # Coché par défaut si pending et calcul OK
                    'selected': line_status == 'pending',
                })

        if line_vals_list:
            Line.create(line_vals_list)

        _logger.info(
            "Audit terminé : %d ligne(s) générée(s)",
            len(line_vals_list)
        )

        return self._reload()

    def action_select_all(self):
        """Coche toutes les lignes éligibles (statut pending)."""
        self.ensure_one()
        self.audit_line_ids.filtered(
            lambda l: l.status == 'pending'
        ).write({'selected': True})
        return self._reload()

    def action_deselect_all(self):
        """Décoche toutes les lignes."""
        self.ensure_one()
        self.audit_line_ids.write({'selected': False})
        return self._reload()

    def action_filter_pending(self):
        """Affiche uniquement les lignes pending."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lignes à indexer'),
            'res_model': 'lolirine.indexation.audit.line',
            'view_mode': 'list',
            'domain': [
                ('wizard_id', '=', self.id),
                ('status', '=', 'pending'),
            ],
            'target': 'new',
        }

    def action_create_indexation_draft(self):
        """Crée un brouillon storage.indexation avec les lignes sélectionnées.

        Ne modifie AUCUN prix sur les SO. Le brouillon devra être confirmé
        puis appliqué manuellement sur la fiche storage.indexation.
        """
        self.ensure_one()

        selected = self.audit_line_ids.filtered('selected')
        if not selected:
            raise UserError(_(
                "Aucune ligne sélectionnée. Cochez les abonnements à indexer "
                "ou utilisez le bouton 'Tout sélectionner'."
            ))

        # Vérifier qu'aucune ligne sélectionnée n'est en erreur
        bad = selected.filtered(
            lambda l: l.status not in ('pending',)
        )
        if bad:
            raise UserError(_(
                "Certaines lignes sélectionnées ne sont pas en statut 'pending' :\n%s"
            ) % '\n'.join(
                f"- {l.subscription_id.name} ({l.partner_id.name}) : {l.status}"
                for l in bad
            ))

        # Créer le brouillon principal
        Indexation = self.env['storage.indexation']

        # Indice de base "global" pour le brouillon : on prend celui le plus
        # fréquent parmi les lignes sélectionnées (à titre indicatif).
        # Chaque ligne d'indexation gardera son propre base_index_id.
        base_index_counts = {}
        for line in selected:
            if line.base_index_id:
                base_index_counts[line.base_index_id.id] = (
                    base_index_counts.get(line.base_index_id.id, 0) + 1
                )
        most_common_base_id = (
            max(base_index_counts, key=base_index_counts.get)
            if base_index_counts else False
        )

        indexation = Indexation.create({
            'date': self.target_date,
            'application_date': self.target_date,
            'index_type': 'health',
            'base_index_id': most_common_base_id,
            'new_index_id': self.target_index_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'notes': _(
                "Indexation créée depuis le wizard d'audit\n"
                "- Date de référence : %s\n"
                "- Indice cible : %s (%s = %s)\n"
                "- Lignes sélectionnées : %d / %d analysées"
            ) % (
                self.target_date.strftime('%d/%m/%Y'),
                self.target_index_id.name,
                self.target_index_id.date.strftime('%Y-%m'),
                self.target_index_id.value,
                len(selected), len(self.audit_line_ids),
            ),
        })

        # Créer les lignes d'indexation
        IndexLine = self.env['storage.indexation.line']
        line_vals_list = []
        for line in selected:
            line_vals_list.append({
                'indexation_id': indexation.id,
                'subscription_id': line.subscription_id.id,
                'subscription_line_id': line.subscription_line_id.id,
                'partner_id': line.partner_id.id,
                'product_id': line.product_id.id,
                'base_index_id': line.base_index_id.id,
                'old_price': line.old_price,
                'new_price': line.new_price,
                'quantity': line.quantity,
            })
        IndexLine.create(line_vals_list)

        # Passer en état 'computed' (déjà calculé)
        indexation.state = 'computed'

        _logger.info(
            "Brouillon d'indexation créé : %s avec %d ligne(s)",
            indexation.name, len(line_vals_list)
        )

        # Rediriger vers la fiche du brouillon créé
        return {
            'type': 'ir.actions.act_window',
            'name': _('Brouillon d\'indexation créé'),
            'res_model': 'storage.indexation',
            'res_id': indexation.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ========================================================================
    # HELPERS
    # ========================================================================

    @staticmethod
    def _compute_age_in_months(start, end):
        """Calcule la différence en mois entiers entre deux dates."""
        if not start or not end:
            return 0
        return (end.year - start.year) * 12 + (end.month - start.month)

    def _reload(self):
        """Recharge le wizard pour rafraîchir l'affichage."""
        return {
            'type': 'ir.actions.act_window',
            'name': _("Audit indexation"),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class LolirineIndexationAuditLine(models.TransientModel):
    """Ligne d'audit : un abonnement éligible (ou non) à l'indexation."""
    _name = 'lolirine.indexation.audit.line'
    _description = "Ligne d'audit indexation"
    _order = 'status, partner_id'

    wizard_id = fields.Many2one(
        'lolirine.indexation.audit.wizard',
        required=True,
        ondelete='cascade'
    )

    # Sélection pour création de brouillon
    selected = fields.Boolean(
        string="✓",
        default=False,
        help="Cocher pour inclure cette ligne dans le brouillon d'indexation"
    )

    # Identifiants
    subscription_id = fields.Many2one(
        'sale.order',
        string="Abonnement",
        readonly=True
    )
    subscription_line_id = fields.Many2one(
        'sale.order.line',
        string="Ligne d'abonnement",
        readonly=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Client",
        readonly=True
    )
    product_id = fields.Many2one(
        'product.product',
        string="Produit",
        readonly=True
    )

    # Dates et ancienneté
    start_date = fields.Date(string="Date de début", readonly=True)
    age_months = fields.Integer(string="Ancienneté (mois)", readonly=True)
    last_indexation_date = fields.Date(
        string="Dernière indexation",
        readonly=True
    )

    # Indices
    base_index_id = fields.Many2one(
        'storage.price.index',
        string="Indice de base",
        readonly=True
    )
    base_index_value = fields.Float(
        string="Valeur indice base",
        readonly=True,
        digits=(10, 2)
    )
    target_index_id = fields.Many2one(
        'storage.price.index',
        string="Indice cible",
        readonly=True
    )
    target_index_value = fields.Float(
        string="Valeur indice cible",
        readonly=True,
        digits=(10, 2)
    )

    # Prix
    old_price = fields.Monetary(
        string="Loyer actuel",
        readonly=True,
        currency_field='currency_id'
    )
    new_price = fields.Monetary(
        string="Loyer indexé théorique",
        readonly=True,
        currency_field='currency_id'
    )
    price_increase = fields.Monetary(
        string="Augmentation",
        compute='_compute_increase',
        currency_field='currency_id',
        store=True
    )
    increase_percentage = fields.Float(
        string="% Augmentation",
        compute='_compute_increase',
        store=True,
        digits=(5, 2)
    )
    quantity = fields.Float(
        string="Quantité",
        readonly=True,
        default=1.0
    )

    currency_id = fields.Many2one(
        related='wizard_id.currency_id'
    )

    # Statut
    status = fields.Selection([
        ('pending', '🟢 À indexer'),
        ('recently_indexed', '🔵 Récemment indexé'),
        ('new_contract', '⚪ Trop récent'),
        ('no_base_index', '🚨 Indice base manquant'),
        ('error_calc', '🚨 Erreur calcul'),
    ], string="Statut", readonly=True, index=True)

    error_msg = fields.Char(string="Détail", readonly=True)

    @api.depends('old_price', 'new_price')
    def _compute_increase(self):
        for line in self:
            line.price_increase = line.new_price - line.old_price
            if line.old_price:
                line.increase_percentage = (
                    (line.new_price - line.old_price) / line.old_price * 100
                )
            else:
                line.increase_percentage = 0.0

    def action_open_subscription(self):
        """Ouvre l'abonnement source."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.subscription_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
