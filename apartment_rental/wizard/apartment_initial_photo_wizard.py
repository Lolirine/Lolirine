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
        created_count = 0
        skipped_files = []
        
        sequence = 10
        for attachment in self.photo_ids:
            # Vérifier que c'est bien une image
            if not attachment.mimetype or not attachment.mimetype.startswith('image/'):
                skipped_files.append(attachment.name)
                continue
            
            try:
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
                
                InitialPhoto.create(photo_vals)
                created_count += 1
                sequence += 10
            except Exception:
                skipped_files.append(attachment.name)
                continue
        
        # Supprimer les attachments temporaires
        self.photo_ids.unlink()
        
        if created_count == 0:
            raise UserError(_("Aucune image valide trouvée parmi les fichiers sélectionnés."))
        
        # Message de notification
        message = _('%d photo(s) importée(s) avec succès.') % created_count
        if skipped_files:
            message += _(' %d fichier(s) ignoré(s).') % len(skipped_files)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import terminé'),
                'message': message,
                'type': 'success' if not skipped_files else 'warning',
                'sticky': False,
            }
        }


class ApartmentPropertyImageWizard(models.TransientModel):
    _name = 'apartment.property.image.wizard'
    _description = 'Import en masse de photos du bien'

    property_id = fields.Many2one(
        'apartment.property',
        string='Bien',
        required=True,
        default=lambda self: self._default_property_id(),
    )
    
    photo_ids = fields.Many2many(
        'ir.attachment',
        'apartment_property_image_wizard_attachment_rel',
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
        """Import les photos sélectionnées comme photos du bien"""
        self.ensure_one()
        
        if not self.photo_ids:
            raise UserError(_("Veuillez sélectionner au moins une photo à importer."))
        
        PropertyImage = self.env['apartment.property.image']
        created_count = 0
        skipped_files = []
        
        sequence = 10
        for attachment in self.photo_ids:
            if not attachment.mimetype or not attachment.mimetype.startswith('image/'):
                skipped_files.append(attachment.name)
                continue
            
            try:
                PropertyImage.create({
                    'property_id': self.property_id.id,
                    'name': attachment.name or _('Photo %s') % sequence,
                    'image': attachment.datas,
                    'sequence': sequence,
                })
                created_count += 1
                sequence += 10
            except Exception:
                skipped_files.append(attachment.name)
                continue
        
        self.photo_ids.unlink()
        
        if created_count == 0:
            raise UserError(_("Aucune image valide trouvée parmi les fichiers sélectionnés."))
        
        message = _('%d photo(s) importée(s) avec succès.') % created_count
        if skipped_files:
            message += _(' %d fichier(s) ignoré(s).') % len(skipped_files)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import terminé'),
                'message': message,
                'type': 'success' if not skipped_files else 'warning',
                'sticky': False,
            }
        }


