# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AssignDropshipSupplierWizard(models.TransientModel):
    _name = 'assign.dropship.supplier.wizard'
    _description = 'Attribuer fournisseur dropship en masse'

    supplier_id = fields.Many2one(
        'res.partner',
        string='Fournisseur dropship',
        required=True,
        domain=[('is_dropship_supplier', '=', True)],
    )
    discount_percent = fields.Float(
        string='Réduction négociée (%)',
        required=True,
        help="Pourcentage de réduction accordé par ce fournisseur (ex: 35, 40, 52.5)",
    )
    overwrite_existing = fields.Boolean(
        string='Écraser les attributions existantes',
        default=False,
        help="Si coché, remplace le fournisseur déjà attribué sur les produits sélectionnés",
    )
    product_count = fields.Integer(
        string='Produits sélectionnés',
        compute='_compute_product_count',
    )
    product_ids = fields.Many2many(
        'product.template',
        string='Produits',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            res['product_ids'] = [(6, 0, active_ids)]
        return res

    @api.depends('product_ids')
    def _compute_product_count(self):
        for wizard in self:
            wizard.product_count = len(wizard.product_ids)

    def action_assign_supplier(self):
        """Attribuer le fournisseur dropship aux produits sélectionnés"""
        self.ensure_one()

        if not self.product_ids:
            raise UserError(_("Aucun produit sélectionné."))

        if self.discount_percent < 0 or self.discount_percent > 100:
            raise UserError(_("La réduction doit être entre 0 et 100%."))

        created = 0
        updated = 0
        skipped = 0

        SupplierInfo = self.env['supplier.dropship.info']

        for product in self.product_ids:
            # Vérifier si une info dropship existe déjà pour ce produit/fournisseur
            existing = SupplierInfo.search([
                ('product_tmpl_id', '=', product.id),
                ('supplier_id', '=', self.supplier_id.id),
            ], limit=1)

            if existing:
                if self.overwrite_existing:
                    existing.write({
                        'discount_percent': self.discount_percent,
                        'is_active': True,
                    })
                    updated += 1
                    # Mettre à jour le fournisseur préféré
                    product.preferred_dropship_supplier_id = existing.id
                else:
                    skipped += 1
                    continue
            else:
                # Créer la fiche supplier.dropship.info
                vals = {
                    'product_tmpl_id': product.id,
                    'supplier_id': self.supplier_id.id,
                    'price': product.list_price,  # Prix catalogue = prix de vente
                    'discount_percent': self.discount_percent,
                    'is_dropship_capable': True,
                    'is_active': True,
                    'delay': self.supplier_id.dropship_standard_delay or 5,
                }
                new_info = SupplierInfo.create(vals)
                created += 1

                # Mettre à jour le fournisseur préféré si pas déjà défini
                if not product.preferred_dropship_supplier_id or self.overwrite_existing:
                    product.preferred_dropship_supplier_id = new_info.id

            # S'assurer que le produit est marqué dropship
            if not product.is_dropship_product:
                product.is_dropship_product = True

        message = _(
            "Attribution terminée :\n"
            "• %(created)s fiche(s) fournisseur créée(s)\n"
            "• %(updated)s fiche(s) mise(s) à jour\n"
            "• %(skipped)s produit(s) ignoré(s) (déjà attribués)",
            created=created, updated=updated, skipped=skipped,
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Attribution fournisseur'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }


class CreateDropshipPOWizard(models.TransientModel):
    _name = 'create.dropship.po.wizard'
    _description = 'Créer BC fournisseur dropshipping'

    sale_order_id = fields.Many2one(
        'sale.order', string='Commande client', required=True,
    )
    line_ids = fields.One2many(
        'create.dropship.po.wizard.line', 'wizard_id', string='Lignes',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            sale = self.env['sale.order'].browse(active_id)
            res['sale_order_id'] = sale.id
        return res

    @api.onchange('sale_order_id')
    def _onchange_sale_order(self):
        """Pré-remplir les lignes avec les produits de la commande"""
        lines = []
        if self.sale_order_id:
            for line in self.sale_order_id.order_line:
                if not line.product_id or line.display_type:
                    continue
                product = line.product_id.product_tmpl_id

                # Chercher la fiche dropship info (prioritaire ou première active)
                dropship_info = False
                supplier = False
                discount = 0.0

                # D'abord le fournisseur préféré
                if product.preferred_dropship_supplier_id:
                    dropship_info = product.preferred_dropship_supplier_id
                    supplier = dropship_info.supplier_id
                    discount = dropship_info.discount_percent

                # Sinon, chercher la première fiche active
                if not dropship_info:
                    dropship_info = self.env['supplier.dropship.info'].search([
                        ('product_tmpl_id', '=', product.id),
                        ('is_active', '=', True),
                    ], order='is_priority desc, sequence', limit=1)
                    if dropship_info:
                        supplier = dropship_info.supplier_id
                        discount = dropship_info.discount_percent

                # Ou si déjà sélectionné sur la ligne de commande
                if line.dropship_supplier_id:
                    supplier = line.dropship_supplier_id
                    if line.dropship_supplier_info_id:
                        discount = line.dropship_supplier_info_id.discount_percent

                lines.append((0, 0, {
                    'sale_line_id': line.id,
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'quantity': line.product_uom_qty,
                    'sale_price': line.price_unit,
                    'supplier_id': supplier.id if supplier else False,
                    'discount_percent': discount,
                    'catalog_price': line.price_unit,  # Prix catalogue = prix de vente
                }))
        self.line_ids = lines

    def action_create_purchase_orders(self):
        """Créer les BC fournisseur groupés par fournisseur"""
        self.ensure_one()

        # Vérifier que toutes les lignes ont un fournisseur
        lines_without_supplier = self.line_ids.filtered(lambda l: not l.supplier_id)
        if lines_without_supplier:
            products = ', '.join(lines_without_supplier.mapped('product_name'))
            raise UserError(_(
                "Les produits suivants n'ont pas de fournisseur assigné :\n%s\n\n"
                "Veuillez attribuer un fournisseur à chaque ligne.", products
            ))

        # Grouper les lignes par fournisseur
        lines_by_supplier = {}
        for line in self.line_ids:
            supplier_id = line.supplier_id.id
            lines_by_supplier.setdefault(supplier_id, []).append(line)

        created_pos = self.env['purchase.order']
        sale = self.sale_order_id
        config = self.env['dropship.config'].get_config()

        for supplier_id, lines in lines_by_supplier.items():
            supplier = self.env['res.partner'].browse(supplier_id)

            # Créer le bon de commande
            po_vals = {
                'partner_id': supplier_id,
                'dropship_sale_id': sale.id,
                'is_dropship_order': True,
                'dest_address_id': sale.partner_shipping_id.id,
                'origin': sale.name,
                'notes': sale._prepare_dropship_notes(supplier, config),
            }
            po = self.env['purchase.order'].create(po_vals)

            # Créer les lignes du BC
            for wiz_line in lines:
                # Calculer le prix d'achat négocié
                purchase_price = wiz_line.catalog_price * (1 - wiz_line.discount_percent / 100)

                # Chercher la ref fournisseur
                supplier_ref = ''
                info = self.env['supplier.dropship.info'].search([
                    ('product_tmpl_id', '=', wiz_line.product_id.product_tmpl_id.id),
                    ('supplier_id', '=', supplier_id),
                    ('is_active', '=', True),
                ], limit=1)
                if info:
                    supplier_ref = info.supplier_product_ref or ''

                po_line_vals = {
                    'order_id': po.id,
                    'product_id': wiz_line.product_id.id,
                    'name': (supplier_ref + ' - ' if supplier_ref else '') + wiz_line.product_name,
                    'product_qty': wiz_line.quantity,
                    'product_uom': wiz_line.sale_line_id.product_uom.id,
                    'price_unit': purchase_price,
                    'date_planned': fields.Datetime.now(),
                    'sale_line_id': wiz_line.sale_line_id.id,
                    'supplier_product_ref': supplier_ref,
                }
                self.env['purchase.order.line'].create(po_line_vals)

                # Mettre à jour la ligne de vente
                wiz_line.sale_line_id.write({
                    'dropship_supplier_id': supplier_id,
                    'dropship_supplier_cost': purchase_price * wiz_line.quantity,
                    'dropship_supplier_info_id': info.id if info else False,
                })

            created_pos |= po
            _logger.info(
                "Dropship PO %s created for SO %s (supplier: %s, lines: %d)",
                po.name, sale.name, supplier.name, len(lines)
            )

        # Mettre à jour le statut dropship
        if created_pos:
            sale.dropship_status = 'po_created'
            sale.message_post(
                body=_(
                    "📋 %(count)s bon(s) de commande fournisseur créé(s) en brouillon.<br/>"
                    "Fournisseurs : %(suppliers)s",
                    count=len(created_pos),
                    suppliers=', '.join(created_pos.mapped('partner_id.name')),
                )
            )

        # Ouvrir les BC créés
        if len(created_pos) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'res_id': created_pos.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_pos.ids)],
            'target': 'current',
        }


