import pytz
from dateutil.relativedelta import relativedelta

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    pool_return_ids = fields.One2many('pool.return', 'order_id', string='Retours')
    pool_return_count = fields.Integer(compute='_compute_pool_return_count', string='Nb retours')

    def _compute_pool_return_count(self):
        for order in self:
            order.pool_return_count = len(order.pool_return_ids)

    def action_voir_retours(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('lolirine_pool_returns.action_pool_return')
        action['domain'] = [('order_id', '=', self.id)]
        action['context'] = {'default_order_id': self.id, 'default_partner_id': self.partner_id.id}
        return action

    def _lpr_lignes_retournables(self):
        """[(ligne, quantité encore retournable)] — articles livrés, hors services et port,
        moins ce qui figure déjà dans un retour non annulé/refusé."""
        self.ensure_one()
        deja = {}
        for ret in self.pool_return_ids.filtered(lambda r: r.state not in ('cancel', 'refused', 'draft')):
            for l in ret.line_ids:
                deja[l.order_line_id.id] = deja.get(l.order_line_id.id, 0.0) + l.quantite
        res = []
        for line in self.order_line:
            if line.display_type or line.is_delivery or not line.product_id or line.product_id.type == 'service':
                continue
            base = line.qty_delivered or 0.0
            reste = base - deja.get(line.id, 0.0)
            if reste > 0:
                res.append((line, reste))
        return res

    # ------------------------------------------------------------------ suivi façon Amazon
    def _lpr_suivi_actif(self):
        """Vue de suivi réservée aux commandes confirmées du Pool Store (site 6 par défaut)."""
        self.ensure_one()
        site = self.env['pool.return'].sudo()._param('website_id', 6)
        return self.state == 'sale' and self.sudo().website_id.id == site
    def _lpr_pickings_client(self):
        """Transferts vers le client (entrepôt ou dropshipping), hors retours et annulés."""
        self.ensure_one()
        return self.picking_ids.filtered(
            lambda p: p.picking_type_code in ('outgoing', 'dropship') and p.state != 'cancel'
            and not getattr(p, 'return_id', False))

    def _lpr_date_estimee(self):
        """(date min, date max) de livraison estimée à partir de la date de commande, ou None."""
        self.ensure_one()
        if self.commitment_date:
            d = fields.Datetime.context_timestamp(self, self.commitment_date).date()
            return d, d
        Liv = self.env.get('lolirine.livraison')
        if Liv is None or not self.date_order:
            return None
        Liv = Liv.sudo()
        produits = self.order_line.filtered(
            lambda l: l.product_id and not l.display_type and not l.is_delivery
            and l.product_id.type != 'service').mapped('product_id.product_tmpl_id')
        if not produits:
            return None
        delai = max(Liv.delai_fournisseur(t) for t in produits)
        tz = pytz.timezone('Europe/Brussels')
        depuis = pytz.utc.localize(self.date_order).astimezone(tz)
        p = Liv.promesse(delai, maintenant=depuis)
        return p['min'], p['max']

    def _lpr_suivi(self):
        """Données de la vue « Suivi de commande » de l'espace client."""
        self.ensure_one()
        order = self.sudo()
        tz_date = lambda dt: dt and fields.Datetime.context_timestamp(order, dt).date()
        pickings = order._lpr_pickings_client()
        faits = pickings.filtered(lambda p: p.state == 'done')
        avec_suivi = pickings.filtered(lambda p: getattr(p, 'carrier_tracking_ref', False))
        achats_ok = False
        if hasattr(order, '_get_purchase_orders'):
            achats_ok = order._get_purchase_orders().filtered(lambda po: po.state in ('purchase', 'done'))

        livree = bool(pickings) and all(p.state == 'done' for p in pickings)
        expediee = livree or bool(avec_suivi) or bool(faits)
        en_preparation = expediee or bool(achats_ok) or any(p.state == 'assigned' for p in pickings)
        paye = order.state == 'sale'

        d_prep = False
        if achats_ok:
            dates = [d for d in achats_ok.mapped('date_approve') if d]
            d_prep = tz_date(min(dates)) if dates else False
        d_exp = tz_date(min(faits.mapped('date_done'))) if faits else False
        d_liv = tz_date(max(faits.mapped('date_done'))) if livree else False

        etapes = [
            {'code': 'commande', 'nom': "Commande passée", 'icone': 'fa-shopping-cart', 'fait': True,
             'date': tz_date(order.date_order)},
            {'code': 'confirmee', 'nom': "Paiement confirmé", 'icone': 'fa-check', 'fait': paye, 'date': False},
            {'code': 'preparation', 'nom': "En préparation", 'icone': 'fa-cube', 'fait': en_preparation,
             'date': d_prep},
            {'code': 'expediee', 'nom': "Expédiée", 'icone': 'fa-truck', 'fait': expediee,
             'date': d_exp if not livree or len(faits) > 1 else False},
            {'code': 'livree', 'nom': "Livrée", 'icone': 'fa-home', 'fait': livree, 'date': d_liv},
        ]
        pos = max(i for i, e in enumerate(etapes) if e['fait'])
        for i, e in enumerate(etapes):
            e['actuelle'] = i == pos

        statut = {
            'commande': "Commande reçue",
            'confirmee': "Commande confirmée",
            'preparation': "En préparation chez notre fournisseur",
            'expediee': "En route",
            'livree': "Livrée",
        }[etapes[pos]['code']]

        estimee = None if livree else order._lpr_date_estimee()
        en_retard = bool(estimee and estimee[1] < fields.Date.context_today(order))

        colis = []
        for p in pickings:
            ref = getattr(p, 'carrier_tracking_ref', False)
            url = False
            if ref and 'carrier_tracking_url' in p._fields:
                url = p.carrier_tracking_url
            colis.append({
                'nom': p.name, 'transporteur': p.carrier_id.name if 'carrier_id' in p._fields else False,
                'ref': ref, 'url': url, 'livre': p.state == 'done', 'date': tz_date(p.date_done),
            })

        retournables = {l.id for l, _r in order._lpr_lignes_retournables()}
        mois = self.env['pool.return'].sudo()._param('garantie_mois', 24)
        livraison = self.env['pool.return'].sudo()._date_livraison_commande(order) if faits else False
        lignes = []
        for line in order.order_line:
            if line.display_type or line.is_delivery or not line.product_id or line.combo_item_id:
                continue
            service = line.product_id.type == 'service'
            if line.qty_delivered >= line.product_uom_qty and line.product_uom_qty:
                etat = "Livré"
            elif line.qty_delivered:
                etat = "Livré en partie (%g sur %g)" % (line.qty_delivered, line.product_uom_qty)
            else:
                etat = statut if not livree else "Livré"
            lignes.append({
                'line': line,
                'etat': False if service else etat,
                'garantie': (livraison + relativedelta(months=mois)) if (livraison and line.qty_delivered
                                                                        and not service) else False,
                'racheter': line._is_reorder_allowed() if hasattr(line, '_is_reorder_allowed') else False,
                'probleme': line.id in retournables,
            })
        return {
            'etapes': etapes, 'statut': statut, 'livree': livree, 'estimee': estimee, 'en_retard': en_retard,
            'colis': colis, 'lignes': lignes,
        }