class ApartmentInventoryPhotoWizard(models.TransientModel):
    _name = 'apartment.inventory.photo.wizard'
    _description = 'Import en masse de photos d\'état des lieux'

    inventory_id = fields.Many2one(
        'apartment.inventory',
        string='État des lieux',
        required=True,
        default=lambda self: self._default_inventory_id(),
    )
    
    room_type_id = fields.Many2one(
        'apartment.room.type',
        string='Pièce (optionnel)',
    )
    
    photo_type = fields.Selection([
        ('general', 'Vue générale'),
        ('detail', 'Détail'),
        ('damage', 'Dégât'),
        ('equipment', 'Équipement'),
        ('meter', 'Compteur'),
        ('key', 'Clé/Badge'),
        ('other', 'Autre'),
    ], string='Type de photo', default='general')
    
    photo_ids = fields.Many2many(
        'ir.attachment',
        'apartment_inventory_photo_wizard_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='Photos à importer',
    )
    
    @api.model
    def _default_inventory_id(self):
        if self.env.context.get('active_model') == 'apartment.inventory':
            return self.env.context.get('active_id')
        return False
    
    def action_import_photos(self):
        """Import les photos sélectionnées pour l'état des lieux"""
        self.ensure_one()
        
        if not self.photo_ids:
            raise UserError(_("Veuillez sélectionner au moins une photo à importer."))
        
        InventoryPhoto = self.env['apartment.inventory.photo']
        created_count = 0
        skipped_files = []
        
        sequence = 10
        for attachment in self.photo_ids:
            if not attachment.mimetype or not attachment.mimetype.startswith('image/'):
                skipped_files.append(attachment.name)
                continue
            
            try:
                photo_vals = {
                    'inventory_id': self.inventory_id.id,
                    'name': attachment.name or _('Photo %s') % sequence,
                    'image': attachment.datas,
                    'photo_type': self.photo_type,
                    'sequence': sequence,
                }
                
                if self.room_type_id:
                    photo_vals['room_type_id'] = self.room_type_id.id
                
                InventoryPhoto.create(photo_vals)
                created_count += 1
                sequence += 10
            except Exception:
                skipped_files.append(attachment.name)
                continue
        
        self.photo_ids.unlink()
        
        if created_count == 0:
            raise UserError(_("Aucune image valide trouvée parmi les fichiers sélectionnés."))
        
        message = _('%d photo(s) importée(s) avec succès.') % created_count
        if skipped_files:
            message += _(' %d fichier(s) ignoré(s).') % len(skipped_files)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import terminé'),
                'message': message,
                'type': 'success' if not skipped_files else 'warning',
                'sticky': False,
            }
        }


class ApartmentControlVisitPhotoWizard(models.TransientModel):
    _name = 'apartment.control.visit.photo.wizard'
    _description = 'Import en masse de photos de visite de contrôle'

    visit_id = fields.Many2one(
        'apartment.control.visit',
        string='Visite',
        required=True,
        default=lambda self: self._default_visit_id(),
    )
    
    room_type_id = fields.Many2one(
        'apartment.room.type',
        string='Pièce (optionnel)',
    )
    
    photo_type = fields.Selection([
        ('general', 'Vue générale'),
        ('anomaly', 'Anomalie'),
        ('damage', 'Dégât'),
        ('maintenance', 'Maintenance'),
        ('other', 'Autre'),
    ], string='Type de photo', default='general')
    
    photo_ids = fields.Many2many(
        'ir.attachment',
        'apartment_visit_photo_wizard_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='Photos à importer',
    )
    
    @api.model
    def _default_visit_id(self):
        if self.env.context.get('active_model') == 'apartment.control.visit':
            return self.env.context.get('active_id')
        return False
    
    def action_import_photos(self):
        """Import les photos sélectionnées pour la visite"""
        self.ensure_one()
        
        if not self.photo_ids:
            raise UserError(_("Veuillez sélectionner au moins une photo à importer."))
        
        VisitPhoto = self.env['apartment.control.visit.photo']
        created_count = 0
        skipped_files = []
        
        sequence = 10
        for attachment in self.photo_ids:
            if not attachment.mimetype or not attachment.mimetype.startswith('image/'):
                skipped_files.append(attachment.name)
                continue
            
            try:
                photo_vals = {
                    'visit_id': self.visit_id.id,
                    'name': attachment.name or _('Photo %s') % sequence,
                    'image': attachment.datas,
                    'photo_type': self.photo_type,
                    'sequence': sequence,
                }
                
                if self.room_type_id:
                    photo_vals['room_type_id'] = self.room_type_id.id
                
                VisitPhoto.create(photo_vals)
                created_count += 1
                sequence += 10
            except Exception:
                skipped_files.append(attachment.name)
                continue
        
        self.photo_ids.unlink()
        
        if created_count == 0:
            raise UserError(_("Aucune image valide trouvée parmi les fichiers sélectionnés."))
        
        message = _('%d photo(s) importée(s) avec succès.') % created_count
        if skipped_files:
            message += _(' %d fichier(s) ignoré(s).') % len(skipped_files)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import terminé'),
                'message': message,
                'type': 'success' if not skipped_files else 'warning',
                'sticky': False,
            }
        }
