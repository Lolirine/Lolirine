# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class ApartmentIndexationWizard(models.TransientModel):
    _name = 'apartment.indexation.wizard'
    _description = 'Assistant d\'indexation des loyers'

    lease_ids = fields.Many2many(
        'apartment.lease',
        string='Baux à indexer',
        domain="[('state', '=', 'active'), ('allow_indexation', '=', True)]",
    )
    
    all_eligible = fields.Boolean(
        string='Tous les baux éligibles',
        default=True,
        help="Cochez pour appliquer l'indexation à tous les baux dont la date d'indexation est passée."
    )
    
    new_index = fields.Float(
        string='Nouvel indice santé',
        digits=(10, 2),
        required=True,
        help="Indice santé à utiliser pour le calcul. Consultez StatBel pour les valeurs actuelles."
    )
    
    index_date = fields.Date(
        string='Date d\'application',
        default=fields.Date.today,
        required=True,
    )
    
    index_type = fields.Selection([
        ('health', 'Indice santé'),
        ('consumer', 'Indice des prix à la consommation'),
    ], string='Type d\'indice', default='health', required=True)
    
    source = fields.Selection([
        ('statbel', 'StatBel (automatique)'),
        ('manual', 'Saisie manuelle'),
    ], string='Source', default='manual', required=True)
    
    preview_line_ids = fields.One2many(
        'apartment.indexation.wizard.line',
        'wizard_id',
        string='Aperçu',
        compute='_compute_preview_lines',
        readonly=True,
    )
    
    send_notifications = fields.Boolean(
        string='Envoyer les notifications',
        default=True,
        help="Envoyer un email aux locataires pour les informer du nouveau loyer."
    )
    
    @api.depends('lease_ids', 'all_eligible', 'new_index', 'index_date')
    def _compute_preview_lines(self):
        for wizard in self:
            lines = []
            leases = wizard._get_leases_to_index()
            
            for lease in leases:
                if wizard.new_index and lease.base_index:
                    # Formule belge: (Loyer de base × Nouvel indice) / Indice de base
                    new_rent = (lease.initial_rent * wizard.new_index) / lease.base_index
                    new_rent = round(new_rent, 2)
                    increase = new_rent - lease.rent_amount
                    increase_pct = ((new_rent / lease.rent_amount) - 1) * 100 if lease.rent_amount else 0
                    
                    lines.append((0, 0, {
                        'lease_id': lease.id,
                        'current_rent': lease.rent_amount,
                        'base_index': lease.base_index,
                        'new_index': wizard.new_index,
                        'new_rent': new_rent,
                        'increase_amount': increase,
                        'increase_percentage': increase_pct,
                    }))
            
            wizard.preview_line_ids = lines
    
    def _get_leases_to_index(self):
        """Retourne les baux à indexer."""
        self.ensure_one()
        
        if self.all_eligible:
            # Baux actifs avec indexation autorisée dont la date d'indexation est passée
            domain = [
                ('state', '=', 'active'),
                ('allow_indexation', '=', True),
                ('next_indexation_date', '<=', self.index_date),
            ]
            return self.env['apartment.lease'].search(domain)
        else:
            return self.lease_ids
    
    def action_preview(self):
        """Rafraîchit l'aperçu."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_apply(self):
        """Applique l'indexation aux baux sélectionnés."""
        self.ensure_one()
        
        if not self.new_index:
            raise UserError(_("Veuillez saisir le nouvel indice."))
        
        leases = self._get_leases_to_index()
        
        if not leases:
            raise UserError(_("Aucun bail à indexer."))
        
        history_ids = []
        
        for lease in leases:
            if not lease.base_index:
                continue
            
            # Calculer le nouveau loyer
            new_rent = (lease.initial_rent * self.new_index) / lease.base_index
            new_rent = round(new_rent, 2)
            old_rent = lease.rent_amount
            
            # Créer l'historique
            history = self.env['apartment.index.history'].create({
                'lease_id': lease.id,
                'date': self.index_date,
                'old_rent': old_rent,
                'new_rent': new_rent,
                'old_index': lease.current_index or lease.base_index,
                'new_index': self.new_index,
                'index_type': self.index_type,
                'source': self.source,
            })
            history_ids.append(history.id)
            
            # Mettre à jour le bail
            lease.write({
                'rent_amount': new_rent,
                'current_index': self.new_index,
                'last_indexation_date': self.index_date,
                'next_indexation_date': self.index_date + relativedelta(years=1),
            })
            
            # Envoyer la notification si demandé
            if self.send_notifications:
                try:
                    template = self.env.ref('apartment_rental.email_template_indexation_notification')
                    template.send_mail(history.id, force_send=True)
                    history.notification_sent = True
                except Exception:
                    pass  # Continuer même si l'envoi échoue
        
        # Message de confirmation
        message = _("%d bail(s) indexé(s) avec succès.") % len(leases)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Indexation terminée'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'apartment.index.history',
                    'view_mode': 'list,form',
                    'domain': [('id', 'in', history_ids)],
                    'target': 'current',
                }
            }
        }


class ApartmentIndexationWizardLine(models.TransientModel):
    _name = 'apartment.indexation.wizard.line'
    _description = 'Ligne d\'aperçu indexation'
    
    wizard_id = fields.Many2one('apartment.indexation.wizard', string='Assistant', required=True, ondelete='cascade')
    lease_id = fields.Many2one('apartment.lease', string='Bail', readonly=True)
    tenant_name = fields.Char(related='lease_id.tenant_id.name', string='Locataire', readonly=True)
    property_name = fields.Char(related='lease_id.property_id.name', string='Bien', readonly=True)
    current_rent = fields.Float(string='Loyer actuel', readonly=True)
    base_index = fields.Float(string='Indice de base', readonly=True)
    new_index = fields.Float(string='Nouvel indice', readonly=True)
    new_rent = fields.Float(string='Nouveau loyer', readonly=True)
    increase_amount = fields.Float(string='Augmentation (€)', readonly=True)
    increase_percentage = fields.Float(string='Augmentation (%)', readonly=True)
