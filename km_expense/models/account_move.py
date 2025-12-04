# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    km_trajet_ids = fields.One2many(
        'km.trajet',
        'invoice_id',
        string='Trajets liés',
    )
    km_trajet_count = fields.Integer(
        string='Nombre de trajets',
        compute='_compute_km_trajet_count',
    )

    @api.depends('km_trajet_ids')
    def _compute_km_trajet_count(self):
        for move in self:
            move.km_trajet_count = len(move.km_trajet_ids)

    def action_create_km_trajet(self):
        """Ouvrir le wizard pour créer un trajet depuis cette facture"""
        self.ensure_one()
        
        if self.move_type not in ('in_invoice', 'in_refund', 'out_invoice', 'out_refund'):
            raise UserError("Cette action n'est disponible que pour les factures.")
        
        if not self.partner_id:
            raise UserError("La facture doit avoir un partenaire défini.")
        
        # Déterminer le type de trajet
        if self.move_type in ('in_invoice', 'in_refund'):
            trajet_type = 'fournisseur'
            categorie = self.env.ref('km_expense.categorie_fournisseur', raise_if_not_found=False)
        else:
            trajet_type = 'client'
            categorie = self.env.ref('km_expense.categorie_client', raise_if_not_found=False)
        
        # Chercher une destination prédéfinie pour ce partenaire
        destination = self.env['km.destination'].search([
            ('partner_id', '=', self.partner_id.id)
        ], limit=1)
        
        if not destination:
            # Chercher par nom similaire
            destination = self.env['km.destination'].search([
                ('name', 'ilike', self.partner_id.name)
            ], limit=1)
        
        # Préparer les valeurs par défaut pour le wizard
        default_values = {
            'invoice_id': self.id,
            'partner_id': self.partner_id.id,
            'date_trajet': self.invoice_date or fields.Date.today(),
            'trajet_type': trajet_type,
            'categorie_id': categorie.id if categorie else False,
            'destination_predef_id': destination.id if destination else False,
            'motif': f"Facture {self.name or 'Brouillon'} - {self.partner_id.name}",
        }
        
        return {
            'name': 'Créer un trajet',
            'type': 'ir.actions.act_window',
            'res_model': 'km.trajet.from.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_date_trajet': self.invoice_date or fields.Date.today(),
                'default_trajet_type': trajet_type,
                'default_categorie_id': categorie.id if categorie else False,
                'default_destination_predef_id': destination.id if destination else False,
                'default_motif': f"Facture {self.name or 'Brouillon'} - {self.partner_id.name}",
            },
        }

    def action_view_km_trajets(self):
        """Voir les trajets liés à cette facture"""
        self.ensure_one()
        return {
            'name': 'Trajets',
            'type': 'ir.actions.act_window',
            'res_model': 'km.trajet',
            'view_mode': 'tree,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {'default_invoice_id': self.id},
        }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_peage_line = fields.Boolean(
        string='Ligne de péage',
        compute='_compute_is_peage_line',
        store=True,
    )

    @api.depends('name', 'product_id')
    def _compute_is_peage_line(self):
        """Détecter automatiquement les lignes de péage"""
        peage_keywords = ['péage', 'peage', 'toll', 'liefkenshoek', 'viapass', 'tunnel', 'autoroute']
        for line in self:
            line.is_peage_line = False
            if line.name:
                name_lower = line.name.lower()
                if any(keyword in name_lower for keyword in peage_keywords):
                    line.is_peage_line = True
