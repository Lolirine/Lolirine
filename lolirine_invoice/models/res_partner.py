from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_followup_attachments(self, options):
        """
        Override pour envoyer uniquement les factures jointes,
        sans le rapport de relance Odoo standard.
        """
        self.ensure_one()
        res_attachment_ids = []
        followup_line = options.get('followup_line')
        
        # NE PAS ajouter le rapport de relance Odoo
        # options['report_attachment_id'] = self._get_followup_report(options)
        # res_attachment_ids.append(options['report_attachment_id'])
        
        # Ajouter les attachments du template email
        if template_id := options.get('template_id', followup_line.mail_template_id):
            template_attachments = template_id._generate_template_attachments(
                self.ids, {'attachment_ids', 'report_template_ids'}
            )[self.id]
            res_attachment_ids += template_attachments['attachment_ids']
            attachments_to_create = []
            for dynamic_report in template_attachments['attachments']:
                attachments_to_create.append({
                    'name': dynamic_report[0],
                    'datas': dynamic_report[1],
                    'res_model': self._name,
                    'res_id': self.id,
                })
            res_attachment_ids += self.env['ir.attachment'].create(attachments_to_create).ids
        
        # Vérifier si on doit joindre les factures
        if not options.get('join_invoices', followup_line.join_invoices):
            return res_attachment_ids
        
        if options.get('manual_followup'):
            # Pour les relances manuelles, utiliser les attachments sélectionnés
            res_attachment_ids += options.get('attachment_ids', [])
            return res_attachment_ids
        
        # Ajouter les PDFs des factures en retard
        res_attachment_ids += self._get_invoices_to_print(options).message_main_attachment_id.ids
        
        return res_attachment_ids
