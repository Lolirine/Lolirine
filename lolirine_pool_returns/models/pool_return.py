from datetime import timedelta

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError

P = 'lolirine_pool_returns.'

# motif → (libellé client, type de dossier, frais de renvoi à charge de)
MOTIFS = [
    ('retractation', "Je me rétracte (aucune raison à donner)", 'retractation', 'client'),
    ('plus_besoin', "Je n'en ai plus besoin", 'retractation', 'client'),
    ('erreur_commande', "J'ai commandé par erreur", 'retractation', 'client'),
    ('incompatible', "L'article ne convient pas à mon installation", 'retractation', 'client'),
    ('meilleur_prix', "J'ai trouvé un meilleur prix ailleurs", 'retractation', 'client'),
    ('retard', "La livraison est arrivée trop tard", 'retractation', 'client'),
    ('defectueux', "L'article est défectueux ou ne fonctionne pas", 'defaut', 'lolirine'),
    ('endommage', "L'article ou le colis est arrivé endommagé", 'dommage', 'lolirine'),
    ('manquant', "Il manque des pièces ou des accessoires", 'dommage', 'lolirine'),
    ('mauvais_article', "Ce n'est pas l'article que j'ai commandé", 'erreur', 'lolirine'),
    ('description', "L'article ne correspond pas à sa description", 'erreur', 'lolirine'),
]
MOTIF_SELECTION = [(m[0], m[1]) for m in MOTIFS]
MOTIF_TYPE = {m[0]: m[2] for m in MOTIFS}
MOTIF_FRAIS = {m[0]: m[3] for m in MOTIFS}


