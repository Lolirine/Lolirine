# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _inherit = 'sale.order'

    # Champs ACT365
    act365_cardholder_id = fields.Char(
        string='ID Cardholder ACT365',
        copy=False,
        help="Identifiant du cardholder dans le système ACT365",
    )
    act365_access_code = fields.Char(
        string='Code d\'accès ACT365',
        copy=False,
        tracking=True,
        help="Code PIN pour l'accès au garde-meubles",
    )
    act365_group_id = fields.Many2one(
        'act365.cardholder.group',
        string='Groupe ACT365',
        help="Groupe de cardholders ACT365 pour cet abonnement",
    )
    act365_synced = fields.Boolean(
        string='Synchronisé ACT365',
        default=False,
        copy=False,
        help="Indique si le cardholder a été créé/synchronisé dans ACT365",
    )
    act365_enabled = fields.Boolean(
        string='Accès activé',
        default=False,
        copy=False,
        help="Indique si l'accès ACT365 est actuellement activé",
    )
    act365_last_sync = fields.Datetime(
        string='Dernière synchronisation',
        copy=False,
        readonly=True,
    )
    act365_valid_from = fields.Datetime(
        string='Accès valide depuis',
        help="Date de début de validité de l'accès ACT365",
    )
    act365_valid_to = fields.Datetime(
        string='Accès valide jusqu\'à',
        help="Date de fin de validité de l'accès ACT365",
    )

    def action_assign_act365_code(self):
        """Ouvre le wizard pour attribuer un code ACT365"""
        self.ensure_one()
        
        # Vérifier si c'est un abonnement
        if not self.is_subscription:
            raise UserError(_("Cette action n'est disponible que pour les abonnements."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attribuer un code ACT365'),
            'res_model': 'act365.assign.code.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_act365_group_id': self.act365_group_id.id if self.act365_group_id else False,
                'default_access_code': self.act365_access_code or '',
            },
        }

    def action_sync_act365(self):
        """Synchronise les données avec ACT365"""
        self.ensure_one()
        
        if not self.act365_access_code:
            raise UserError(_("Veuillez d'abord attribuer un code d'accès."))
        
        ACT365API = self.env['act365.api']
        
        # Préparer les données du cardholder
        cardholder_data = {
            'firstName': self.partner_id.name.split()[0] if self.partner_id.name else 'Client',
            'lastName': ' '.join(self.partner_id.name.split()[1:]) if self.partner_id.name and len(self.partner_id.name.split()) > 1 else self.partner_id.name or '',
            'email': self.partner_id.email or '',
            'phone': self.partner_id.phone or self.partner_id.mobile or '',
            'enabled': True,
            'externalReference': f'ODOO-SUB-{self.id}',
        }
        
        # Ajouter les dates de validité si définies
        if self.act365_valid_from:
            cardholder_data['validFrom'] = self.act365_valid_from.isoformat()
        if self.act365_valid_to:
            cardholder_data['validTo'] = self.act365_valid_to.isoformat()
        
        # Ajouter le groupe si défini
        if self.act365_group_id:
            cardholder_data['cardholderGroups'] = [self.act365_group_id.act365_id]
        
        try:
            if self.act365_cardholder_id:
                # Mise à jour du cardholder existant
                result = ACT365API.update_cardholder(self.act365_cardholder_id, cardholder_data)
                message = _("Cardholder mis à jour dans ACT365")
            else:
                # Création d'un nouveau cardholder
                result = ACT365API.create_cardholder(cardholder_data)
                
                # Récupérer l'ID du cardholder créé
                cardholder_id = result.get('id') or result.get('cardholderId')
                if cardholder_id:
                    self.act365_cardholder_id = str(cardholder_id)
                    
                    # Ajouter le credential PIN
                    pin_result = ACT365API.add_pin_credential(cardholder_id, self.act365_access_code)
                    _logger.info(f"PIN credential added: {pin_result}")
                
                message = _("Cardholder créé dans ACT365")
            
            # Mettre à jour les champs de suivi
            self.write({
                'act365_synced': True,
                'act365_enabled': True,
                'act365_last_sync': fields.Datetime.now(),
            })
            
            # Mettre à jour le partenaire
            if self.partner_id and self.act365_access_code:
                self.partner_id.act365_access_code = self.act365_access_code
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Synchronisation ACT365'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Erreur synchronisation ACT365: {str(e)}")
            raise UserError(_("Erreur lors de la synchronisation ACT365:\n%s") % str(e))

    def action_enable_act365_access(self):
        """Active l'accès ACT365 pour cet abonnement"""
        self.ensure_one()
        
        if not self.act365_cardholder_id:
            raise UserError(_("Aucun cardholder ACT365 associé. Veuillez d'abord synchroniser."))
        
        ACT365API = self.env['act365.api']
        
        try:
            ACT365API.enable_cardholder(self.act365_cardholder_id)
            self.act365_enabled = True
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('ACT365'),
                    'message': _("Accès activé avec succès"),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_("Erreur lors de l'activation de l'accès:\n%s") % str(e))

    def action_disable_act365_access(self):
        """Désactive l'accès ACT365 pour cet abonnement"""
        self.ensure_one()
        
        if not self.act365_cardholder_id:
            raise UserError(_("Aucun cardholder ACT365 associé."))
        
        ACT365API = self.env['act365.api']
        
        try:
            ACT365API.disable_cardholder(self.act365_cardholder_id)
            self.act365_enabled = False
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('ACT365'),
                    'message': _("Accès désactivé avec succès"),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_("Erreur lors de la désactivation de l'accès:\n%s") % str(e))

    def action_view_act365_info(self):
        """Récupère et affiche les informations ACT365 actuelles"""
        self.ensure_one()
        
        if not self.act365_cardholder_id:
            raise UserError(_("Aucun cardholder ACT365 associé."))
        
        ACT365API = self.env['act365.api']
        
        try:
            cardholder = ACT365API.get_cardholder(self.act365_cardholder_id)
            credentials = ACT365API.get_cardholder_credentials(self.act365_cardholder_id)
            
            # Construire le message d'information
            info_lines = [
                f"**Cardholder ID:** {self.act365_cardholder_id}",
                f"**Nom:** {cardholder.get('firstName', '')} {cardholder.get('lastName', '')}",
                f"**Email:** {cardholder.get('email', 'N/A')}",
                f"**Statut:** {'Activé' if cardholder.get('enabled') else 'Désactivé'}",
            ]
            
            if credentials:
                info_lines.append("\n**Credentials:**")
                for cred in credentials.get('data', credentials if isinstance(credentials, list) else []):
                    cred_type = cred.get('type', 'Inconnu')
                    info_lines.append(f"  - Type: {cred_type}")
            
            message = '\n'.join(info_lines)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Informations ACT365'),
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            raise UserError(_("Erreur lors de la récupération des informations:\n%s") % str(e))

    # Hooks sur les changements d'état de l'abonnement
    def _subscription_post_success_payment(self, invoice, transaction):
        """Hook appelé après un paiement réussi"""
        res = super()._subscription_post_success_payment(invoice, transaction)
        
        ICP = self.env['ir.config_parameter'].sudo()
        auto_sync = ICP.get_param('act365.auto_sync', 'True') == 'True'
        enable_on_confirm = ICP.get_param('act365.enable_on_confirm', 'True') == 'True'
        
        for subscription in self.filtered(lambda s: s.is_subscription):
            if auto_sync and subscription.act365_access_code:
                try:
                    subscription.action_sync_act365()
                    if enable_on_confirm and subscription.act365_cardholder_id:
                        subscription.action_enable_act365_access()
                except Exception as e:
                    _logger.error(f"Erreur auto-sync ACT365 pour {subscription.name}: {str(e)}")
        
        return res

    def set_close(self):
        """Override pour désactiver l'accès ACT365 à la clôture"""
        res = super().set_close()
        
        ICP = self.env['ir.config_parameter'].sudo()
        disable_on_close = ICP.get_param('act365.disable_on_close', 'True') == 'True'
        
        if disable_on_close:
            for subscription in self.filtered(lambda s: s.act365_cardholder_id and s.act365_enabled):
                try:
                    subscription.action_disable_act365_access()
                except Exception as e:
                    _logger.error(f"Erreur désactivation ACT365 pour {subscription.name}: {str(e)}")
        
        return res
