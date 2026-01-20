# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def action_view_related_document(self):
        """Ouvrir le document lié à cet email (facture, abonnement, etc.)"""
        self.ensure_one()
        
        if not self.model or not self.res_id:
            raise UserError(_("Cet email n'est pas lié à un document."))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_retry_send(self):
        """Réessayer d'envoyer les emails en échec"""
        failed_mails = self.filtered(lambda m: m.state == 'exception')
        if failed_mails:
            failed_mails.write({'state': 'outgoing'})
            failed_mails.send()
        return True
