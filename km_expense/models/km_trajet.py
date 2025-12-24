# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import date


class KmTrajet(models.Model):
    """Trajet professionnel pour le calcul des indemnités kilométriques"""
    _name = 'km.trajet'
    _description = 'Trajet Professionnel'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default='Nouveau',
    )
    
    # Informations de base
    date = fields.Date(
        string='Date du trajet',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True,
    )
    
    # Véhicule (soit du parc, soit personnel)
    type_vehicule_utilise = fields.Selection([
        ('parc', 'Véhicule de société'),
        ('personnel', 'Véhicule personnel'),
    ], string='Type de véhicule', default='personnel', required=True)
    
    vehicule_id = fields.Many2one(
        'fleet.vehicle',
        string='Véhicule de société',
    )
    
    vehicule_personnel_id = fields.Many2one(
        'km.vehicule.personnel',
        string='Véhicule personnel',
    )
    
    # === NOUVEAU : Lieux prédéfinis ===
    use_predefined = fields.Boolean(
        string='Utiliser destination prédéfinie',
        default=True,
    )
    
    lieu_depart_predef_id = fields.Many2one(
        'km.lieu.depart',
        string='Lieu de départ',
        domain="[('active', '=', True)]",
    )
    
    destination_predef_id = fields.Many2one(
        'km.destination',
        string='Destination',
        domain="[('active', '=', True)]",
    )
    
    # Points de trajet (manuels ou calculés)
    lieu_depart = fields.Char(
        string='Lieu de départ',
        compute='_compute_lieux',
        store=True,
        readonly=False,
        tracking=True,
    )
    lieu_arrivee = fields.Char(
        string='Lieu d\'arrivée',
        compute='_compute_lieux',
        store=True,
        readonly=False,
        tracking=True,
    )
    
    # Trajet aller-retour
    aller_retour = fields.Boolean(
        string='Aller-retour',
        default=True,
        help="Cocher si le trajet est un aller-retour",
    )
    
    # Distance
    distance_aller = fields.Float(
        string='Distance aller (km)',
        digits=(10, 1),
    )
    distance = fields.Float(
        string='Distance totale (km)',
        compute='_compute_distance',
        store=True,
        digits=(10, 1),
    )
    
    # Bouton pour calculer la distance automatiquement
    distance_calculee = fields.Boolean(
        string='Distance calculée auto',
        default=False,
    )
    
    # Catégorie et motif
    categorie_id = fields.Many2one(
        'km.trajet.categorie',
        string='Catégorie',
        required=True,
    )
    motif = fields.Text(
        string='Motif du déplacement',
        required=True,
        tracking=True,
    )
    
    # Client/Fournisseur associé
    partner_id = fields.Many2one(
        'res.partner',
        string='Client/Fournisseur',
        help="Client ou fournisseur visité lors de ce trajet",
    )
    
    # Calcul de l'indemnité
    puissance_fiscale = fields.Selection([
        ('3', '3 CV et moins'),
        ('4', '4 CV'),
        ('5', '5 CV'),
        ('6', '6 CV'),
        ('7', '7 CV et plus'),
    ], string='Puissance Fiscale',
       compute='_compute_puissance_fiscale',
       store=True,
       readonly=False,
       default='7',
    )
    
    type_vehicule_km = fields.Selection([
        ('voiture', 'Voiture'),
        ('moto', 'Moto (> 50cc)'),
        ('cyclomoteur', 'Cyclomoteur (< 50cc)'),
        ('velo', 'Vélo / VAE'),
    ], string='Type véhicule IK',
       compute='_compute_puissance_fiscale',
       store=True,
       readonly=False,
       default='voiture',
    )
    
    bareme_id = fields.Many2one(
        'km.bareme',
        string='Barème appliqué',
        compute='_compute_bareme',
        store=True,
        readonly=False,  # Permet la modification manuelle
    )
    
    taux_km = fields.Float(
        string='Taux (€/km)',
        compute='_compute_montant_indemnite',
        store=True,
        digits=(10, 4),
        readonly=False,  # Permet la modification manuelle
    )
    
    montant_indemnite = fields.Float(
        string='Montant Indemnité (€)',
        compute='_compute_montant_indemnite',
        store=True,
        digits=(10, 2),
        tracking=True,
        readonly=False,  # Permet la modification manuelle
    )
    
    # Statut
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('soumis', 'Soumis'),
        ('valide', 'Validé'),
        ('refuse', 'Refusé'),
        ('rembourse', 'Remboursé'),
    ], string='Statut', default='brouillon', tracking=True)
    
    # Lien avec les notes de frais
    expense_id = fields.Many2one(
        'hr.expense',
        string='Note de frais',
        readonly=True,
        copy=False,
    )
    
    # Lien avec les factures
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture liée',
        readonly=True,
        copy=False,
        domain="[('move_type', 'in', ['in_invoice', 'out_invoice'])]",
    )
    
    # Lien avec les événements (visites, signatures, etc.)
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Événement lié',
        readonly=True,
        copy=False,
    )
    
    # Type d'événement ayant généré le trajet
    origine_trajet = fields.Selection([
        ('manuel', 'Saisie manuelle'),
        ('facture_fournisseur', 'Facture fournisseur'),
        ('facture_client', 'Facture client'),
        ('visite_box', 'Visite box'),
        ('signature_contrat', 'Signature contrat'),
        ('rdv_client', 'Rendez-vous client'),
        ('autre', 'Autre'),
    ], string='Origine', default='manuel')
    
    # Champs de comptabilisation
    comptabilise = fields.Boolean(
        string='Comptabilisé',
        default=False,
        copy=False,
        help="Indique si ce trajet a été comptabilisé",
    )
    date_comptabilisation = fields.Date(
        string='Date de comptabilisation',
        copy=False,
    )
    account_move_id = fields.Many2one(
        'account.move',
        string='Écriture comptable',
        copy=False,
        readonly=True,
    )
    
    # Champs techniques
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Devise',
    )
    
    notes = fields.Text(string='Notes internes')
    
    # Pièces jointes
    justificatif_ids = fields.Many2many(
        'ir.attachment',
        string='Justificatifs',
        help="Tickets de péage, parking, etc.",
    )
    
    # Alerte changement de trimestre
    alerte_trimestre = fields.Html(
        string='Alerte Trimestre',
        compute='_compute_alerte_trimestre',
    )
    
    # Info barème actuel
    info_bareme = fields.Char(
        string='Info Barème',
        compute='_compute_info_bareme',
    )

    @api.depends('date')
    def _compute_info_bareme(self):
        """Affiche les informations sur le barème actuel"""
        Bareme = self.env['km.bareme']
        for trajet in self:
            date_trajet = trajet.date or fields.Date.today()
            
            # Utiliser la méthode avec fallback
            bareme = Bareme.get_bareme_applicable(date_trajet, '7', 'voiture')
            
            if bareme:
                date_fin_str = bareme.date_fin.strftime('%d/%m/%Y') if bareme.date_fin else '...'
                
                # Vérifier si c'est un barème en cours ou un fallback (ancien barème)
                is_fallback = bareme.date_fin and bareme.date_fin < date_trajet
                
                if is_fallback:
                    trajet.info_bareme = f"⚠️ Barème {bareme.taux_jusqu_5000:.4f} €/km utilisé (période {bareme.date_debut.strftime('%d/%m/%Y')} au {date_fin_str}) - Nouveau barème non configuré"
                else:
                    trajet.info_bareme = f"Barème actif : {bareme.taux_jusqu_5000:.4f} €/km (du {bareme.date_debut.strftime('%d/%m/%Y')} au {date_fin_str})"
            else:
                trajet.info_bareme = "⚠️ Aucun barème configuré"

    @api.depends('date')
    def _compute_alerte_trimestre(self):
        """Calcule l'alerte de changement de trimestre"""
        alerte_info = self.env['km.bareme'].check_alerte_changement_trimestre()
        for trajet in self:
            if alerte_info:
                if alerte_info['type'] == 'warning':
                    trajet.alerte_trimestre = f'''
                        <div class="alert alert-warning" role="alert">
                            <i class="fa fa-exclamation-triangle"></i> {alerte_info['message']}
                            <br/><small>Pensez à configurer les barèmes du prochain trimestre dans Configuration &gt; Barèmes.</small>
                        </div>
                    '''
                elif alerte_info['type'] == 'changement':
                    trajet.alerte_trimestre = f'''
                        <div class="alert alert-info" role="alert">
                            <i class="fa fa-info-circle"></i> {alerte_info['message']}
                        </div>
                    '''
                else:
                    trajet.alerte_trimestre = False
            else:
                trajet.alerte_trimestre = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('km.trajet') or 'Nouveau'
        return super().create(vals_list)

    @api.depends('lieu_depart_predef_id', 'destination_predef_id', 'use_predefined')
    def _compute_lieux(self):
        for trajet in self:
            if trajet.use_predefined:
                if trajet.lieu_depart_predef_id:
                    trajet.lieu_depart = trajet.lieu_depart_predef_id.adresse_complete
                if trajet.destination_predef_id:
                    trajet.lieu_arrivee = trajet.destination_predef_id.adresse_complete

    @api.depends('distance_aller', 'aller_retour')
    def _compute_distance(self):
        for trajet in self:
            if trajet.aller_retour:
                trajet.distance = trajet.distance_aller * 2
            else:
                trajet.distance = trajet.distance_aller

    @api.depends('type_vehicule_utilise', 'vehicule_id', 'vehicule_personnel_id')
    def _compute_puissance_fiscale(self):
        for trajet in self:
            puissance = '7'  # Valeur par défaut
            type_veh = 'voiture'
            
            if trajet.type_vehicule_utilise == 'parc' and trajet.vehicule_id:
                puissance = trajet.vehicule_id.puissance_fiscale or '7'
                type_veh = trajet.vehicule_id.type_vehicule_km or 'voiture'
            elif trajet.type_vehicule_utilise == 'personnel' and trajet.vehicule_personnel_id:
                puissance = trajet.vehicule_personnel_id.puissance_fiscale or '7'
                type_veh = trajet.vehicule_personnel_id.type_vehicule or 'voiture'
            
            trajet.puissance_fiscale = puissance
            trajet.type_vehicule_km = type_veh

    @api.depends('date', 'puissance_fiscale', 'type_vehicule_km')
    def _compute_bareme(self):
        Bareme = self.env['km.bareme']
        for trajet in self:
            date_trajet = trajet.date or fields.Date.today()
            puissance = trajet.puissance_fiscale or '7'
            type_veh = trajet.type_vehicule_km or 'voiture'
            
            trajet.bareme_id = Bareme.get_bareme_applicable(
                date_trajet,
                puissance,
                type_veh,
            )

    @api.depends('distance', 'bareme_id', 'employee_id', 'date')
    def _compute_montant_indemnite(self):
        for trajet in self:
            # Si pas de barème, essayer de le trouver
            if not trajet.bareme_id:
                date_trajet = trajet.date or fields.Date.today()
                puissance = trajet.puissance_fiscale or '7'
                type_veh = trajet.type_vehicule_km or 'voiture'
                bareme = self.env['km.bareme'].get_bareme_applicable(date_trajet, puissance, type_veh)
            else:
                bareme = trajet.bareme_id
            
            # Si toujours pas de barème ou distance <= 0
            if not bareme:
                trajet.taux_km = 0.0
                trajet.montant_indemnite = 0.0
                continue
            
            # Afficher le taux même si distance = 0
            trajet.taux_km = bareme.taux_jusqu_5000
            
            if trajet.distance <= 0:
                trajet.montant_indemnite = 0.0
                continue
            
            # Calcul du cumul annuel pour cet employé
            if trajet.employee_id and trajet.date:
                debut_annee = date(trajet.date.year, 1, 1)
                trajets_annee = self.search([
                    ('employee_id', '=', trajet.employee_id.id),
                    ('date', '>=', debut_annee),
                    ('date', '<', trajet.date),
                    ('state', 'in', ('valide', 'rembourse')),
                    ('id', '!=', trajet.id if trajet.id else 0),
                ])
                cumul_km = sum(trajets_annee.mapped('distance'))
            else:
                cumul_km = 0
            
            # Calcul avec le cumul
            total_avec_trajet = cumul_km + trajet.distance
            montant_total = bareme.calculer_indemnite(total_avec_trajet)
            montant_cumul = bareme.calculer_indemnite(cumul_km)
            
            trajet.montant_indemnite = montant_total - montant_cumul
            # Recalculer le taux effectif si distance > 0
            if trajet.distance > 0:
                trajet.taux_km = trajet.montant_indemnite / trajet.distance

    @api.onchange('type_vehicule_utilise')
    def _onchange_type_vehicule(self):
        if self.type_vehicule_utilise == 'parc':
            self.vehicule_personnel_id = False
        else:
            self.vehicule_id = False

    @api.onchange('date', 'puissance_fiscale', 'type_vehicule_km')
    def _onchange_recalc_bareme(self):
        """Recalculer le barème quand les paramètres changent"""
        date_trajet = self.date or fields.Date.today()
        puissance = self.puissance_fiscale or '7'
        type_veh = self.type_vehicule_km or 'voiture'
        
        self.bareme_id = self.env['km.bareme'].get_bareme_applicable(
            date_trajet,
            puissance,
            type_veh,
        )
        # Mettre à jour le taux
        if self.bareme_id:
            self.taux_km = self.bareme_id.taux_jusqu_5000

    @api.onchange('distance_aller', 'aller_retour', 'bareme_id', 'taux_km')
    def _onchange_recalc_montant(self):
        """Recalculer le montant quand la distance, le barème ou le taux change"""
        # Calculer la distance totale
        if self.aller_retour:
            self.distance = self.distance_aller * 2
        else:
            self.distance = self.distance_aller
        
        # Si on change le barème, mettre à jour le taux
        if self.bareme_id and not self.env.context.get('skip_taux_update'):
            self.taux_km = self.bareme_id.taux_jusqu_5000
        
        # Calculer le montant (distance × taux)
        if self.taux_km and self.distance > 0:
            self.montant_indemnite = self.distance * self.taux_km
        else:
            self.montant_indemnite = 0.0

    @api.onchange('montant_indemnite')
    def _onchange_montant_manuel(self):
        """Recalculer le taux si on modifie le montant manuellement"""
        if self.distance > 0 and self.montant_indemnite > 0:
            # Calculer le taux implicite
            nouveau_taux = self.montant_indemnite / self.distance
            # Ne mettre à jour que si significativement différent (éviter boucles)
            if abs(nouveau_taux - (self.taux_km or 0)) > 0.0001:
                self.taux_km = nouveau_taux

    @api.onchange('use_predefined')
    def _onchange_use_predefined(self):
        """Réinitialiser les champs selon le mode choisi"""
        if not self.use_predefined:
            self.lieu_depart_predef_id = False
            self.destination_predef_id = False
        else:
            # Sélectionner le lieu de départ par défaut
            default_depart = self.env['km.lieu.depart'].get_default()
            if default_depart:
                self.lieu_depart_predef_id = default_depart

    @api.onchange('destination_predef_id')
    def _onchange_destination_predef(self):
        """Mettre à jour le motif et le partenaire depuis la destination"""
        if self.destination_predef_id:
            # Mettre à jour le partenaire si lié
            if self.destination_predef_id.partner_id:
                self.partner_id = self.destination_predef_id.partner_id
            # Proposer un motif par défaut
            if not self.motif:
                type_label = dict(self.destination_predef_id._fields['type_destination'].selection).get(
                    self.destination_predef_id.type_destination, ''
                )
                self.motif = f"Visite {type_label}: {self.destination_predef_id.name}"

    @api.onchange('lieu_depart_predef_id', 'destination_predef_id')
    def _onchange_predef_distance(self):
        """Mettre à jour la distance quand on change la destination prédéfinie"""
        if self.use_predefined and self.lieu_depart_predef_id and self.destination_predef_id:
            distance = self.destination_predef_id.get_distance_from(self.lieu_depart_predef_id.id)
            if distance > 0:
                self.distance_aller = distance
                self.distance_calculee = True
                # Recalculer le montant
                if self.aller_retour:
                    self.distance = distance * 2
                else:
                    self.distance = distance
                if self.bareme_id:
                    self.taux_km = self.bareme_id.taux_jusqu_5000
                    self.montant_indemnite = self.distance * self.taux_km

    def action_calculer_distance(self):
        """Calculer la distance via API"""
        self.ensure_one()
        if not self.lieu_depart or not self.lieu_arrivee:
            raise UserError("Veuillez renseigner les adresses de départ et d'arrivée.")
        
        calculator = self.env['km.distance.calculator']
        distance = calculator.calculate_distance(self.lieu_depart, self.lieu_arrivee)
        
        if distance > 0:
            # Si l'enregistrement existe déjà, utiliser write()
            if self.id:
                self.write({
                    'distance_aller': distance,
                    'distance_calculee': True,
                })
                # Recharger le formulaire pour afficher la nouvelle valeur
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'km.trajet',
                    'res_id': self.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                # Pour un nouvel enregistrement, retourner une notification avec la valeur
                # L'utilisateur devra la saisir manuellement
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Distance calculée',
                        'message': f'Distance calculée : {distance} km. Veuillez saisir cette valeur dans le champ "Distance aller".',
                        'type': 'success',
                        'sticky': True,
                    }
                }
        else:
            raise UserError(
                "Impossible de calculer la distance automatiquement.\n"
                "Vérifiez les adresses ou configurez une clé API dans les paramètres système:\n"
                "- km_expense.distance_api_key\n"
                "- km_expense.distance_api_provider (google ou openroute)"
            )

    @api.constrains('distance_aller', 'state')
    def _check_distance(self):
        for trajet in self:
            # Ne vérifier que si on n'est plus en brouillon
            if trajet.state != 'brouillon' and trajet.distance_aller <= 0:
                raise ValidationError("La distance doit être supérieure à 0.")

    def action_soumettre(self):
        """Soumettre le trajet pour validation"""
        for trajet in self:
            if trajet.state != 'brouillon':
                raise UserError("Seuls les trajets en brouillon peuvent être soumis.")
            if trajet.distance_aller <= 0:
                raise UserError("Veuillez renseigner la distance avant de soumettre.")
            trajet.state = 'soumis'

    def action_valider(self):
        """Valider le trajet"""
        for trajet in self:
            if trajet.state != 'soumis':
                raise UserError("Seuls les trajets soumis peuvent être validés.")
            trajet.state = 'valide'

    def action_refuser(self):
        """Refuser le trajet"""
        for trajet in self:
            if trajet.state != 'soumis':
                raise UserError("Seuls les trajets soumis peuvent être refusés.")
            trajet.state = 'refuse'

    def action_remettre_brouillon(self):
        """Remettre en brouillon"""
        for trajet in self:
            if trajet.state in ('rembourse',):
                raise UserError("Un trajet remboursé ne peut pas être remis en brouillon.")
            trajet.state = 'brouillon'

    def action_creer_note_frais(self):
        """Créer une note de frais à partir du trajet"""
        self.ensure_one()
        if self.state != 'valide':
            raise UserError("Le trajet doit être validé avant de créer une note de frais.")
        if self.expense_id:
            raise UserError("Une note de frais existe déjà pour ce trajet.")
        
        # Recherche du produit pour les indemnités kilométriques
        product = self.env.ref('km_expense.product_indemnite_km', raise_if_not_found=False)
        if not product:
            product = self.env['product.product'].search([
                ('can_be_expensed', '=', True),
                ('default_code', '=', 'IK'),
            ], limit=1)
        
        if not product:
            raise UserError(
                "Veuillez configurer un produit pour les indemnités kilométriques."
            )
        
        expense_vals = {
            'name': f"IK - {self.name} - {self.lieu_depart} → {self.lieu_arrivee}",
            'employee_id': self.employee_id.id,
            'product_id': product.id,
            'quantity': self.distance,
            'unit_amount': self.taux_km,
            'total_amount': self.montant_indemnite,
            'date': self.date,
            'description': f"Trajet: {self.lieu_depart} → {self.lieu_arrivee}\n"
                          f"Motif: {self.motif}\n"
                          f"Distance: {self.distance} km",
        }
        
        expense = self.env['hr.expense'].create(expense_vals)
        self.expense_id = expense
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Note de frais',
            'res_model': 'hr.expense',
            'res_id': expense.id,
            'view_mode': 'form',
        }

    def action_voir_note_frais(self):
        """Ouvrir la note de frais associée"""
        self.ensure_one()
        if not self.expense_id:
            raise UserError("Aucune note de frais associée à ce trajet.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Note de frais',
            'res_model': 'hr.expense',
            'res_id': self.expense_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_voir_facture(self):
        """Ouvrir la facture associée"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError("Aucune facture associée à ce trajet.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_recalculer_bareme(self):
        """Recalculer le barème et le montant pour ce trajet"""
        for trajet in self:
            # Récupérer le barème applicable
            date_trajet = trajet.date or fields.Date.today()
            puissance = trajet.puissance_fiscale or '7'
            type_vehicule = trajet.type_vehicule_km or 'voiture'
            
            bareme = self.env['km.bareme'].get_bareme_applicable(
                date_trajet, puissance, type_vehicule
            )
            
            if bareme:
                taux = bareme.taux_jusqu_5000
                montant = trajet.distance * taux
                
                trajet.write({
                    'bareme_id': bareme.id,
                    'taux_km': taux,
                    'montant_indemnite': montant,
                })
            else:
                raise UserError(f"Aucun barème trouvé pour la date {date_trajet}, puissance {puissance}, type {type_vehicule}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Barème recalculé',
                'message': f'{len(self)} trajet(s) mis à jour avec succès.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_recalculer_bareme_selection(self):
        """Action serveur pour recalculer le barème sur une sélection de trajets"""
        return self.action_recalculer_bareme()

    def action_voir_ecriture_comptable(self):
        """Ouvrir l'écriture comptable associée"""
        self.ensure_one()
        if not self.account_move_id:
            raise UserError("Aucune écriture comptable associée à ce trajet.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Écriture comptable',
            'res_model': 'account.move',
            'res_id': self.account_move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_annuler_comptabilisation(self):
        """Annuler la comptabilisation d'un trajet"""
        for trajet in self:
            if trajet.account_move_id:
                if trajet.account_move_id.state == 'posted':
                    raise UserError(f"L'écriture comptable {trajet.account_move_id.name} est validée. Annulez-la d'abord.")
                # Ne pas supprimer l'écriture, juste délier
            trajet.write({
                'comptabilise': False,
                'date_comptabilisation': False,
                'account_move_id': False,
            })


class KmTrajetCategorie(models.Model):
    """Catégories de trajets"""
    _name = 'km.trajet.categorie'
    _description = 'Catégorie de Trajet'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Séquence', default=10)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Couleur')
    
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, company_id)', 'Le code doit être unique!')
    ]
