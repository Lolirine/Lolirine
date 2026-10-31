# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

TYPES = [('hivernage', '❄️ Hivernage'), ('remise_en_route', '🌱 Remise en route')]


class PoolEntretienWizard(models.TransientModel):
    """Devis d'hivernage ou de remise en route pour un client, depuis le menu Ventes."""
    _name = 'lolirine.pool.entretien.wizard'
    _description = "Nouveau devis d'hivernage / de remise en route"

    type_intervention = fields.Selection(TYPES, string="Intervention", required=True, default='hivernage')
    partner_id = fields.Many2one('res.partner', string="Client", required=True)
    adresse = fields.Char("Adresse de la piscine")
    prestation_id = fields.Many2one('lolirine.pool.prestation', string="Formule", required=True,
                                    domain=[('categorie', '=', 'entretien')])
    prix = fields.Float(related='prestation_id.total_ouvrage', string="Prix de la formule HT")
    date_souhaitee = fields.Datetime("Date souhaitée par le client")
    avec_options = fields.Boolean("Proposer les options (produits, accessoires)", default=True)
    memoriser = fields.Boolean("Client en entretien saisonnier",
                               help="Mémorise la formule sur la fiche du client : il recevra chaque saison "
                                    "une proposition (septembre : hivernage, mars : remise en route).")
    equipement_ids = fields.Many2many('lolirine.pool.equipement', string="Parc installé du client",
                                      compute='_compute_equipements')
    demande = fields.Text("Demande du client", help="Notée dans l'historique du devis.")

    @api.depends('partner_id')
    def _compute_equipements(self):
        for w in self:
            w.equipement_ids = w.partner_id.pool_equipement_ids

    @api.onchange('partner_id', 'type_intervention')
    def _onchange_client(self):
        p = self.partner_id
        if p:
            self.adresse = p.pool_adresse_piscine or p.contact_address
            self.memoriser = p.pool_entretien_auto
        formule = (p.pool_formule_hivernage_id if self.type_intervention == 'hivernage' else p.pool_formule_remise_id) \
            if p else False
        self.prestation_id = formule or self.env['sale.order']._pool_formule_defaut(self.type_intervention)

    def action_creer(self):
        self.ensure_one()
        p = self.partner_id
        if self.memoriser:
            vals = {'pool_entretien_auto': True, 'pool_adresse_piscine': self.adresse or p.pool_adresse_piscine}
            vals['pool_formule_hivernage_id' if self.type_intervention == 'hivernage'
                 else 'pool_formule_remise_id'] = self.prestation_id.id
            p.write(vals)
        order = self.env['sale.order']._pool_creer_devis_entretien(
            p, self.type_intervention, prestation=self.prestation_id, adresse=self.adresse,
            date_souhaitee=self.date_souhaitee, avec_options=self.avec_options,
            note_interne=(_("Demande du client : %s") % self.demande) if self.demande else False)
        return {'type': 'ir.actions.act_window', 'res_model': 'sale.order', 'res_id': order.id,
                'view_mode': 'form', 'target': 'current'}


class PoolCampagneWizard(models.TransientModel):
    """Campagne saisonnière : un devis par client en entretien saisonnier (brouillons à vérifier)."""
    _name = 'lolirine.pool.campagne.wizard'
    _description = "Campagne d'hivernage / de remise en route"

    type_intervention = fields.Selection(TYPES, string="Campagne", required=True, default='hivernage')
    partner_ids = fields.Many2many('res.partner', string="Clients",
                                   default=lambda self: self.env['res.partner'].search([('pool_entretien_auto', '=', True)]))

    def action_lancer(self):
        self.ensure_one()
        if not self.partner_ids:
            raise UserError(_("Aucun client sélectionné."))
        SO = self.env['sale.order']
        crees = SO.browse()
        for client in self.partner_ids:
            crees |= SO._pool_creer_devis_entretien(client, self.type_intervention)
        return {'type': 'ir.actions.act_window', 'res_model': 'sale.order',
                'name': _("Campagne — devis créés"), 'view_mode': 'list,form',
                'domain': [('id', 'in', crees.ids)]}