class CreateDropshipPOWizardLine(models.TransientModel):
    _name = 'create.dropship.po.wizard.line'
    _description = 'Ligne wizard BC dropshipping'

    wizard_id = fields.Many2one('create.dropship.po.wizard', required=True, ondelete='cascade')
    sale_line_id = fields.Many2one('sale.order.line', string='Ligne commande')
    product_id = fields.Many2one('product.product', string='Produit', required=True)
    product_name = fields.Char(string='Description')
    quantity = fields.Float(string='Quantité', default=1.0)
    sale_price = fields.Float(string='Prix de vente HT')
    catalog_price = fields.Float(string='Prix catalogue fournisseur HT')
    supplier_id = fields.Many2one(
        'res.partner', string='Fournisseur',
        domain=[('is_dropship_supplier', '=', True)],
    )
    discount_percent = fields.Float(string='Réduction (%)')
    purchase_price = fields.Float(
        string="Prix d'achat négocié",
        compute='_compute_purchase_price',
    )
    margin = fields.Float(string='Marge', compute='_compute_purchase_price')
    margin_percent = fields.Float(string='Marge %', compute='_compute_purchase_price')

    @api.depends('catalog_price', 'discount_percent', 'sale_price', 'quantity')
    def _compute_purchase_price(self):
        for line in self:
            line.purchase_price = line.catalog_price * (1 - line.discount_percent / 100)
            line.margin = (line.sale_price - line.purchase_price) * line.quantity
            line.margin_percent = (
                (line.sale_price - line.purchase_price) / line.sale_price * 100
                if line.sale_price else 0
            )

    @api.onchange('supplier_id')
    def _onchange_supplier_id(self):
        """Mettre à jour la réduction quand on change de fournisseur"""
        if self.supplier_id and self.product_id:
            info = self.env['supplier.dropship.info'].search([
                ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                ('supplier_id', '=', self.supplier_id.id),
                ('is_active', '=', True),
            ], limit=1)
            if info:
                self.discount_percent = info.discount_percent
                self.catalog_price = info.price
