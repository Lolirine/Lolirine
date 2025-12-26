# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64


class ApartmentInitialPhotoWizard(models.TransientModel):
    _name = 'apartment.initial.photo.wizard'
    _description = 'Import en masse de photos initiales'

    property_id = fields.Many2one(
        'apartment.property',
        string='Bien',
        required=True,
        default=lambda self: self._default_property_id(),
    )
    
    taken_date = fields.Date(
        string='Date des photos',
        default=fields.Date.today,
        required=True,
    )
    
    room_type_id = fields.Many2one(
        'apartment.room.type',
        string='Pièce (optionnel)',
        help='Si renseigné, toutes les photos seront associées à cette pièce',
    )
    
    photo_type = fields.Selection([
        ('general', 'Vue générale'),
        ('detail', 'Détail'),
        ('equipment', 'Équipement'),
        ('meter', 'Compteur'),
        ('exterior', 'Extérieur'),
        ('common_area', 'Parties communes'),
        ('other', 'Autre'),
    ], string='Type de photo', default='general')
    
    photo_ids = fields.Many2many(
        'ir.attachment',
        'apartment_initial_photo_wizard_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='Photos à importer',
    )
    
    @api.model
    def _default_property_id(self):
        if self.env.context.get('active_model') == 'apartment.property':
            return self.env.context.get('active_id')
        return False
    
    def action_import_photos(self):
        """Import les photos sélectionnées comme photos initiales"""
        self.ensure_one()
        
        if not self.photo_ids:
            raise UserError(_("Veuillez sélectionner au moins une photo à importer."))
        
        InitialPhoto = self.env['apartment.property.initial.photo']
        created_photos = InitialPhoto
        
        sequence = 10
        for attachment in self.photo_ids:
            # Vérifier que c'est bien une image
            if not attachment.mimetype or not attachment.mimetype.startswith('image/'):
                continue
            
            # Créer la photo initiale
            photo_vals = {
                'property_id': self.property_id.id,
                'name': attachment.name or _('Photo %s') % sequence,
                'image': attachment.datas,
                'taken_date': self.taken_date,
                'photo_type': self.photo_type,
                'sequence': sequence,
            }
            
            if self.room_type_id:
                photo_vals['room_type_id'] = self.room_type_id.id
            
            created_photos |= InitialPhoto.create(photo_vals)
            sequence += 10
        
        # Supprimer les attachments temporaires
        self.photo_ids.unlink()
        
        # Message de confirmation
        if created_photos:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import réussi'),
                    'message': _('%d photo(s) importée(s) avec succès.') % len(created_photos),
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_window',
                        'res_model': 'apartment.property.initial.photo',
                        'view_mode': 'kanban,list,form',
                        'domain': [('property_id', '=', self.property_id.id)],
                        'name': _('Photos initiales - %s') % self.property_id.name,
                        'context': {'default_property_id': self.property_id.id},
                    }
                }
            }
        else:
            raise UserError(_("Aucune image valide trouvée parmi les fichiers sélectionnés."))
