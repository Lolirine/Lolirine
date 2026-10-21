from datetime import timedelta

from odoo import _, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal

from ..models.pool_return import MOTIFS

TAILLE_MAX_PHOTO = 8 * 1024 * 1024
MAX_PHOTOS = 6


class PoolReturnPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'pool_return_count' in counters:
            Ret = request.env['pool.return']
            values['pool_return_count'] = Ret.search_count(self._lpr_domaine()) if Ret.has_access('read') else 0
        return values

    def _lpr_domaine(self):
        partner = request.env.user.partner_id
        return [('partner_id', 'child_of', [partner.commercial_partner_id.id]), ('state', '!=', 'draft')]

    # ---------------------------------------------------------------- liste
    @http.route(['/my/returns'], type='http', auth='user', website=True)
    def portal_my_returns(self, **kw):
        retours = request.env['pool.return'].search(self._lpr_domaine())
        values = self._prepare_portal_layout_values()
        values.update({'retours': retours, 'page_name': 'pool_returns', 'default_url': '/my/returns'})
        return request.render('lolirine_pool_returns.portal_my_returns', values)

    # ---------------------------------------------------------------- détail
    @http.route(['/my/returns/<int:return_id>'], type='http', auth='public', website=True)
    def portal_my_return(self, return_id, access_token=None, message=None, **kw):
        try:
            retour = self._document_check_access('pool.return', return_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = self._prepare_portal_layout_values()
        values.update({'retour': retour, 'page_name': 'pool_return', 'message': message,
                       'token': access_token or retour.sudo()._portal_ensure_token()})
        return request.render('lolirine_pool_returns.portal_my_return', values)

    @http.route(['/my/returns/<int:return_id>/bon'], type='http', auth='public', website=True)
    def portal_my_return_bon(self, return_id, access_token=None, download=False, **kw):
        try:
            retour = self._document_check_access('pool.return', return_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if retour.state in ('draft', 'submitted', 'refused', 'cancel'):
            return request.redirect(retour.get_portal_url())
        return self._show_report(model=retour, report_type='pdf',
                                 report_ref='lolirine_pool_returns.action_report_pool_return',
                                 download=bool(download))

    # ---------------------------------------------------------------- demande
    def _lpr_commande(self, order_id, access_token):
        order = self._document_check_access('sale.order', order_id, access_token)
        if order.state != 'sale':
            raise MissingError(_("Commande non confirmée."))
        return order

    def _lpr_valeurs_formulaire(self, order, erreurs=None, saisie=None):
        Ret = request.env['pool.return'].sudo()
        livraison = Ret._date_livraison_commande(order)
        lignes = []
        for line, reste in order.sudo()._lpr_lignes_retournables():
            exclu, motif_exclu = line.product_id.product_tmpl_id._lolirine_exclu_retractation()
            lignes.append({'line': line, 'reste': reste, 'exclu': exclu, 'motif_exclu': motif_exclu})
        commercial = order.partner_id.commercial_partner_id
        pro = bool(commercial.is_company or commercial.vat)
        delai = Ret._param('delai_pro', 7) if pro else Ret._param('delai_retractation', 14)
        return {
            'order': order, 'lignes': lignes, 'motifs': MOTIFS, 'erreurs': erreurs or [],
            'saisie': saisie or {}, 'page_name': 'pool_return_new', 'livraison': livraison,
            'limite_retractation': livraison + timedelta(days=delai), 'est_pro': pro,
            'lien_cgv': Ret._param('lien_cgv', '/terms'),
            'delai_dommage_txt': self._lpr_delai_dommage_txt(order),
            'retours_existants': order.sudo().pool_return_ids.filtered(lambda r: r.state != 'draft'),
        }

    def _lpr_delai_dommage_txt(self, order):
        """Délai le plus court parmi les fournisseurs des articles (Fluidra : 24 h, SCP : 48 h)."""
        Regle = request.env['pool.return.regle'].sudo()
        heures = []
        for partner in order.sudo().order_line.mapped('product_id.seller_ids.partner_id'):
            regle = Regle.pour(partner)
            if regle and regle.delai_dommage_heures:
                heures.append(regle.delai_dommage_heures)
        h = min(heures) if heures else 24 * request.env['pool.return'].sudo()._param('delai_dommage', 2)
        return 'dans les %d heures' % h if h <= 72 else 'dans les %d jours' % (h // 24)

    @http.route(['/my/orders/<int:order_id>/retour'], type='http', auth='public', website=True, methods=['GET'])
    def portal_return_form(self, order_id, access_token=None, **kw):
        try:
            order = self._lpr_commande(order_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        saisie = {}
        # « Problème avec cet article » depuis la page de la commande : article et motif présélectionnés
        ligne = kw.get('ligne')
        if ligne and ligne.isdigit():
            saisie = {'sel_%s' % ligne: '1', 'motif': 'defectueux'}
        values = self._prepare_portal_layout_values()
        values.update(self._lpr_valeurs_formulaire(order, saisie=saisie))
        values['access_token'] = access_token
        return request.render('lolirine_pool_returns.portal_return_form', values)

    @http.route(['/my/orders/<int:order_id>/retour'], type='http', auth='public', website=True, methods=['POST'])
    def portal_return_submit(self, order_id, access_token=None, **post):
        try:
            order = self._lpr_commande(order_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        motifs_valides = {m[0] for m in MOTIFS}
        motif = post.get('motif')
        erreurs = []
        if motif not in motifs_valides:
            erreurs.append(_("Choisissez le motif du retour."))
        retournables = {line.id: reste for line, reste in order.sudo()._lpr_lignes_retournables()}
        lignes = []
        for key, val in post.items():
            if not key.startswith('qty_'):
                continue
            try:
                line_id, qty = int(key[4:]), float(val or 0)
            except ValueError:
                continue
            if qty <= 0 or not post.get('sel_%s' % line_id):
                continue
            if line_id not in retournables:
                continue
            lignes.append((0, 0, {'order_line_id': line_id, 'quantite': min(qty, retournables[line_id])}))
        if not lignes:
            erreurs.append(_("Cochez au moins un article et indiquez la quantité."))
        commentaire = (post.get('commentaire') or '').strip()[:2000]
        if motif in ('defectueux', 'endommage', 'manquant', 'description') and len(commentaire) < 10:
            erreurs.append(_("Décrivez le problème en quelques mots : cela nous permet de vous répondre plus vite."))
        photos = [f for f in request.httprequest.files.getlist('photos') if f and f.filename][:MAX_PHOTOS]
        if motif == 'endommage' and not photos:
            erreurs.append(_("Ajoutez au moins une photo du colis ou de l'article endommagé."))
        if erreurs:
            values = self._prepare_portal_layout_values()
            values.update(self._lpr_valeurs_formulaire(order, erreurs=erreurs, saisie=post))
            values['access_token'] = access_token
            return request.render('lolirine_pool_returns.portal_return_form', values)

        retour = request.env['pool.return'].sudo().create({
            'order_id': order.id,
            'partner_id': order.partner_id.id,
            'motif': motif,
            'commentaire': commentaire,
            'line_ids': lignes,
            'user_id': order.user_id.id or False,
        })
        attachments = request.env['ir.attachment'].sudo()
        for f in photos:
            data = f.read()
            if not data or len(data) > TAILLE_MAX_PHOTO:
                continue
            attachments |= attachments.create({
                'name': f.filename, 'raw': data, 'res_model': 'pool.return', 'res_id': retour.id,
                'mimetype': f.mimetype,
            })
        if attachments:
            attachments.generate_access_token()
        if attachments or commentaire:
            retour.message_post(body=commentaire or _("Photos jointes par le client."),
                                attachment_ids=attachments.ids,
                                author_id=order.partner_id.id, message_type='comment',
                                subtype_xmlid='mail.mt_comment')
        retour.action_soumettre()
        return request.redirect(retour.get_portal_url(query_string='&message=cree'))

    # ---------------------------------------------------------------- acheter à nouveau
    @http.route(['/my/orders/<int:order_id>/racheter'], type='http', auth='public', website=True,
                methods=['POST'])
    def portal_order_racheter(self, order_id, line_id=None, access_token=None, **kw):
        """Ajoute un article d'une commande passée au panier, puis ouvre le panier."""
        try:
            order = self._document_check_access('sale.order', order_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        try:
            line = order.sudo().order_line.filtered(lambda l: l.id == int(line_id or 0))
        except ValueError:
            line = None
        if not line or not line.with_user(request.env.user).sudo()._is_reorder_allowed():
            return request.redirect(order.get_portal_url())
        cart = request.cart or request.website._create_cart()
        cart.with_context(skip_cart_verification=True)._cart_add(
            product_id=line.product_id.id, quantity=1,
            no_variant_attribute_value_ids=line.product_no_variant_attribute_value_ids.ids)
        return request.redirect('/shop/cart')
