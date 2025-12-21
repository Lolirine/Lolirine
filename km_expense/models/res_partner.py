# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Configuration trajet automatique
    km_trajet_auto = fields.Boolean(
        string='Créer trajet automatiquement',
        default=False,
        help="Créer automatiquement un trajet kilométrique lors de la validation d'une facture avec ce partenaire",
    )
    
    km_trajet_type = fields.Selection([
        ('fournisseur', 'Factures fournisseurs uniquement'),
        ('client', 'Factures clients uniquement'),
        ('les_deux', 'Toutes les factures'),
    ], string='Type de factures', default='fournisseur',
       help="Types de factures pour lesquels créer automatiquement un trajet")
    
    km_destination_id = fields.Many2one(
        'km.destination',
        string='Destination prédéfinie',
        help="Destination à utiliser pour les trajets automatiques. Si vide, sera recherchée automatiquement.",
    )
    
    km_categorie_id = fields.Many2one(
        'km.trajet.categorie',
        string='Catégorie de trajet',
        help="Catégorie à utiliser pour les trajets automatiques",
    )
    
    km_aller_retour = fields.Boolean(
        string='Aller-retour par défaut',
        default=True,
        help="Créer les trajets en aller-retour par défaut",
    )

    def action_view_km_trajets(self):
        """Voir tous les trajets liés à ce partenaire"""
        self.ensure_one()
        return {
            'name': f'Trajets - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'km.trajet',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
