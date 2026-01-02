# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Produit/Box associé au client
    storage_product_id = fields.Many2one(
        'product.template',
        string='Box de stockage',
        domain="[('is_storage_box', '=', True)]",
        help="Le box de stockage loué par ce client"
    )
    
    # Abonnement actif
    storage_subscription_id = fields.Many2one(
        'sale.order',
        string='Abonnement stockage',
        domain="[('is_subscription', '=', True), ('subscription_state', '=', '3_progress')]",
        help="L'abonnement actif pour le stockage"
    )
    
    # Remarques sur le comportement
    behavior_notes = fields.Text(
        string='Remarques comportement',
        help="Notes sur le comportement du client (paiements, respect des règles, etc.)"
    )
    
    behavior_rating = fields.Selection([
        ('excellent', '⭐⭐⭐⭐⭐ Excellent'),
        ('good', '⭐⭐⭐⭐ Bon'),
        ('average', '⭐⭐⭐ Moyen'),
        ('poor', '⭐⭐ Problématique'),
        ('bad', '⭐ Très problématique'),
    ], string='Évaluation comportement', default='good')
    
    # Pénalités
    penalty_ids = fields.One2many(
        'partner.penalty', 
        'partner_id', 
        string='Pénalités'
    )
    
    penalty_count = fields.Integer(
        string='Nombre de pénalités',
        compute='_compute_penalty_stats',
        store=True
    )
    
    penalty_total = fields.Float(
        string='Total pénalités (€)',
        compute='_compute_penalty_stats',
        store=True
    )
    
    penalty_unpaid = fields.Float(
        string='Pénalités impayées (€)',
        compute='_compute_penalty_stats',
        store=True
    )
    
    @api.depends('penalty_ids', 'penalty_ids.amount', 'penalty_ids.state')
    def _compute_penalty_stats(self):
        for partner in self:
            penalties = partner.penalty_ids.filtered(lambda p: p.state != 'cancelled')
            partner.penalty_count = len(penalties)
            partner.penalty_total = sum(penalties.mapped('amount'))
            partner.penalty_unpaid = sum(
                penalties.filtered(lambda p: p.state in ('draft', 'confirmed')).mapped('amount')
            )
    
    def action_view_penalties(self):
        """Ouvre la liste des pénalités du client"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pénalités',
            'res_model': 'partner.penalty',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
    
    def action_add_penalty(self):
        """Ouvre le formulaire pour ajouter une pénalité"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouvelle pénalité',
            'res_model': 'partner.penalty',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_product_id': self.storage_product_id.id if self.storage_product_id else False,
            },
        }
