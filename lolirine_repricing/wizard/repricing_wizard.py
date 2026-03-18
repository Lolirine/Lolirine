import base64
import logging
import time

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MARKETS = [
    (2250, "fr", "Belgique"),
    (2208, "fr", "France"),
    (2276, "de", "Allemagne"),
    (2528, "nl", "Pays-Bas"),
    (2442, "fr", "Luxembourg"),
]

PRICE_FACTOR  = 0.99   # meilleur concurrent × 0.99
MARGIN_FLOOR  = 0.20   # plancher 20% de marge
MAX_PRICE     = 50_000 # ignorer prix aberrants
DELAY_SEC     = 0.3    # pause entre requêtes
WEBSITE_ID    = 6      # Pool Store


class RepricingWizard(models.TransientModel):
    _name = 'lolirine.repricing.wizard'
    _description = 'Wizard de repricing Pool Store'

    # — Configuration —
    dataforseo_login    = fields.Char(string='DataForSEO Login', required=True,
                                      default=lambda self: self._get_param('repricing.dataforseo_login'))
    dataforseo_password = fields.Char(string='DataForSEO Password', required=True,
                                      default=lambda self: self._get_param('repricing.dataforseo_password'))
    save_credentials    = fields.Boolean(string='Mémoriser les identifiants', default=True)

    # — Périmètre —
    market_be = fields.Boolean(string='Belgique',   default=True)
    market_fr = fields.Boolean(string='France',     default=True)
    market_de = fields.Boolean(string='Allemagne',  default=True)
    market_nl = fields.Boolean(string='Pays-Bas',   default=True)
    market_lu = fields.Boolean(string='Luxembourg', default=True)

    only_no_price = fields.Boolean(
        string='Traiter uniquement les produits sans prix',
        default=False,
    )
    dry_run = fields.Boolean(
        string='Simulation (ne pas modifier les prix)',
        default=False,
        help="Calcule les nouveaux prix sans les appliquer dans Odoo.",
    )
    product_limit = fields.Integer(
        string='Limite de produits (0 = tous)',
        default=0,
        help="Utile pour tester sur un petit lot avant de lancer en masse.",
    )

    # — Résultats (lecture seule, remplis après exécution) —
    state = fields.Selection([
        ('draft',  'Configuration'),
        ('done',   'Terminé'),
    ], default='draft')

    result_total     = fields.Integer(string='Total traités',  readonly=True)
    result_updated   = fields.Integer(string='Mis à jour',     readonly=True)
    result_init      = fields.Integer(string='Initialisés',    readonly=True)
    result_floor     = fields.Integer(string='Plancher',       readonly=True)
    result_fallback  = fields.Integer(string='Plancher fallback', readonly=True)
    result_unchanged = fields.Integer(string='Inchangés',     readonly=True)
    result_no_data   = fields.Integer(string='Sans données',   readonly=True)
    result_skipped   = fields.Integer(string='Ignorés',        readonly=True)
    session_name     = fields.Char(string='Session', readonly=True)

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────
    def _get_param(self, key):
        return self.env['ir.config_parameter'].sudo().get_param(key, '')

    def _set_param(self, key, value):
        self.env['ir.config_parameter'].sudo().set_param(key, value)

    def _auth_header(self):
        token = base64.b64encode(
            f"{self.dataforseo_login}:{self.dataforseo_password}".encode()
        ).decode()
        return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

    def _active_markets(self):
        mapping = {
            'market_be': (2250, "fr", "Belgique"),
            'market_fr': (2208, "fr", "France"),
            'market_de': (2276, "de", "Allemagne"),
            'market_nl': (2528, "nl", "Pays-Bas"),
            'market_lu': (2442, "fr", "Luxembourg"),
        }
        return [v for k, v in mapping.items() if getattr(self, k)]

    # ──────────────────────────────────────────────
    # RECHERCHE DATAFORSEO
    # ──────────────────────────────────────────────
    def _search_prices(self, keyword):
        """
        Cherche le prix le plus bas sur les marchés actifs.
        Retourne (meilleur_prix, marché) ou (None, None).
        """
        markets = self._active_markets()
        if not markets:
            return None, None

        tasks = [{
            "keyword":       keyword,
            "location_code": loc_code,
            "language_code": lang_code,
            "depth":         10,
        } for loc_code, lang_code, _ in markets]

        best_price  = None
        best_market = None

        try:
            r = requests.post(
                "https://api.dataforseo.com/v3/serp/google/shopping/live/advanced",
                headers=self._auth_header(),
                json=tasks,
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()

            for task_idx, task_result in enumerate(data.get("tasks", [])):
                label = markets[task_idx][2]
                items = (task_result
                         .get("result", [{}])[0]
                         .get("items", []) or [])
                for item in items:
                    if item.get("type") != "shopping":
                        continue
                    price = item.get("price")
                    if price and isinstance(price, (int, float)) and 0 < price < MAX_PRICE:
                        if best_price is None or price < best_price:
                            best_price  = float(price)
                            best_market = label

            time.sleep(DELAY_SEC)

        except Exception as e:
            _logger.warning("DataForSEO error for '%s': %s", keyword, e)

        return best_price, best_market

    # ──────────────────────────────────────────────
    # CALCUL DU NOUVEAU PRIX
    # ──────────────────────────────────────────────
    @staticmethod
    def _floor_price(cout):
        return round(cout / (1 - MARGIN_FLOOR), 2) if cout > 0 else 0.0

    def _compute_new_price(self, prix_actuel, floor_p, best_competitor, marche):
        """
        Retourne (nouveau_prix, statut, note).
        - Sans prix existant  → meilleur prix du marché direct
        - Avec prix existant  → concurrent × 0.99
        Dans les deux cas, plancher de marge respecté.
        """
        note = f"concurrent={best_competitor:.2f}€ ({marche})"

        # Produit sans prix : on rejoint le marché directement
        if prix_actuel == 0:
            price_web = round(best_competitor, 2)
            if floor_p > 0 and price_web < floor_p:
                note += f" → plancher {floor_p:.2f}€"
                return floor_p, "floor", note
            note += " → prix marché assigné directement"
            return price_web, "initialized", note

        # Produit avec prix : on bat le concurrent de 1%
        target = round(best_competitor * PRICE_FACTOR, 2)
        if floor_p > 0 and target < floor_p:
            note += f" → plancher {floor_p:.2f}€"
            return floor_p, "floor", note
        if target >= prix_actuel:
            target = round(prix_actuel * 0.995, 2)
            if floor_p > 0 and target < floor_p:
                target = floor_p
            note += " → déjà compétitif (-0.5%)"
        return target, "updated", note

    # ──────────────────────────────────────────────
    # ACTION PRINCIPALE
    # ──────────────────────────────────────────────
    def action_run(self):
        self.ensure_one()

        if not self.dataforseo_login or not self.dataforseo_password:
            raise UserError(_("Veuillez renseigner vos identifiants DataForSEO."))

        if self.save_credentials:
            self._set_param('repricing.dataforseo_login',    self.dataforseo_login)
            self._set_param('repricing.dataforseo_password', self.dataforseo_password)

        # — Charger les produits du Pool Store (website_id = 6) —
        domain = [('website_id', '=', WEBSITE_ID)]
        if self.only_no_price:
            domain += [('list_price', '=', 0)]

        products = self.env['product.template'].search(domain)
        if self.product_limit > 0:
            products = products[:self.product_limit]

        session_name = fields.Datetime.now().strftime('Repricing %Y-%m-%d %H:%M')
        _logger.info("Repricing session '%s' — %d produits", session_name, len(products))

        # — Compteurs —
        cnt = {k: 0 for k in ('updated','initialized','floor','floor_fallback',
                               'no_competitor','no_data','skipped')}

        log_vals = []

        for product in products:
            ref         = product.default_code or ''
            nom         = product.name or ''
            prix_actuel = product.list_price or 0.0
            cout        = product.standard_price or 0.0
            floor_p     = self._floor_price(cout)

            # Mot-clé : référence fournisseur si dispo, sinon nom
            keyword = ref.strip() if ref and len(ref) > 4 else nom[:80].strip()

            if not keyword:
                cnt['skipped'] += 1
                continue

            best_price, best_market = self._search_prices(keyword)

            if best_price:
                new_price, statut, note = self._compute_new_price(
                    prix_actuel, floor_p, best_price, best_market
                )
            else:
                # Aucun concurrent trouvé
                if prix_actuel == 0 and floor_p > 0:
                    new_price = floor_p
                    statut    = 'floor_fallback'
                    note      = f"aucun concurrent → plancher coût {floor_p:.2f}€"
                elif prix_actuel == 0:
                    cnt['no_data'] += 1
                    log_vals.append({
                        'name':               session_name,
                        'product_id':         product.id,
                        'ref':                ref,
                        'prix_actuel':        prix_actuel,
                        'cout':               cout,
                        'floor_price':        floor_p,
                        'meilleur_concurrent': 0,
                        'marche_gagnant':     '',
                        'nouveau_prix':       0,
                        'statut':             'no_data',
                        'note':               'aucun concurrent et coût inconnu',
                    })
                    continue
                else:
                    new_price = prix_actuel
                    statut    = 'no_competitor'
                    note      = 'aucun concurrent → prix inchangé'

            cnt[statut] = cnt.get(statut, 0) + 1

            # Appliquer le prix sauf en simulation
            if not self.dry_run and abs(new_price - prix_actuel) >= 0.01:
                product.list_price = new_price

            log_vals.append({
                'name':                session_name,
                'product_id':          product.id,
                'ref':                 ref,
                'prix_actuel':         prix_actuel,
                'cout':                cout,
                'floor_price':         floor_p,
                'meilleur_concurrent': best_price or 0,
                'marche_gagnant':      best_market or '',
                'nouveau_prix':        new_price,
                'statut':              statut,
                'note':                note,
            })

        # — Créer les logs —
        self.env['lolirine.repricing.log'].create(log_vals)

        # — Mettre à jour le wizard pour afficher les résultats —
        self.write({
            'state':           'done',
            'session_name':    session_name,
            'result_total':    sum(cnt.values()),
            'result_updated':  cnt.get('updated', 0),
            'result_init':     cnt.get('initialized', 0),
            'result_floor':    cnt.get('floor', 0),
            'result_fallback': cnt.get('floor_fallback', 0),
            'result_unchanged':cnt.get('no_competitor', 0),
            'result_no_data':  cnt.get('no_data', 0),
            'result_skipped':  cnt.get('skipped', 0),
        })

        # Rouvrir le wizard avec les résultats
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'lolirine.repricing.wizard',
            'res_id':    self.id,
            'view_mode': 'form',
            'target':    'new',
        }

    def action_view_logs(self):
        return {
            'type':      'ir.actions.act_window',
            'name':      'Logs repricing',
            'res_model': 'lolirine.repricing.log',
            'view_mode': 'list,form',
            'domain':    [('name', '=', self.session_name)],
            'target':    'current',
        }
