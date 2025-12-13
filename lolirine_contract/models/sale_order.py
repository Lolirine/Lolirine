# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Champs spécifiques au contrat de garde-meubles
    contract_access_code = fields.Char(
        string="Code d'accès",
        help="Code d'accès personnel attribué au client pour entrer dans le garde-meubles"
    )
    
    contract_forklift_code = fields.Char(
        string="Code gerbeur",
        help="Code pour l'utilisation du gerbeur/élévateur"
    )
    
    contract_deposit_date = fields.Date(
        string="Date de dépôt des effets",
        help="Date prévue pour le dépôt des effets dans le box"
    )
    
    contract_signature_date = fields.Date(
        string="Date de signature",
        default=fields.Date.context_today,
        help="Date de signature du contrat"
    )
    
    contract_signature_location = fields.Char(
        string="Lieu de signature",
        default="Boninne",
        help="Lieu où le contrat est signé"
    )
    
    # Montants calculés
    contract_deposit_amount = fields.Monetary(
        string="Montant caution",
        compute='_compute_contract_amounts',
        store=True,
        help="Montant du dépôt de garantie (2 mois de loyer)"
    )
    
    contract_monthly_rent = fields.Monetary(
        string="Loyer mensuel",
        compute='_compute_contract_amounts',
        store=True,
        help="Montant du loyer mensuel récurrent"
    )
    
    contract_dossier_fees = fields.Monetary(
        string="Frais de dossier",
        compute='_compute_contract_amounts',
        store=True,
        help="Frais de dossier unique"
    )

    @api.depends('order_line', 'order_line.price_subtotal', 'order_line.product_id')
    def _compute_contract_amounts(self):
        """Calcule les montants du contrat à partir des lignes de commande"""
        for order in self:
            monthly_rent = 0.0
            dossier_fees = 0.0
            
            for line in order.order_line:
                # Identifier le loyer mensuel (produit récurrent)
                if line.product_id and line.product_id.recurring_invoice:
                    monthly_rent += line.price_subtotal
                # Identifier les frais de dossier (nom contenant "dossier" ou "frais")
                elif line.product_id and ('dossier' in (line.product_id.name or '').lower() 
                                          or 'frais' in (line.product_id.name or '').lower()):
                    dossier_fees += line.price_subtotal
            
            order.contract_monthly_rent = monthly_rent
            order.contract_dossier_fees = dossier_fees
            order.contract_deposit_amount = monthly_rent * 2  # 2 mois de caution

    def get_box_info(self):
        """Retourne les informations du box depuis les lignes de commande"""
        self.ensure_one()
        box_info = {
            'name': '',
            'dimensions': '',
            'volume': '',
            'location': 'Rue de la Drève Boninnas 2, B-5021 BONINNE',
            'width': '',
            'depth': '',
            'height': '',
        }
        
        for line in self.order_line:
            product = line.product_id
            if product and product.is_storage_box if hasattr(product, 'is_storage_box') else False:
                # Récupérer les infos du produit box
                box_info['name'] = product.name or ''
                
                # Essayer de récupérer les attributs du produit
                for attr_line in product.attribute_line_ids if hasattr(product, 'attribute_line_ids') else []:
                    attr_name = attr_line.attribute_id.name.lower() if attr_line.attribute_id else ''
                    for value in attr_line.value_ids:
                        if 'largeur' in attr_name:
                            box_info['width'] = value.name
                        elif 'profondeur' in attr_name:
                            box_info['depth'] = value.name
                        elif 'hauteur' in attr_name:
                            box_info['height'] = value.name
                        elif 'volume' in attr_name:
                            box_info['volume'] = value.name
                
                # Si pas d'attributs, chercher dans la description
                if product.description_sale:
                    box_info['description'] = product.description_sale
                    
                break  # On prend le premier box trouvé
        
        # Construire la chaîne de dimensions
        if box_info['width'] or box_info['depth'] or box_info['height']:
            dims = []
            if box_info['width']:
                dims.append(f"Largeur {box_info['width']}")
            if box_info['depth']:
                dims.append(f"Profondeur {box_info['depth']}")
            if box_info['height']:
                dims.append(f"Hauteur {box_info['height']}")
            box_info['dimensions'] = ', '.join(dims)
        
        return box_info

    def action_send_contract(self):
        """Action pour envoyer le contrat par email"""
        self.ensure_one()
        template = self.env.ref('lolirine_contract.email_template_contract', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Contrat envoyé',
                    'message': f'Le contrat a été envoyé à {self.partner_id.email}',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Erreur',
                    'message': 'Modèle d\'email non trouvé',
                    'type': 'danger',
                    'sticky': False,
                }
            }