class PoolReturn(models.Model):
    _name = 'pool.return'
    _description = 'Retour client'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='N° de retour', required=True, copy=False, readonly=True,
                       default=lambda self: _('Nouveau'), index=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'À examiner'),
        ('approved', 'Accepté – bon émis'),
        ('received', 'Reçu'),
        ('refunded', 'Remboursé'),
        ('refused', 'Refusé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True, copy=False)
    order_id = fields.Many2one('sale.order', string='Commande', required=True, index=True, ondelete='restrict')
    partner_id = fields.Many2one('res.partner', string='Client', required=True, index=True)
    company_id = fields.Many2one(related='order_id.company_id', store=True)
    currency_id = fields.Many2one(related='order_id.currency_id')
    website_id = fields.Many2one(related='order_id.website_id', store=True)
    user_id = fields.Many2one('res.users', string='Responsable', tracking=True,
                              default=lambda self: self.env.user if self.env.user._is_internal() else False)
    motif = fields.Selection(MOTIF_SELECTION, string='Motif', required=True, tracking=True)
    type_retour = fields.Selection([
        ('retractation', 'Rétractation'),
        ('defaut', 'Article défectueux (garantie)'),
        ('dommage', 'Dommage ou manquant à la livraison'),
        ('erreur', 'Erreur de notre part'),
    ], string='Type', compute='_compute_type_retour', store=True)
    frais_renvoi = fields.Selection([('client', 'À charge du client'), ('lolirine', 'À charge de Lolirine')],
                                    string='Frais de renvoi', compute='_compute_type_retour', store=True, readonly=False)
    commentaire = fields.Text(string='Commentaire du client')
    note_interne = fields.Html(string='Note interne')
    line_ids = fields.One2many('pool.return.line', 'return_id', string='Articles', copy=True)
    est_professionnel = fields.Boolean(string='Client professionnel', compute='_compute_eligibilite', store=True)
    date_livraison = fields.Date(string='Livré le', compute='_compute_eligibilite', store=True)
    date_limite = fields.Date(string='Retour possible jusqu\'au', compute='_compute_eligibilite', store=True)
    eligible = fields.Boolean(string='Dans les conditions', compute='_compute_eligibilite', store=True)
    eligibilite_note = fields.Text(string='Analyse des conditions', compute='_compute_eligibilite', store=True)
    sans_renvoi = fields.Boolean(string='Remboursement sans renvoi', tracking=True,
                                 help="Le client n'a pas à renvoyer l'article (faible valeur).")
    adresse_retour = fields.Text(string='Adresse de renvoi')
    montant_articles = fields.Monetary(string='Valeur des articles', compute='_compute_montants', store=True)
    frais_remise_stock = fields.Monetary(string='Frais de remise en stock', compute='_compute_montants', store=True)
    montant_rembourse = fields.Monetary(string='Montant à rembourser', compute='_compute_montants', store=True)
    refund_id = fields.Many2one('account.move', string='Avoir', copy=False, readonly=True)
    fournisseur_id = fields.Many2one('res.partner', string='Fournisseur', compute='_compute_fournisseur', store=True,
                                     readonly=False, help="Fournisseur principal des articles retournés.")
    retour_direct_fournisseur = fields.Boolean(
        string='Renvoi direct au fournisseur possible', compute='_compute_eligibilite', store=True,
        help="Demande assez tôt pour que l'article reparte chez le fournisseur dans son délai de reprise "
             "(SCP : 8 jours après réception, avec autorisation RMA).")
    date_limite_fournisseur = fields.Date(string='Reprise fournisseur jusqu\'au', compute='_compute_eligibilite', store=True)
    rma_fournisseur = fields.Char(string='N° d\'autorisation fournisseur (RMA)', tracking=True, copy=False)
    rma_attachment_ids = fields.Many2many('ir.attachment', 'pool_return_rma_attachment_rel', 'return_id', 'attachment_id',
                                          string='Autorisation du fournisseur (document)',
                                          help="Document RMA reçu du fournisseur : il est joint au mail du client, "
                                               "qui doit le coller sur le colis.")
    date_demande = fields.Datetime(string='Demandé le', readonly=True, copy=False)
    date_reception = fields.Date(string='Reçu le', copy=False, tracking=True)

    # ------------------------------------------------------------------ calculs
    @api.depends('motif')
    def _compute_type_retour(self):
        for rec in self:
            rec.type_retour = MOTIF_TYPE.get(rec.motif)
            rec.frais_renvoi = MOTIF_FRAIS.get(rec.motif, 'client')

    @api.model
    def _param(self, key, default):
        val = self.env['ir.config_parameter'].sudo().get_param(P + key)
        try:
            return type(default)(val) if val not in (None, '', False) else default
        except (TypeError, ValueError):
            return default

    @api.model
    def _date_livraison_commande(self, order):
        """Date de livraison : dernier transfert sortant terminé, sinon date de commande."""
        pickings = order.picking_ids.filtered(lambda p: p.state == 'done' and p.picking_type_code in ('outgoing', 'dropship'))
        if pickings:
            return max(pickings.mapped('date_done')).date()
        return (order.date_order or fields.Datetime.now()).date()

    @api.model
    def _jours_ouvrables(self, depart, nb):
        d = depart
        while nb > 0:
            d += timedelta(days=1)
            if d.weekday() < 5:
                nb -= 1
        return d

    def _regle(self):
        self.ensure_one()
        return self.env['pool.return.regle'].sudo().pour(self.fournisseur_id)

    def _delai_dommage_jours(self):
        """Délai de signalement d'un dommage en jours ouvrables (règle du fournisseur, sinon réglage)."""
        regle = self._regle()
        if regle and regle.delai_dommage_heures:
            return max(1, -(-regle.delai_dommage_heures // 24))
        return self._param('delai_dommage', 2)

    @api.depends('line_ids.product_id')
    def _compute_fournisseur(self):
        for rec in self:
            fournisseurs = rec.line_ids.mapped('product_id.seller_ids').sorted('sequence').mapped('partner_id')
            rec.fournisseur_id = fournisseurs[:1].commercial_partner_id if fournisseurs else False

    @api.depends('order_id', 'partner_id', 'motif', 'line_ids.product_id', 'line_ids.quantite', 'fournisseur_id')
    def _compute_eligibilite(self):
        aujourdhui = fields.Date.context_today(self)
        for rec in self:
            notes = []
            ok = True
            commercial = rec.partner_id.commercial_partner_id
            pro = bool(commercial.is_company or commercial.vat)
            rec.est_professionnel = pro
            if not rec.order_id:
                rec.date_livraison = rec.date_limite = rec.date_limite_fournisseur = False
                rec.retour_direct_fournisseur = False
                rec.eligible = False
                rec.eligibilite_note = False
                continue
            livraison = self._date_livraison_commande(rec.order_id)
            rec.date_livraison = livraison
            regle = rec._regle()
            delai_f = regle.delai_reprise if regle else self._param('delai_fournisseur', 8)
            rec.date_limite_fournisseur = livraison + timedelta(days=delai_f)
            # 2 jours de marge pour obtenir le RMA et faire partir le colis
            rec.retour_direct_fournisseur = bool(
                rec.fournisseur_id and MOTIF_TYPE.get(rec.motif) == 'retractation'
                and aujourdhui <= livraison + timedelta(days=max(delai_f - 2, 0)))
            type_retour = MOTIF_TYPE.get(rec.motif)
            if type_retour == 'retractation':
                delai = self._param('delai_pro', 7) if pro else self._param('delai_retractation', 14)
                limite = livraison + timedelta(days=delai)
                rec.date_limite = limite
                if aujourdhui > limite:
                    ok = False
                    notes.append(_("Délai de %(d)s jours dépassé (livré le %(l)s).", d=delai, l=livraison.strftime('%d/%m/%Y')))
                for line in rec.line_ids:
                    exclu, motif = line.product_id.product_tmpl_id._lolirine_exclu_retractation()
                    if exclu:
                        ok = False
                        notes.append(_("%(p)s : %(m)s, exclu de la rétractation.", p=line.product_id.display_name, m=motif))
                if pro:
                    notes.append(_("Client professionnel : retour commercial, frais de remise en stock de %s %%.",
                                   self._param('frais_pro', 15.0)))
            elif type_retour == 'dommage':
                delai_dom = rec._delai_dommage_jours()
                limite = self._jours_ouvrables(livraison, delai_dom)
                rec.date_limite = limite
                if aujourdhui > limite:
                    notes.append(_("Signalé après le délai de %(d)s jour(s) ouvrable(s) : recours contre le transporteur "
                                   "et le fournisseur (%(f)s) compromis, à examiner.",
                                   d=delai_dom, f=rec.fournisseur_id.name or '-'))
            else:
                rec.date_limite = livraison + timedelta(days=730)
                if aujourdhui > rec.date_limite:
                    ok = False
                    notes.append(_("Garantie légale de 2 ans dépassée."))
            if not rec.line_ids:
                ok = False
                notes.append(_("Aucun article sélectionné."))
            rec.eligible = ok
            rec.eligibilite_note = '\n'.join(notes) or _("Conditions respectées.")

    @api.depends('line_ids.montant', 'est_professionnel', 'type_retour')
    def _compute_montants(self):
        for rec in self:
            total = sum(rec.line_ids.mapped('montant'))
            frais = 0.0
            if rec.est_professionnel and rec.type_retour == 'retractation':
                frais = round(total * self._param('frais_pro', 15.0) / 100.0, 2)
            rec.montant_articles = total
            rec.frais_remise_stock = frais
            rec.montant_rembourse = total - frais

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/my/returns/%s' % rec.id

    def _adresse_par_defaut(self):
        txt = self._param('adresse_retour', '')
        if txt:
            return '\n'.join(x.strip() for x in txt.split(';') if x.strip())
        soc = (self.company_id or self.env.company).partner_id
        return '\n'.join(x for x in [soc.name, soc.street, soc.street2,
                                     ' '.join(y for y in [soc.zip, soc.city] if y), soc.country_id.name] if x)

    # ------------------------------------------------------------------ CRUD
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('pool.return') or _('Nouveau')
        recs = super().create(vals_list)
        for rec in recs:
            if not rec.adresse_retour:
                rec.adresse_retour = rec._adresse_par_defaut()
        return recs

    # ------------------------------------------------------------------ actions
    def action_soumettre(self):
        """Appelée depuis l'espace client une fois la demande complète."""
        for rec in self:
            if rec.state != 'draft':
                continue
            rec.write({'state': 'submitted', 'date_demande': fields.Datetime.now()})
            seuil = self._param('seuil_sans_retour', 15.0)
            if rec.type_retour != 'retractation' and rec.montant_articles <= seuil:
                rec.sans_renvoi = True
            rec.message_post(body=_("Demande de retour envoyée par le client : %(m)s.",
                                    m=dict(MOTIF_SELECTION).get(rec.motif)))
            auto = self._param('auto_accepter', '') == 'True'
            if rec.retour_direct_fournisseur and rec.eligible:
                # Encore dans le délai de reprise du fournisseur : demander d'abord son autorisation,
                # le client renverra alors directement chez lui (bon + RMA).
                rec.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=rec._responsable().id,
                    date_deadline=rec.date_limite_fournisseur - timedelta(days=2),
                    summary=_("Demander l'autorisation de retour (RMA) à %s", rec.fournisseur_id.name),
                    note=_("Rétractation demandée dans le délai de reprise du fournisseur (jusqu'au %s). "
                           "Bouton « Demander le RMA », puis saisir le n° reçu, joindre le document et accepter "
                           "avec l'adresse du fournisseur. Sans réponse à temps : accepter avec l'adresse de Boninne.",
                           rec.date_limite_fournisseur.strftime('%d/%m/%Y')))
            elif auto and rec.type_retour == 'retractation' and rec.eligible and not rec.est_professionnel:
                rec.action_accepter()
            else:
                resume = _("Examiner le retour %s", rec.name)
                if rec.type_retour == 'defaut' and rec.fournisseur_id:
                    resume = _("Retour %(r)s : ouvrir une demande SAV chez %(f)s", r=rec.name, f=rec.fournisseur_id.name)
                rec.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=rec._responsable().id,
                    summary=resume, note=rec.eligibilite_note or '')
        return True

    def _responsable(self):
        """Utilisateur interne qui traite le retour."""
        self.ensure_one()
        order = self.order_id
        for u in (self.user_id, order.user_id, order.website_id.salesperson_id, order.team_id.user_id,
                  self.env.ref('base.user_admin', raise_if_not_found=False)):
            if u and u.id != SUPERUSER_ID and u._is_internal():
                if not self.user_id:
                    self.sudo().user_id = u
                return u
        return self.env['res.users']

    def action_accepter(self):
        template = self.env.ref('lolirine_pool_returns.mail_template_retour_accepte', raise_if_not_found=False)
        for rec in self:
            if rec.state not in ('draft', 'submitted', 'refused'):
                raise UserError(_("Le retour %s ne peut plus être accepté.", rec.name))
            rec.state = 'approved'
            rec.activity_unlink(['mail.mail_activity_data_todo'])
            if template:
                # même chemin que le bouton « Envoyer » d'Odoo : bon de retour PDF du modèle
                # + document d'autorisation du fournisseur (RMA) s'il y en a un
                composer = self.env['mail.compose.message'].with_context(
                    lang=rec.partner_id.lang, default_model='pool.return', default_res_ids=rec.ids,
                    default_template_id=template.id, default_composition_mode='comment',
                    default_message_type='comment', default_subtype_id=self.env.ref('mail.mt_comment').id,
                ).create({})
                if rec.rma_attachment_ids:
                    ids = composer.attachment_ids.ids + rec.rma_attachment_ids.ids
                    composer.attachment_ids = [(6, 0, ids)]
                composer._action_send_mail()
        return True

    def _email_rma(self):
        self.ensure_one()
        regle = self._regle()
        if regle:
            mail = regle.email_rma_sav if self.type_retour == 'defaut' else regle.email_rma_neuf
            if mail:
                return mail
        cle = 'email_rma_sav' if self.type_retour == 'defaut' else 'email_rma_neuf'
        defaut = 'technicalsupport.benelux@scppool.com' if self.type_retour == 'defaut' else 'info.benelux@scppool.com'
        return self._param(cle, defaut)

    def _adresse_fournisseur(self):
        regle = self._regle() if len(self) == 1 else False
        if regle and regle.adresse_retour:
            return regle.adresse_retour
        txt = self._param('adresse_fournisseur', 'SCP Benelux ; Maalbeekweg 21 ; 1930 Zaventem ; Belgique')
        return '\n'.join(x.strip() for x in txt.split(';') if x.strip())

    def action_demander_rma(self):
        """Ouvre un e-mail pré-rempli vers le fournisseur (formulaire de demande de retour)."""
        self.ensure_one()
        template = self.env.ref('lolirine_pool_returns.mail_template_demande_rma')
        return {
            'type': 'ir.actions.act_window', 'res_model': 'mail.compose.message', 'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'pool.return', 'default_res_ids': self.ids,
                'default_template_id': template.id, 'default_composition_mode': 'comment',
                'default_email_layout_xmlid': 'mail.mail_notification_light',
                'force_email': True,
            },
        }

    def action_adresse_fournisseur(self):
        for rec in self:
            rec.adresse_retour = rec._adresse_fournisseur()
        return True

    def action_adresse_boninne(self):
        for rec in self:
            rec.adresse_retour = rec._adresse_par_defaut()
        return True

    def action_refuser(self):
        for rec in self:
            rec.state = 'refused'
            rec.activity_unlink(['mail.mail_activity_data_todo'])
        return True

    def action_recu(self):
        for rec in self:
            rec.write({'state': 'received', 'date_reception': rec.date_reception or fields.Date.context_today(rec)})
        return True

    def action_annuler(self):
        self.write({'state': 'cancel'})
        return True

    def action_remettre_brouillon(self):
        self.write({'state': 'draft'})
        return True

    def action_creer_avoir(self):
        """Crée un avoir BROUILLON : articles retournés (+ frais de livraison initiaux en
        cas de rétractation totale), moins les frais de remise en stock éventuels."""
        self.ensure_one()
        if self.refund_id:
            return self.action_voir_avoir()
        order = self.order_id
        factures = order.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
        lignes = []
        for line in self.line_ids:
            ol = line.order_line_id
            lignes.append((0, 0, {
                'product_id': line.product_id.id,
                'name': ol.name or line.product_id.display_name,
                'quantity': line.quantite,
                'price_unit': ol.price_unit,
                'discount': ol.discount,
                'tax_ids': [(6, 0, ol.tax_ids.ids)],
                'sale_line_ids': [(6, 0, ol.ids)],
            }))
        # rétractation de toute la commande : frais de livraison standard remboursés
        if self.type_retour == 'retractation' and not self.est_professionnel:
            tout = all(
                sum(self.line_ids.filtered(lambda l, ol=ol: l.order_line_id == ol).mapped('quantite')) >= ol.qty_delivered
                for ol in order.order_line.filtered(lambda l: not l.is_delivery and not l.display_type
                                                     and l.product_id.type != 'service'))
            if tout:
                for dl in order.order_line.filtered('is_delivery'):
                    lignes.append((0, 0, {
                        'product_id': dl.product_id.id, 'name': dl.name, 'quantity': dl.product_uom_qty,
                        'price_unit': dl.price_unit, 'tax_ids': [(6, 0, dl.tax_ids.ids)],
                        'sale_line_ids': [(6, 0, dl.ids)],
                    }))
        if self.frais_remise_stock:
            taxes = self.line_ids[:1].order_line_id.tax_ids
            taux = sum(t.amount for t in taxes if t.amount_type == 'percent' and not t.price_include)
            lignes.append((0, 0, {
                'name': _("Frais de remise en stock (%s %%)", self._param('frais_pro', 15.0)),
                'quantity': 1,
                'price_unit': -round(self.frais_remise_stock / (1 + taux / 100.0), 2),
                'tax_ids': [(6, 0, taxes.ids)],
            }))
        move = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': order.partner_invoice_id.id or order.partner_id.id,
            'invoice_origin': '%s / %s' % (order.name, self.name),
            'ref': _("Retour %s", self.name),
            'reversed_entry_id': factures[:1].id or False,
            'currency_id': order.currency_id.id,
            'company_id': order.company_id.id,
            'invoice_line_ids': lignes,
        })
        self.refund_id = move
        self.message_post(body=_("Avoir brouillon %s créé.", move._get_move_display_name()))
        return self.action_voir_avoir()

    def action_voir_avoir(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'account.move',
            'res_id': self.refund_id.id, 'view_mode': 'form', 'target': 'current',
        }

    def action_marquer_rembourse(self):
        self.write({'state': 'refunded'})
        return True

    def action_imprimer_bon(self):
        return self.env.ref('lolirine_pool_returns.action_report_pool_return').report_action(self)

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Bon de retour %s' % self.name

    @api.model
    def lpr_motifs(self):
        return MOTIFS


