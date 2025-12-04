# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class KmTrajetFromInvoiceWizard(models.TransientModel):
    _name = 'km.trajet.from.invoice.wizard'
    _description = 'Créer un trajet depuis une facture'

    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partenaire',
        required=True,
        readonly=True,
    )
    date_trajet = fields.Date(
        string='Date du trajet',
        required=True,
        default=fields.Date.today,
    )
    trajet_type = fields.Selection([
        ('fournisseur', 'Fournisseur'),
        ('client', 'Client'),
    ], string='Type', required=True, readonly=True)
    
    categorie_id = fields.Many2one(
        'km.trajet.categorie',
        string='Catégorie',
        required=True,
    )
    
    # Mode de saisie
    use_predefined = fields.Boolean(
        string='Utiliser destination prédéfinie',
        default=True,
    )
    
    # Destination prédéfinie
    lieu_depart_predef_id = fields.Many2one(
        'km.lieu.depart',
        string='Lieu de départ',
        default=lambda self: self.env['km.lieu.depart'].get_default(),
    )
    destination_predef_id = fields.Many2one(
        'km.destination',
        string='Destination prédéfinie',
    )
    
    # Destination manuelle
    lieu_depart = fields.Char(string='Lieu de départ (manuel)')
    lieu_arrivee = fields.Char(string='Lieu d\'arrivée (manuel)')
    
    # Distance
    distance_aller = fields.Float(
        string='Distance aller (km)',
        digits=(10, 1),
    )
    aller_retour = fields.Boolean(
        string='Aller-retour',
        default=True,
    )
    
    motif = fields.Text(
        string='Motif',
        required=True,
    )
    
    # Info
    destination_found = fields.Boolean(
        string='Destination trouvée',
        compute='_compute_destination_info',
    )
    destination_info = fields.Char(
        string='Info destination',
        compute='_compute_destination_info',
    )

    @api.depends('partner_id', 'destination_predef_id')
    def _compute_destination_info(self):
        for wizard in self:
            if wizard.destination_predef_id:
                wizard.destination_found = True
                wizard.destination_info = f"✓ Destination prédéfinie trouvée : {wizard.destination_predef_id.name}"
            elif wizard.partner_id:
                # Chercher une destination pour ce partenaire
                dest = self.env['km.destination'].search([
                    '|',
                    ('partner_id', '=', wizard.partner_id.id),
                    ('name', 'ilike', wizard.partner_id.name),
                ], limit=1)
                if dest:
                    wizard.destination_found = True
                    wizard.destination_info = f"✓ Destination trouvée : {dest.name}"
                    wizard.destination_predef_id = dest
                else:
                    wizard.destination_found = False
                    wizard.destination_info = "⚠ Aucune destination prédéfinie trouvée. Utilisez l'adresse du partenaire ou saisissez manuellement."
            else:
                wizard.destination_found = False
                wizard.destination_info = ""

    @api.onchange('use_predefined')
    def _onchange_use_predefined(self):
        if self.use_predefined:
            self.lieu_depart = False
            self.lieu_arrivee = False
            # Réinitialiser le lieu de départ par défaut
            default_depart = self.env['km.lieu.depart'].get_default()
            if default_depart:
                self.lieu_depart_predef_id = default_depart
        else:
            self.lieu_depart_predef_id = False
            self.destination_predef_id = False
            # Utiliser l'adresse du partenaire
            if self.partner_id:
                self.lieu_arrivee = self._format_partner_address(self.partner_id)
            # Utiliser l'adresse par défaut pour le départ
            default_depart = self.env['km.lieu.depart'].get_default()
            if default_depart:
                self.lieu_depart = default_depart.adresse_complete

    @api.onchange('lieu_depart_predef_id', 'destination_predef_id')
    def _onchange_predef_distance(self):
        """Calculer la distance depuis les données prédéfinies"""
        if self.use_predefined and self.lieu_depart_predef_id and self.destination_predef_id:
            distance = self.destination_predef_id.get_distance_from(self.lieu_depart_predef_id.id)
            if distance > 0:
                self.distance_aller = distance

    def _format_partner_address(self, partner):
        """Formater l'adresse d'un partenaire"""
        parts = []
        if partner.street:
            parts.append(partner.street)
        if partner.street2:
            parts.append(partner.street2)
        if partner.zip or partner.city:
            parts.append(f"{partner.zip or ''} {partner.city or ''}".strip())
        if partner.country_id:
            parts.append(partner.country_id.name)
        return ', '.join(parts) if parts else partner.name

    def action_create_trajet(self):
        """Créer le trajet"""
        self.ensure_one()
        
        # Déterminer l'origine
        if self.trajet_type == 'fournisseur':
            origine = 'facture_fournisseur'
        else:
            origine = 'facture_client'
        
        # Préparer les valeurs
        vals = {
            'date': self.date_trajet,
            'employee_id': self.env.user.employee_id.id,
            'categorie_id': self.categorie_id.id,
            'partner_id': self.partner_id.id,
            'invoice_id': self.invoice_id.id,
            'origine_trajet': origine,
            'motif': self.motif,
            'aller_retour': self.aller_retour,
            'use_predefined': self.use_predefined,
        }
        
        if self.use_predefined:
            vals.update({
                'lieu_depart_predef_id': self.lieu_depart_predef_id.id,
                'destination_predef_id': self.destination_predef_id.id,
                'distance_aller': self.distance_aller,
            })
        else:
            vals.update({
                'lieu_depart': self.lieu_depart,
                'lieu_arrivee': self.lieu_arrivee,
                'distance_aller': self.distance_aller,
            })
        
        # Vérifications
        if self.use_predefined and not self.destination_predef_id:
            raise UserError("Veuillez sélectionner une destination prédéfinie ou passer en mode manuel.")
        
        if not self.use_predefined and (not self.lieu_depart or not self.lieu_arrivee):
            raise UserError("Veuillez renseigner les adresses de départ et d'arrivée.")
        
        # Créer le trajet
        trajet = self.env['km.trajet'].create(vals)
        
        # Retourner vers le trajet créé
        return {
            'name': 'Trajet créé',
            'type': 'ir.actions.act_window',
            'res_model': 'km.trajet',
            'res_id': trajet.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_and_new(self):
        """Créer le trajet et ouvrir un nouveau wizard"""
        self.action_create_trajet()
        
        return {
            'name': 'Créer un autre trajet',
            'type': 'ir.actions.act_window',
            'res_model': 'km.trajet.from.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.invoice_id.id,
                'default_partner_id': self.partner_id.id,
                'default_date_trajet': self.date_trajet,
                'default_trajet_type': self.trajet_type,
                'default_categorie_id': self.categorie_id.id,
            },
        }


