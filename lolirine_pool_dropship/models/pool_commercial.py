# -*- coding: utf-8 -*-
"""Commerciaux fournisseurs sur les devis piscine et les bons de commande
fournisseur : qui appeler ou à qui écrire quand un article pose problème
(prix « sur devis », référence douteuse, délai…).

Un commercial est un contact rattaché au fournisseur (SCP Benelux, Fluidra
Benelux…) portant l'étiquette « Commercial fournisseur ». Aucun nouveau champ
en base : l'encart et le bouton sont calculés à l'affichage.
"""
from urllib.parse import quote

from markupsafe import Markup, escape

from odoo import api, fields, models

ETIQUETTE = 'Commercial fournisseur'


class PoolCommercialMixin(models.AbstractModel):
    _name = 'pool.commercial.mixin'
    _description = 'Commerciaux fournisseurs (Pool Store)'

    def _pool_fournisseurs(self):
        """Fournisseurs concernés par le document (à surcharger)."""
        return self.env['res.partner']

    def _pool_commerciaux(self):
        fournisseurs = self._pool_fournisseurs().mapped('commercial_partner_id')
        etiquette = self.env['res.partner.category'].sudo().search([('name', '=', ETIQUETTE)], limit=1)
        if not fournisseurs or not etiquette:
            return self.env['res.partner']
        return self.env['res.partner'].sudo().search([
            ('parent_id', 'in', fournisseurs.ids), ('category_id', 'in', etiquette.ids)], order='parent_id, name')

    def _pool_commerciaux_html(self):
        commerciaux = self._pool_commerciaux()
        if not commerciaux:
            return False
        sujet = quote('%s — demande d\'information' % (self.display_name or ''))
        blocs = []
        for c in commerciaux:
            morceaux = [Markup('<strong>%s</strong> — %s') % (c.parent_id.name, c.name)]
            if c.function:
                morceaux.append(Markup('<span class="text-muted">%s</span>') % c.function)
            for numero in [getattr(c, 'mobile', False), c.phone]:
                if numero:
                    morceaux.append(Markup('<a href="tel:%s"><i class="fa fa-phone" title="Téléphone"/> %s</a>') % (
                        numero.replace(' ', ''), numero))
            if c.email:
                morceaux.append(Markup('<a href="mailto:%s?subject=%s"><i class="fa fa-envelope" title="E-mail"/> %s</a>')
                                % (c.email, sujet, c.email))
            general = c.parent_id.email
            if general and general != c.email:
                morceaux.append(Markup('<span class="text-muted">général : <a href="mailto:%s?subject=%s">%s</a></span>')
                                % (general, sujet, general))
            blocs.append(Markup(' · ').join(morceaux))
        return Markup('<br/>').join(blocs)

    def action_pool_ecrire_commercial(self):
        """Message au(x) commercial(aux) depuis Odoo : envoyé par e-mail et
        gardé dans l'historique du document ; la réponse y revient."""
        self.ensure_one()
        commerciaux = self._pool_commerciaux()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': self._name,
                'default_res_ids': self.ids,
                'default_composition_mode': 'comment',
                'default_message_type': 'comment',
                'default_subtype_xmlid': 'mail.mt_comment',
                'default_partner_ids': commerciaux.ids,
                'default_subject': '%s — demande d\'information' % self.display_name,
            },
        }


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'pool.commercial.mixin']

    pool_commerciaux_html = fields.Html(compute='_compute_pool_commerciaux_html', sanitize=False)

    def _pool_fournisseurs(self):
        lignes = self.order_line.filtered('product_id')
        fournisseurs = lignes.mapped('dropship_supplier_id')
        infos = self.env['supplier.dropship.info'].sudo().search([
            ('product_tmpl_id', 'in', lignes.mapped('product_id.product_tmpl_id').ids), ('is_active', '=', True)])
        achats = self.env['purchase.order'].sudo().search([('dropship_sale_id', '=', self._origin.id)]) \
            if 'dropship_sale_id' in self.env['purchase.order']._fields and self._origin.id \
            else self.env['purchase.order']
        return fournisseurs | infos.mapped('supplier_id') | achats.mapped('partner_id')

    @api.depends('order_line.product_id')
    def _compute_pool_commerciaux_html(self):
        for so in self:
            so.pool_commerciaux_html = so._pool_commerciaux_html() if so.pool_catalogue_visible else False


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'pool.commercial.mixin']

    pool_commerciaux_html = fields.Html(compute='_compute_pool_commerciaux_html', sanitize=False)

    def _pool_fournisseurs(self):
        return self.partner_id

    @api.depends('partner_id')
    def _compute_pool_commerciaux_html(self):
        for po in self:
            po.pool_commerciaux_html = po._pool_commerciaux_html()
