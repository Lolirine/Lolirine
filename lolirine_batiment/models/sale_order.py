# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

REGIMES_TVA = [
    ('21', '21 % — taux normal'),
    ('6', '6 % — rénovation d\'un logement privé de plus de 10 ans'),
    ('autoliq', 'Autoliquidation — client assujetti (cocontractant)'),
]
TYPES_TRAVAUX = [
    ('renovation', 'Rénovation'),
    ('construction', 'Construction / extension'),
    ('toiture', 'Toiture'),
    ('amenagement', 'Aménagement intérieur'),
    ('exterieur', 'Aménagements extérieurs'),
    ('entretien', 'Entretien / dépannage'),
]


class SaleOrderTemplateBatiment(models.Model):
    _inherit = 'sale.order.template'

    bat_template = fields.Boolean(
        "Modèle bâtiment", help="Proposé (et choisi par défaut) sur les devis bâtiment, et seulement sur ceux-ci.")


class SaleOrderBatiment(models.Model):
    _inherit = 'sale.order'

    bat_type_travaux = fields.Selection(TYPES_TRAVAUX, string="Type de travaux")
    bat_tva_regime = fields.Selection(REGIMES_TVA, string="Régime de TVA", default='21', tracking=True)
    bat_logement_10ans = fields.Boolean("Logement de plus de 10 ans",
                                        help="Première occupation du logement il y a au moins 10 ans.")
    bat_habitation_privee = fields.Boolean("Habitation privée",
                                           help="Utilisé exclusivement ou principalement comme habitation privée.")
    bat_alerte_tva = fields.Char(compute='_compute_bat_alerte_tva')
    bat_description = fields.Text("Description du chantier")

    @api.depends('bat_tva_regime', 'bat_logement_10ans', 'bat_habitation_privee', 'partner_id')
    def _compute_bat_alerte_tva(self):
        for o in self:
            alerte = False
            if o.chantier_domaine == 'batiment' and o.bat_tva_regime == '6':
                manque = []
                if not o.bat_logement_10ans:
                    manque.append(_("logement de plus de 10 ans"))
                if not o.bat_habitation_privee:
                    manque.append(_("habitation privée"))
                if o.partner_id.commercial_partner_id.is_company:
                    manque.append(_("client consommateur final (ici une société)"))
                if manque:
                    alerte = _("TVA 6 %% : conditions à vérifier — %s.") % ", ".join(manque)
            o.bat_alerte_tva = alerte

    # ── Modèle de devis bâtiment, jamais d'abonnement ─────────────────
    @api.model
    def _bat_modele(self):
        modele = self.env.ref('lolirine_batiment.sale_template_batiment', raise_if_not_found=False)
        return modele if modele and modele.active else self.env['sale.order.template'].search(
            [('bat_template', '=', True)], limit=1)

    def _bat_vals_sans_abonnement(self, vals):
        """Devis bâtiment : modèle bâtiment et pas de plan récurrent (abonnement garde-meuble)."""
        modele_id = vals.get('sale_order_template_id')
        modele = self.env['sale.order.template'].browse(modele_id) if modele_id else self.env['sale.order.template']
        if not modele or not modele.bat_template:
            vals['sale_order_template_id'] = self._bat_modele().id or False
        if 'plan_id' in self._fields:
            vals['plan_id'] = False
        return vals

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_chantier_domaine') == 'batiment':
            if 'sale_order_template_id' in fields_list or 'sale_order_template_id' in res:
                res['sale_order_template_id'] = self._bat_modele().id or False
            if 'plan_id' in self._fields:
                res['plan_id'] = False
        return res

    @api.onchange('sale_order_template_id')
    def _onchange_bat_modele_sans_plan(self):
        if self.chantier_domaine == 'batiment' and 'plan_id' in self._fields and self.plan_id:
            self.plan_id = False

    # ── Numérotation BAT/AAAA/NNNN ───────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('chantier_domaine') == 'batiment':
                if not vals.get('name') or vals.get('name') in ('/', _('New'), 'New'):
                    vals['name'] = self.env['ir.sequence'].next_by_code('lolirine.batiment.devis') or '/'
                vals.setdefault('require_signature', True)
                self._bat_vals_sans_abonnement(vals)
        orders = super().create(vals_list)
        for o in orders.filtered(lambda o: o.chantier_domaine == 'batiment'):
            if 'plan_id' in o._fields and o.plan_id:
                o.plan_id = False
            modele = o.sale_order_template_id
            if modele and modele.bat_template and modele.note and not o.note:
                o.note = modele.note
        orders.filtered(lambda o: o.chantier_domaine == 'batiment' and o.bat_tva_regime != '21')._bat_appliquer_tva()
        return orders

    def write(self, vals):
        if 'plan_id' in vals and vals['plan_id'] and any(o.chantier_domaine == 'batiment' for o in self):
            vals = dict(vals, plan_id=False)
        res = super().write(vals)
        if 'bat_tva_regime' in vals and not self.env.context.get('bat_tva_en_cours'):
            self._bat_appliquer_tva()
        return res

    # ── TVA : 21 %, 6 % rénovation, autoliquidation ──────────────────
    def _bat_position_6(self):
        fp = self.env.ref('lolirine_batiment.fp_renovation_6', raise_if_not_found=False)
        if not fp:
            raise UserError(_("Position fiscale « Rénovation 6 % » introuvable."))
        return fp

    @api.onchange('bat_tva_regime')
    def _onchange_bat_tva_regime(self):
        if self.chantier_domaine != 'batiment':
            return
        if self.bat_tva_regime == 'autoliq':
            self.pool_autoliquidation = True
            self.fiscal_position_id = self._pool_position_cocontractant()
        elif self.bat_tva_regime == '6':
            self.pool_autoliquidation = False
            self.fiscal_position_id = self._bat_position_6()
        else:
            self.pool_autoliquidation = False
            self._compute_fiscal_position_id()

    def _bat_appliquer_tva(self):
        for o in self.with_context(bat_tva_en_cours=True):
            if o.chantier_domaine != 'batiment' or o.state not in ('draft', 'sent'):
                continue
            if o.bat_tva_regime == 'autoliq':
                o.pool_autoliquidation = True          # position Cocontractant + taxes recalculées
                continue
            if o.pool_autoliquidation:
                o.pool_autoliquidation = False         # position recalculée
            if o.bat_tva_regime == '6':
                o.fiscal_position_id = o._bat_position_6()
            else:
                o._compute_fiscal_position_id()
            o._recompute_taxes()

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.chantier_domaine == 'batiment' and self.bat_tva_regime == '6':
            vals['fiscal_position_id'] = self._bat_position_6().id
        return vals

    # ── E-mail d'envoi ───────────────────────────────────────────────
    def _find_mail_template(self):
        if len(self) == 1 and self.chantier_domaine == 'batiment' and self.state in ('draft', 'sent'):
            modele = self.env.ref('lolirine_batiment.mail_template_devis_batiment', raise_if_not_found=False)
            if modele:
                return modele
        return super()._find_mail_template()

    def action_bat_ajouter_ouvrage(self):
        return self.action_ajouter_prestation()