class KmTrajetFromEventWizard(models.TransientModel):
    _name = 'km.trajet.from.event.wizard'
    _description = 'Créer un trajet depuis un événement'

    event_id = fields.Many2one(
        'calendar.event',
        string='Événement',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
    )
    date_trajet = fields.Date(
        string='Date du trajet',
        required=True,
        default=fields.Date.today,
    )
    
    event_type = fields.Selection([
        ('visite_box', 'Visite box'),
        ('signature_contrat', 'Signature contrat'),
        ('rdv_client', 'Rendez-vous client'),
        ('autre', 'Autre'),
    ], string='Type d\'événement', required=True, default='rdv_client')
    
    categorie_id = fields.Many2one(
        'km.trajet.categorie',
        string='Catégorie',
        required=True,
    )
    
    # Mode de saisie
    use_predefined = fields.Boolean(
        string='Utiliser destination prédéfinie',
        default=False,
    )
    
    # Destination prédéfinie
    lieu_depart_predef_id = fields.Many2one(
        'km.lieu.depart',
        string='Lieu de départ',
        default=lambda self: self.env['km.lieu.depart'].get_default(),
    )
    destination_predef_id = fields.Many2one(
        'km.destination',
        string='Destination prédéfinie',
    )
    
    # Destination manuelle (adresse du client)
    lieu_depart = fields.Char(
        string='Lieu de départ',
        default=lambda self: self._get_default_depart(),
    )
    lieu_arrivee = fields.Char(string='Lieu d\'arrivée (adresse client)')
    
    # Distance
    distance_aller = fields.Float(
        string='Distance aller (km)',
        digits=(10, 1),
    )
    aller_retour = fields.Boolean(
        string='Aller-retour',
        default=True,
    )
    
    motif = fields.Text(string='Motif')

    def _get_default_depart(self):
        default = self.env['km.lieu.depart'].get_default()
        return default.adresse_complete if default else ''

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and not self.use_predefined:
            self.lieu_arrivee = self._format_partner_address(self.partner_id)
            # Générer le motif
            event_labels = dict(self._fields['event_type'].selection)
            event_label = event_labels.get(self.event_type, '')
            self.motif = f"{event_label} - {self.partner_id.name}"

    @api.onchange('event_type')
    def _onchange_event_type(self):
        # Mettre à jour la catégorie selon le type d'événement
        if self.event_type == 'visite_box':
            cat = self.env.ref('km_expense.categorie_client', raise_if_not_found=False)
        elif self.event_type == 'signature_contrat':
            cat = self.env.ref('km_expense.categorie_client', raise_if_not_found=False)
        else:
            cat = self.env.ref('km_expense.categorie_client', raise_if_not_found=False)
        
        if cat:
            self.categorie_id = cat
        
        # Mettre à jour le motif
        if self.partner_id:
            event_labels = dict(self._fields['event_type'].selection)
            event_label = event_labels.get(self.event_type, '')
            self.motif = f"{event_label} - {self.partner_id.name}"

    def _format_partner_address(self, partner):
        """Formater l'adresse d'un partenaire"""
        parts = []
        if partner.street:
            parts.append(partner.street)
        if partner.street2:
            parts.append(partner.street2)
        if partner.zip or partner.city:
            parts.append(f"{partner.zip or ''} {partner.city or ''}".strip())
        if partner.country_id:
            parts.append(partner.country_id.name)
        return ', '.join(parts) if parts else partner.name

    @api.onchange('lieu_depart_predef_id', 'destination_predef_id')
    def _onchange_predef_distance(self):
        """Calculer la distance depuis les données prédéfinies"""
        if self.use_predefined and self.lieu_depart_predef_id and self.destination_predef_id:
            distance = self.destination_predef_id.get_distance_from(self.lieu_depart_predef_id.id)
            if distance > 0:
                self.distance_aller = distance

    def action_create_trajet(self):
        """Créer le trajet"""
        self.ensure_one()
        
        # Préparer les valeurs
        vals = {
            'date': self.date_trajet,
            'employee_id': self.env.user.employee_id.id,
            'categorie_id': self.categorie_id.id,
            'partner_id': self.partner_id.id,
            'calendar_event_id': self.event_id.id if self.event_id else False,
            'origine_trajet': self.event_type,
            'motif': self.motif,
            'aller_retour': self.aller_retour,
            'use_predefined': self.use_predefined,
        }
        
        if self.use_predefined:
            vals.update({
                'lieu_depart_predef_id': self.lieu_depart_predef_id.id,
                'destination_predef_id': self.destination_predef_id.id if self.destination_predef_id else False,
                'distance_aller': self.distance_aller,
            })
        else:
            vals.update({
                'lieu_depart': self.lieu_depart,
                'lieu_arrivee': self.lieu_arrivee,
                'distance_aller': self.distance_aller,
            })
        
        # Créer le trajet
        trajet = self.env['km.trajet'].create(vals)
        
        return {
            'name': 'Trajet créé',
            'type': 'ir.actions.act_window',
            'res_model': 'km.trajet',
            'res_id': trajet.id,
            'view_mode': 'form',
            'target': 'current',
        }
