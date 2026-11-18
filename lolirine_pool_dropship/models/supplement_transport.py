# -*- coding: utf-8 -*-
"""Supplément transport fournisseur ajouté à la livraison du panier.

1. Ancienne règle (conservée pour les fournisseurs sans barème) : Fluidra facture un
   transport (95 € HT) pour les colis lourds ; quand le panier contient un article
   marqué « Supplément transport », le montant fixe du mode de livraison est ajouté.

2. Règle de marge minimale (18/11/2026) : chaque fournisseur peut porter un barème de
   frais de port (Fluidra, SCP, Allforpools). Le panier est découpé par fournisseur
   principal ; pour chaque groupe, on estime ce que coûtera réellement l'envoi direct
   au client (port + suppléments) et, si la vente du groupe (articles + part de la
   livraison facturée) ne laisse pas la marge minimale du fournisseur (20 % par
   défaut), la différence est ajoutée aux frais de livraison du panier.
"""
from odoo import _, api, fields, models

BAREMES = [
    ('fluidra', 'Fluidra Benelux 2026'),
    ('scp', 'SCP Benelux 2026'),
    ('afp', 'Allforpools (bpost 24h)'),
]

# SCP Benelux 2026 (BE) : forfait par tranche de marchandises HT, franco dès 1200 €
SCP_TRANCHES = [(200, 7.50), (400, 12.0), (600, 15.0), (800, 20.0), (1000, 25.0), (1200, 35.0)]


class ProductTemplateSupplementTransport(models.Model):
    _inherit = 'product.template'

    pool_supplement_transport = fields.Boolean(
        "Supplément transport", help="Colis lourd livré par le transporteur du fournisseur : le supplément "
                                     "transport du mode de livraison est ajouté au panier qui contient cet article.")
    pool_adr = fields.Boolean(
        "Marchandise dangereuse (ADR)",
        help="Article marqué « LQ ADR » au catalogue fournisseur : supplément matières dangereuses "
             "facturé par le fournisseur (Fluidra : 35 € HT par envoi).")


class ResPartnerBaremePort(models.Model):
    _inherit = 'res.partner'

    pool_bareme_port = fields.Selection(
        BAREMES, string="Barème de port (dropship)",
        help="Barème utilisé pour estimer le coût réel d'un envoi direct au client et garantir la marge "
             "minimale sur les petites commandes.")
    pool_marge_min_livraison = fields.Float(
        "Marge minimale port compris (%)", default=20.0,
        help="Marge minimale visée sur la part de la commande servie par ce fournisseur, frais de port inclus.")