class PoolReturnLine(models.Model):
    _name = 'pool.return.line'
    _description = 'Article retourné'

    return_id = fields.Many2one('pool.return', required=True, ondelete='cascade', index=True)
    order_line_id = fields.Many2one('sale.order.line', string='Ligne de commande', required=True)
    product_id = fields.Many2one(related='order_line_id.product_id', store=True, string='Article')
    quantite = fields.Float(string='Quantité', required=True, default=1.0)
    currency_id = fields.Many2one(related='return_id.currency_id')
    prix_unitaire = fields.Monetary(string='Prix unitaire TVAC', compute='_compute_montant', store=True)
    montant = fields.Monetary(string='Montant TVAC', compute='_compute_montant', store=True)
    exclu = fields.Boolean(string='Exclu de la rétractation', compute='_compute_exclu')

    @api.depends('order_line_id.price_total', 'order_line_id.product_uom_qty', 'quantite')
    def _compute_montant(self):
        for line in self:
            ol = line.order_line_id
            pu = ol.price_total / ol.product_uom_qty if ol.product_uom_qty else 0.0
            line.prix_unitaire = pu
            line.montant = pu * line.quantite

    @api.depends('product_id')
    def _compute_exclu(self):
        for line in self:
            line.exclu = bool(line.product_id) and line.product_id.product_tmpl_id._lolirine_exclu_retractation()[0]
