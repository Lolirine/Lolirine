# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import random
import re


class ACT365AssignCodeWizard(models.TransientModel):
    _name = 'act365.assign.code.wizard'
    _description = 'Assistant d\'attribution de code ACT365'

    subscription_id = fields.Many2one(
        'sale.order',
        string='Abonnement',
        required=True,
        domain=[('is_subscription', '=', True)],
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        related='subscription_id.partner_id',
        readonly=True,
    )
    act365_group_id = fields.Many2one(
        'act365.cardholder.group',
        string='Groupe ACT365',
        help="Groupe de cardholders pour définir les accès",
    )
    access_code = fields.Char(
        string='Code d\'accès',
        help="Code PIN pour l'accès. Laissez vide pour générer automatiquement.",
    )
    code_generation_mode = fields.Selection([
        ('auto', 'Générer automatiquement'),
        ('manual', 'Saisir manuellement'),
    ], string='Mode de génération', default='auto', required=True)
    
    pin_length = fields.Integer(
        string='Longueur du PIN',
        default=4,
        help="Nombre de chiffres pour le code PIN",
    )
    
    valid_from = fields.Datetime(
        string='Valide depuis',
        default=fields.Datetime.now,
        help="Date de début de validité de l'accès",
    )
    valid_to = fields.Datetime(
        string='Valide jusqu\'à',
        help="Date de fin de validité de l'accès (laisser vide pour illimité)",
    )
    
    sync_immediately = fields.Boolean(
        string='Synchroniser immédiatement',
        default=True,
        help="Créer/mettre à jour le cardholder dans ACT365 immédiatement",
    )
    update_partner = fields.Boolean(
        string='Mettre à jour le client',
        default=True,
        help="Mettre à jour le code d'accès sur la fiche client",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        # Récupérer la longueur du PIN depuis la configuration
        ICP = self.env['ir.config_parameter'].sudo()
        pin_length = int(ICP.get_param('act365.pin_length', '4'))
        res['pin_length'] = pin_length
        
        # Récupérer le groupe par défaut
        default_group_id = ICP.get_param('act365.default_group_id', '0')
        try:
            default_group_id = int(default_group_id)
            if default_group_id:
                res['act365_group_id'] = default_group_id
        except (ValueError, TypeError):
            pass
        
        return res

    @api.onchange('code_generation_mode')
    def _onchange_code_generation_mode(self):
        if self.code_generation_mode == 'auto':
            self.access_code = self._generate_pin()

    @api.constrains('access_code')
    def _check_access_code(self):
        for wizard in self:
            if wizard.access_code:
                # Vérifier que le code ne contient que des chiffres
                if not re.match(r'^\d+$', wizard.access_code):
                    raise ValidationError(_("Le code d'accès ne doit contenir que des chiffres."))
                
                # Vérifier la longueur
                if len(wizard.access_code) < 4:
                    raise ValidationError(_("Le code d'accès doit contenir au moins 4 chiffres."))
                if len(wizard.access_code) > 8:
                    raise ValidationError(_("Le code d'accès ne peut pas dépasser 8 chiffres."))

    def _generate_pin(self):
        """Génère un code PIN aléatoire"""
        length = self.pin_length or 4
        # Éviter les PIN trop simples comme 0000, 1234, etc.
        while True:
            pin = ''.join([str(random.randint(0, 9)) for _ in range(length)])
            # Vérifier que le PIN n'est pas trop simple
            if not self._is_simple_pin(pin):
                return pin

    def _is_simple_pin(self, pin):
        """Vérifie si un PIN est trop simple"""
        # Tous les mêmes chiffres
        if len(set(pin)) == 1:
            return True
        
        # Séquences croissantes ou décroissantes
        ascending = ''.join([str(i % 10) for i in range(10)])
        descending = ascending[::-1]
        if pin in ascending or pin in descending:
            return True
        
        # PINs courants à éviter
        common_pins = ['1234', '4321', '0000', '1111', '2222', '3333', 
                       '4444', '5555', '6666', '7777', '8888', '9999',
                       '1212', '2121', '1010', '0101']
        if pin in common_pins:
            return True
        
        return False

    def action_generate_pin(self):
        """Génère un nouveau code PIN"""
        self.ensure_one()
        self.access_code = self._generate_pin()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        """Confirme l'attribution du code d'accès"""
        self.ensure_one()
        
        if not self.access_code and self.code_generation_mode == 'manual':
            raise UserError(_("Veuillez saisir un code d'accès."))
        
        # Si auto et pas de code, générer
        if self.code_generation_mode == 'auto' and not self.access_code:
            self.access_code = self._generate_pin()
        
        # Mettre à jour l'abonnement
        subscription_vals = {
            'act365_access_code': self.access_code,
            'act365_group_id': self.act365_group_id.id if self.act365_group_id else False,
            'act365_valid_from': self.valid_from,
            'act365_valid_to': self.valid_to,
        }
        self.subscription_id.write(subscription_vals)
        
        # Mettre à jour le partenaire si demandé
        if self.update_partner and self.partner_id:
            self.partner_id.act365_access_code = self.access_code
        
        # Synchroniser avec ACT365 si demandé
        if self.sync_immediately:
            try:
                self.subscription_id.action_sync_act365()
            except Exception as e:
                # Afficher l'erreur mais ne pas bloquer
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Code attribué avec avertissement'),
                        'message': _(
                            "Code d'accès attribué: %s\n\n"
                            "Attention: La synchronisation ACT365 a échoué:\n%s\n\n"
                            "Vous pouvez réessayer manuellement depuis l'abonnement."
                        ) % (self.access_code, str(e)),
                        'type': 'warning',
                        'sticky': True,
                    }
                }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Code d\'accès attribué'),
                'message': _(
                    "Code d'accès: %s\n"
                    "Client: %s\n"
                    "Abonnement: %s"
                ) % (self.access_code, self.partner_id.name, self.subscription_id.name),
                'type': 'success',
                'sticky': True,
            }
        }

    def action_open_act365_portal(self):
        """Ouvre le portail ACT365 dans un nouvel onglet"""
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.act365.eu',
            'target': 'new',
        }
