# -*- coding: utf-8 -*-
"""Commerciaux fournisseurs sur les devis piscine et les bons de commande
fournisseur : qui appeler ou à qui écrire quand un article pose problème
(prix « sur devis », référence douteuse, délai…).

Conditions commerciales : les documents joints à la fiche du fournisseur
(tableau des remises, conditions de port…) sont proposés en lien dans le même
encart, sur la fiche du fournisseur et sur ses fiches dropshipping. Un document
est retenu s'il est joint au fournisseur (pièce jointe de sa fiche) et que sa
description contient « Conditions commerciales » ou que son nom évoque des
remises ou conditions (discount, remise, korting, condition, tarif).

Un commercial est un contact rattaché au fournisseur (SCP Benelux, Fluidra
Benelux…) portant l'étiquette « Commercial fournisseur ». Aucun nouveau champ
en base : l'encart et le bouton sont calculés à l'affichage.
"""
from urllib.parse import quote

from markupsafe import Markup, escape

from odoo import api, fields, models

ETIQUETTE = 'Commercial fournisseur'
MOTS_CONDITIONS = ('Conditions commerciales', 'discount', 'remise', 'korting', 'condition', 'tarif')


def pool_documents_conditions(env, fournisseurs):
    """Pièces jointes « conditions commerciales » des fournisseurs (les plus récentes d'abord)."""
    ids = fournisseurs.mapped('commercial_partner_id').ids
    if not ids:
        return env['ir.attachment']
    domaine = [('res_model', '=', 'res.partner'), ('res_id', 'in', ids)]
    ou = []
    for mot in MOTS_CONDITIONS:
        ou = (['|'] + ou if ou else []) + [('name', 'ilike', mot)]
    ou = ['|', ('description', 'ilike', MOTS_CONDITIONS[0])] + ou
    return env['ir.attachment'].sudo().search(domaine + ou, order='create_date desc')


def pool_documents_html(documents, avec_fournisseur=True):
    if not documents:
        return False
    noms = {}
    if avec_fournisseur:
        partenaires = documents.env['res.partner'].sudo().browse(documents.mapped('res_id'))
        noms = {p.id: p.name for p in partenaires}
    liens = []
    for d in documents:
        lien = Markup('<a href="/web/content/%s?download=true" target="_blank"><i class="fa fa-file-excel-o me-1" '
                      'title="Document"/>%s</a> <span class="text-muted">(%s)</span>') % (
            d.id, d.name, d.create_date.strftime('%d/%m/%Y') if d.create_date else '')
        if avec_fournisseur and noms.get(d.res_id):
            lien = Markup('<strong>%s</strong> — ') % noms[d.res_id] + lien
        liens.append(lien)
    return Markup(' · ').join(liens)


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
        documents = pool_documents_conditions(self.env, self._pool_fournisseurs())
        if not commerciaux and not documents:
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
        lignes = []
        if blocs:
            lignes.append(Markup('<span class="me-1">Commercial :</span>') + Markup('<br/>').join(blocs))
        if documents:
            lignes.append(Markup('<i class="fa fa-percent me-1" title="Conditions"/><span class="me-1">Conditions '
                                 'commerciales :</span>') + pool_documents_html(documents))
        return Markup('<br/>').join(lignes)

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


class ResPartner(models.Model):
    _inherit = 'res.partner'

    pool_conditions_html = fields.Html(string='Conditions commerciales (documents)',
                                       compute='_compute_pool_conditions_html', sanitize=False)

    def _compute_pool_conditions_html(self):
        for p in self:
            p.pool_conditions_html = pool_documents_html(pool_documents_conditions(self.env, p), avec_fournisseur=False) \
                if p.supplier_rank and p.id else False


class SupplierDropshipInfo(models.Model):
    _inherit = 'supplier.dropship.info'

    pool_conditions_html = fields.Html(string='Conditions commerciales (documents)',
                                       compute='_compute_pool_conditions_html', sanitize=False)

    @api.depends('supplier_id')
    def _compute_pool_conditions_html(self):
        for i in self:
            i.pool_conditions_html = pool_documents_html(pool_documents_conditions(self.env, i.supplier_id),
                                                         avec_fournisseur=False) if i.supplier_id else False
