# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.pool_prestation import arrondi_5

SECTION_MO = "Main-d'œuvre et déplacements"


class PoolPrestationWizard(models.TransientModel):
    _name = 'lolirine.pool.prestation.wizard'
    _description = "Ajouter une prestation de main-d'œuvre au devis"

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    prestation_id = fields.Many2one('lolirine.pool.prestation', string='Prestation', required=True)
    titre = fields.Char("Titre sur le devis", required=True)
    description_client = fields.Text("Travaux décrits au client")
    detail_interne = fields.Text("Détail interne (étapes et heures)")
    heures = fields.Float("Heures", digits=(10, 2))
    taux_horaire = fields.Float("Taux horaire HT (€)", digits=(10, 2))
    coef_difficulte = fields.Float("Coefficient de difficulté", digits=(10, 2), default=1.0)
    motif_coef = fields.Char("Motif du coefficient")
    prix = fields.Float("Forfait HT (€)", digits=(10, 2), compute='_compute_prix', store=True, readonly=False)

    @api.onchange('prestation_id')
    def _onchange_prestation(self):
        p = self.prestation_id
        if p:
            self.titre = p.name
            self.description_client = p.description_client
            self.detail_interne = p.detail_interne
            self.heures = p.heures
            self.taux_horaire = p.taux_horaire
            self.coef_difficulte = p.coef_difficulte or 1.0

    @api.depends('heures', 'taux_horaire', 'coef_difficulte')
    def _compute_prix(self):
        for w in self:
            w.prix = arrondi_5(w.heures * w.taux_horaire * (w.coef_difficulte or 1.0))

    def action_ajouter(self):
        self.ensure_one()
        order = self.order_id
        if order.state not in ('draft', 'sent'):
            raise UserError(_("Le devis n'est plus modifiable."))
        if self.prix <= 0:
            raise UserError(_("Le forfait est à 0 € : indiquez les heures et le taux horaire."))
        product = self.prestation_id.product_id or self.env['product.product'].search(
            [('default_code', '=', 'MO-FORFAIT')], limit=1)
        if not product:
            raise UserError(_("Article de main-d'œuvre introuvable (référence MO-FORFAIT)."))

        nom = self.titre.strip()
        if (self.description_client or '').strip():
            nom += "\n" + self.description_client.strip()
        detail = "%s h × %.2f €/h" % (('%g' % self.heures), self.taux_horaire)
        if (self.coef_difficulte or 1.0) != 1.0:
            detail += " × coef. %g" % self.coef_difficulte
            if self.motif_coef:
                detail += " (%s)" % self.motif_coef
        detail += " = %.2f € HT" % self.prix
        if (self.detail_interne or '').strip():
            detail += "\n" + self.detail_interne.strip()

        lignes = order.order_line.sorted(lambda l: (l.sequence, l.id))
        section = lignes.filtered(lambda l: l.display_type == 'line_section'
                                  and "main" in (l.name or '').lower())[:1]
        if not section:
            section = self.env['sale.order.line'].create({
                'order_id': order.id, 'display_type': 'line_section', 'name': SECTION_MO,
                'sequence': (max(lignes.mapped('sequence')) if lignes else 0) + 10,
            })
            lignes = order.order_line.sorted(lambda l: (l.sequence, l.id))
        nouvelle = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product.id,
            'name': nom,
            'product_uom_qty': 1.0,
            'price_unit': self.prix,
            'pool_mo_detail': detail,
            'pool_prestation_id': self.prestation_id.id,
        })
        # Place la ligne en fin de section main-d'œuvre, avant la section suivante.
        ordre = [l for l in lignes if l != nouvelle]
        i = ordre.index(section) + 1
        while i < len(ordre) and ordre[i].display_type != 'line_section':
            i += 1
        ordre.insert(i, nouvelle)
        for n, l in enumerate(ordre, start=1):
            if l.sequence != n * 10:
                l.sequence = n * 10
        return {'type': 'ir.actions.act_window_close'}
