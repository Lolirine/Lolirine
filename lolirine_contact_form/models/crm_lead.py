# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # ===== Informations personnelles =====
    is_company_contact = fields.Boolean(
        string="Contact professionnel",
        default=False,
        help="Cocher si le contact représente une entreprise"
    )
    company_name_contact = fields.Char(
        string="Nom de l'entreprise",
        help="Nom de l'entreprise si contact professionnel"
    )
    vat_number = fields.Char(
        string="Numéro de TVA",
        help="Numéro de TVA de l'entreprise"
    )
    
    # ===== Adresse complète =====
    contact_street = fields.Char(string="Rue")
    contact_street_number = fields.Char(string="Numéro")
    contact_street2 = fields.Char(string="Complément d'adresse")
    contact_zip = fields.Char(string="Code postal")
    contact_city = fields.Char(string="Ville")
    contact_country_id = fields.Many2one(
        'res.country', 
        string="Pays",
        default=lambda self: self.env.ref('base.be', raise_if_not_found=False)
    )
    
    # ===== Informations garde-meubles =====
    storage_type = fields.Selection([
        ('box_small', 'Petit box (< 5 m²)'),
        ('box_medium', 'Box moyen (5-10 m²)'),
        ('box_large', 'Grand box (10-15 m²)'),
        ('box_xlarge', 'Très grand box (> 15 m²)'),
        ('unknown', 'Je ne sais pas encore'),
    ], string="Type de box souhaité", default='unknown')
    
    storage_duration = fields.Selection([
        ('short', 'Court terme (< 3 mois)'),
        ('medium', 'Moyen terme (3-12 mois)'),
        ('long', 'Long terme (> 12 mois)'),
        ('unknown', 'Je ne sais pas encore'),
    ], string="Durée estimée", default='unknown')
    
    storage_content = fields.Text(
        string="Contenu à stocker",
        help="Description des biens à stocker"
    )
    
    desired_start_date = fields.Date(
        string="Date de début souhaitée"
    )
    
    how_did_you_hear = fields.Selection([
        ('google', 'Recherche Google'),
        ('facebook', 'Facebook'),
        ('recommendation', 'Recommandation'),
        ('sign', 'Panneau publicitaire'),
        ('other', 'Autre'),
    ], string="Comment nous avez-vous connu ?")
    
    special_requests = fields.Text(
        string="Demandes particulières",
        help="Accès 24h/24, assurance spéciale, etc."
    )
    
    # ===== Champs calculés =====
    full_address = fields.Char(
        string="Adresse complète",
        compute='_compute_full_address',
        store=True
    )
    
    @api.depends('contact_street', 'contact_street_number', 'contact_zip', 'contact_city')
    def _compute_full_address(self):
        for lead in self:
            parts = []
            if lead.contact_street:
                street_full = lead.contact_street
                if lead.contact_street_number:
                    street_full += f", {lead.contact_street_number}"
                parts.append(street_full)
            if lead.contact_zip and lead.contact_city:
                parts.append(f"{lead.contact_zip} {lead.contact_city}")
            lead.full_address = " - ".join(parts) if parts else ""

    def action_create_partner_and_subscription(self):
        """Créer un contact et un abonnement à partir du lead"""
        self.ensure_one()
        
        # Vérifier les informations requises
        if not self.contact_name and not self.partner_name:
            raise UserError(_("Le nom du contact est requis pour créer un client."))
        
        # Créer ou récupérer le partenaire
        partner_vals = {
            'name': self.partner_name or self.contact_name,
            'email': self.email_from,
            'phone': self.phone,
            'mobile': self.mobile,
            'street': f"{self.contact_street or ''} {self.contact_street_number or ''}".strip(),
            'street2': self.contact_street2,
            'zip': self.contact_zip,
            'city': self.contact_city,
            'country_id': self.contact_country_id.id if self.contact_country_id else False,
            'is_company': self.is_company_contact,
            'vat': self.vat_number,
        }
        
        if self.is_company_contact and self.company_name_contact:
            partner_vals['name'] = self.company_name_contact
            # Créer aussi le contact
            partner_vals['child_ids'] = [(0, 0, {
                'name': self.contact_name or self.partner_name,
                'email': self.email_from,
                'phone': self.phone,
                'type': 'contact',
            })]
        
        partner = self.env['res.partner'].create(partner_vals)
        
        # Lier le lead au partenaire
        self.write({
            'partner_id': partner.id,
        })
        
        # Convertir en opportunité si c'est un lead
        if self.type == 'lead':
            self.convert_opportunity(partner.id)
        
        # Ouvrir le formulaire de création d'abonnement pré-rempli
        return {
            'name': _('Créer un abonnement'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'context': {
                'default_partner_id': partner.id,
                'default_is_subscription': True,
                'default_origin': self.name,
                'default_note': f"""
Demande via formulaire de contact:
- Type de box souhaité: {dict(self._fields['storage_type'].selection).get(self.storage_type, 'Non spécifié')}
- Durée estimée: {dict(self._fields['storage_duration'].selection).get(self.storage_duration, 'Non spécifié')}
- Contenu à stocker: {self.storage_content or 'Non spécifié'}
- Date de début souhaitée: {self.desired_start_date or 'Non spécifié'}
- Demandes particulières: {self.special_requests or 'Aucune'}
                """.strip(),
            },
            'target': 'current',
        }

    def action_view_partner(self):
        """Voir la fiche du partenaire"""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Aucun client lié à cette opportunité."))
        return {
            'name': _('Client'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
