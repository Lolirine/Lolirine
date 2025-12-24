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
    
    # Option pour désactiver la création auto sur cette facture spécifique
    km_skip_auto_trajet = fields.Boolean(
        string='Ne pas créer de trajet auto',
        default=False,
        help="Cocher pour ne pas créer automatiquement de trajet lors de la validation",
    )
    
    # Indique si un trajet auto a déjà été créé
    km_trajet_auto_created = fields.Boolean(
        string='Trajet auto créé',
        default=False,
        copy=False,
    )

    @api.depends('km_trajet_ids')
    def _compute_km_trajet_count(self):
        for move in self:
            move.km_trajet_count = len(move.km_trajet_ids)

    def action_post(self):
        """Surcharge pour créer automatiquement les trajets lors de la validation"""
        res = super().action_post()
        
        for move in self:
            move._create_auto_km_trajet()
        
        return res

    def _create_auto_km_trajet(self, force=False):
        """Créer automatiquement un trajet si configuré sur le partenaire
        
        Args:
            force: Si True, créer le trajet même si le partenaire n'a pas km_trajet_auto activé
        """
        self.ensure_one()
        
        # Vérifications préalables
        if self.km_skip_auto_trajet:
            return False
        
        if self.km_trajet_auto_created and not force:
            return False
        
        if not self.partner_id:
            return False
        
        # Vérifier si création auto activée (sauf si force)
        if not force and not self.partner_id.km_trajet_auto:
            return False
        
        # Vérifier le type de facture
        if self.move_type in ('in_invoice', 'in_refund'):
            if not force and self.partner_id.km_trajet_type not in ('fournisseur', 'les_deux'):
                return False
            trajet_type = 'fournisseur'
            origine = 'facture_fournisseur'
            default_categorie = self.env.ref('km_expense.categorie_fournisseur', raise_if_not_found=False)
        elif self.move_type in ('out_invoice', 'out_refund'):
            if not force and self.partner_id.km_trajet_type not in ('client', 'les_deux'):
                return False
            trajet_type = 'client'
            origine = 'facture_client'
            default_categorie = self.env.ref('km_expense.categorie_client', raise_if_not_found=False)
        else:
            return False
        
        # Trouver la destination
        destination = self.partner_id.km_destination_id
        if not destination:
            # Chercher une destination prédéfinie pour ce partenaire
            destination = self.env['km.destination'].search([
                ('partner_id', '=', self.partner_id.id)
            ], limit=1)
        
        if not destination:
            # Chercher par nom similaire
            destination = self.env['km.destination'].search([
                ('name', 'ilike', self.partner_id.name)
            ], limit=1)
        
        # Trouver la catégorie
        categorie = self.partner_id.km_categorie_id or default_categorie
        
        # Trouver le lieu de départ par défaut
        lieu_depart = self.env['km.lieu.depart'].get_default()
        
        # Trouver la distance si destination trouvée
        distance_aller = 0.0
        if destination and lieu_depart:
            distance_record = self.env['km.destination.distance'].search([
                ('destination_id', '=', destination.id),
                ('lieu_depart_id', '=', lieu_depart.id),
            ], limit=1)
            if distance_record:
                distance_aller = distance_record.distance_km
        
        # Trouver l'employé lié à l'utilisateur courant
        employee = self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid)
        ], limit=1)
        
        if not employee:
            # Si pas d'employé, créer le trajet sans employé (sera à compléter)
            employee = False
        
        # Préparer les valeurs du trajet
        trajet_vals = {
            'date': self.invoice_date or fields.Date.today(),
            'employee_id': employee.id if employee else False,
            'partner_id': self.partner_id.id,
            'invoice_id': self.id,
            'origine_trajet': origine,
            'categorie_id': categorie.id if categorie else False,
            'motif': f"Facture {self.name} - {self.partner_id.name}",
            'aller_retour': self.partner_id.km_aller_retour,
            'state': 'brouillon',
        }
        
        # Mode prédéfini ou manuel
        if destination and lieu_depart and distance_aller > 0:
            trajet_vals.update({
                'use_predefined': True,
                'lieu_depart_predef_id': lieu_depart.id,
                'destination_predef_id': destination.id,
                'distance_aller': distance_aller,
            })
        else:
            # Mode manuel - utiliser l'adresse du partenaire
            adresse_partenaire = self._format_partner_address()
            lieu_depart_adresse = lieu_depart.adresse if lieu_depart else ''
            
            trajet_vals.update({
                'use_predefined': False,
                'lieu_depart': lieu_depart_adresse,
                'lieu_arrivee': adresse_partenaire,
                'distance_aller': 0.0,  # À compléter manuellement
            })
        
        # Créer le trajet
        trajet = self.env['km.trajet'].create(trajet_vals)
        
        # Marquer comme créé
        self.km_trajet_auto_created = True
        
        return trajet

    def _format_partner_address(self):
        """Formater l'adresse complète du partenaire"""
        self.ensure_one()
        parts = []
        if self.partner_id.street:
            parts.append(self.partner_id.street)
        if self.partner_id.street2:
            parts.append(self.partner_id.street2)
        if self.partner_id.zip or self.partner_id.city:
            parts.append(f"{self.partner_id.zip or ''} {self.partner_id.city or ''}".strip())
        if self.partner_id.country_id:
            parts.append(self.partner_id.country_id.name)
        return ', '.join(parts) if parts else self.partner_id.name

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
        destination = self.partner_id.km_destination_id
        if not destination:
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

    def action_create_km_trajet_auto(self):
        """Créer automatiquement un trajet pour cette facture (même brouillon)"""
        self.ensure_one()
        
        if self.km_trajet_ids:
            raise UserError("Un trajet existe déjà pour cette facture.")
        
        # Forcer la création même si pas configuré sur le partenaire
        trajet = self._create_auto_km_trajet(force=True)
        
        if trajet:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Trajet créé',
                'res_model': 'km.trajet',
                'res_id': trajet.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise UserError("Impossible de créer le trajet. Vérifiez que la facture a un partenaire.")

    def action_create_km_trajets_batch(self):
        """Créer des trajets pour plusieurs factures sélectionnées"""
        trajets_created = self.env['km.trajet']
        errors = []
        
        for move in self:
            if move.km_trajet_ids:
                errors.append(f"{move.name or 'Brouillon'}: trajet déjà existant")
                continue
            if not move.partner_id:
                errors.append(f"{move.name or 'Brouillon'}: pas de partenaire")
                continue
            
            try:
                trajet = move._create_auto_km_trajet(force=True)
                if trajet:
                    trajets_created |= trajet
            except Exception as e:
                errors.append(f"{move.name or 'Brouillon'}: {str(e)}")
        
        message = f"{len(trajets_created)} trajet(s) créé(s)"
        if errors:
            message += f"\n\nErreurs:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                message += f"\n... et {len(errors) - 10} autres erreurs"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Création de trajets',
                'message': message,
                'type': 'success' if trajets_created else 'warning',
                'sticky': True,
            }
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