class DeliveryCarrierSupplementTransport(models.Model):
    _inherit = 'delivery.carrier'

    pool_supplement_transport = fields.Monetary(
        "Supplément transport (HT)", currency_field='currency_id', default=0.0,
        help="Ajouté une fois par commande quand le panier contient un article marqué « Supplément transport » "
             "(part du transport fournisseur supportée par le client), même si la livraison est offerte.")
    pool_marge_min_active = fields.Boolean(
        "Garantir la marge minimale (frais fournisseur)", default=True,
        help="Ajoute aux frais de livraison le complément nécessaire pour que chaque fournisseur du panier "
             "garde sa marge minimale une fois ses frais de port d'envoi direct payés.")
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    # ------------------------------------------------------------------
    # Estimation du coût fournisseur
    # ------------------------------------------------------------------
    @api.model
    def _pool_frais_fournisseur(self, bareme, net, lines):
        """Coût HT estimé d'un envoi direct au client pour un groupe d'articles."""
        tmpls = lines.mapped('product_id.product_tmpl_id')
        if bareme == 'fluidra':
            if net < 150:
                frais = 30.0
            elif net < 500:
                frais = 18.75
            else:
                frais = 0.0
            frais += 50.0                                   # adresse différente (dropship)
            if any(tmpls.mapped('pool_adr')):
                frais += 35.0                               # matières dangereuses
            if any(tmpls.mapped('pool_supplement_transport')):
                frais += 95.0                               # supplément poids
            return frais
        if bareme == 'scp':
            frais = 0.0
            for seuil, montant in SCP_TRANCHES:
                if net < seuil:
                    frais = montant
                    break
            return frais + 17.0 + 20.0                      # adresse privée + gestion
        if bareme == 'afp':
            return 18.0                                     # bpost Domestic 24h Pro
        return 0.0

    @api.model
    def _pool_fournisseur_principal(self, product):
        seller = product.seller_ids.filtered(
            lambda s: not s.product_id or s.product_id == product)[:1]
        return seller.partner_id.commercial_partner_id if seller else self.env['res.partner']

    def _pool_complement_marge(self, order, prix_livraison):
        """Complément HT à ajouter à la livraison pour garantir la marge de chaque fournisseur."""
        lignes = order.order_line.filtered(
            lambda l: not l.is_delivery and not l.display_type and l.product_id
            and l.product_id.type != 'service' and l.product_uom_qty > 0)
        if not lignes:
            return 0.0, []
        groupes = {}
        for line in lignes:
            partner = self._pool_fournisseur_principal(line.product_id)
            groupes.setdefault(partner, self.env['sale.order.line'])
            groupes[partner] |= line
        vente_totale = sum(lignes.mapped('price_subtotal')) or 1.0
        complement, details = 0.0, []
        for partner, lines in groupes.items():
            bareme = partner.pool_bareme_port if partner else False
            if not bareme:
                continue
            cout = sum(l.product_id.standard_price * l.product_uom_qty for l in lines)
            vente = sum(lines.mapped('price_subtotal'))
            part_livraison = prix_livraison * vente / vente_totale
            frais = self._pool_frais_fournisseur(bareme, cout, lines)
            marge = min(max(partner.pool_marge_min_livraison or 20.0, 0.0), 90.0) / 100.0
            requis = (cout + frais) / (1.0 - marge)
            manque = order.currency_id.round(requis - vente - part_livraison)
            if manque > 0:
                complement += manque
                details.append((partner.name, manque))
        return complement, details

    def rate_shipment(self, order):
        res = super().rate_shipment(order)
        if not res.get('success') or not order:
            return res
        notes = []
        # Règle de marge minimale par fournisseur
        fournisseurs_bareme = set()
        if self.pool_marge_min_active:
            prix = res.get('price') or 0.0
            complement, details = self._pool_complement_marge(order, prix)
            fournisseurs_bareme = {
                self._pool_fournisseur_principal(l.product_id)
                for l in order.order_line if l.product_id and not l.is_delivery
            }
            fournisseurs_bareme = {p for p in fournisseurs_bareme if p and p.pool_bareme_port}
            if complement > 0:
                res['price'] = prix + complement
                if 'carrier_price' in res:
                    res['carrier_price'] = (res.get('carrier_price') or 0.0) + complement
                notes.append(_("Comprend %s HT de frais d'expédition fournisseur (petite commande).") % (
                    ('%.2f €' % complement).replace('.', ',')))
        # Ancienne règle colis lourd, seulement pour les articles sans barème fournisseur
        if self.pool_supplement_transport:
            lourds = order.order_line.filtered(
                lambda l: not l.is_delivery and l.product_id.product_tmpl_id.pool_supplement_transport
                and self._pool_fournisseur_principal(l.product_id) not in fournisseurs_bareme)
            if lourds:
                supplement = order.currency_id.round(self.pool_supplement_transport)
                res['price'] = (res.get('price') or 0.0) + supplement
                if 'carrier_price' in res:
                    res['carrier_price'] = (res.get('carrier_price') or 0.0) + supplement
                notes.append(_("Comprend un supplément transport de %s HT pour colis lourd.") % (
                    ('%.2f €' % supplement).replace('.', ',')))
        if notes:
            res['warning_message'] = ((res.get('warning_message') or '') + ' ' + ' '.join(notes)).strip()
        return res
