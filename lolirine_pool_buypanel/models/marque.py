"""Habillage « Lolirine Pool Store » des e-mails et PDF des commandes du site Pool Store.

La société Odoo (Srl Lolirine) est partagée avec le garde-meuble : sans ce module,
les e-mails et documents du Pool Store portent le logo, les couleurs, l'adresse
e-mail et le site du garde-meuble.

Règle : un document est « Pool Store » quand il vient du site web Pool Store
(commande du site, facture ou livraison de cette commande, transaction de
paiement, carte de fidélité de son programme), OU d'un devis / d'une commande
piscine fait dans Odoo (case « Devis piscine » de lolirine_pool_sale, ou
commande dropship de lolirine_pool_dropship), avec sa facture et sa livraison.

Ce qui change pour ces documents :
  * e-mails : logo Pool Store en tête, pied de page Pool Store (nom, téléphone,
    e-mail, site), boutons aux couleurs du Pool Store ;
  * modèles d'e-mail : la version « Pool Store » de chaque modèle est utilisée
    (correspondance enregistrée dans le paramètre
    lolirine_pool_buypanel.modeles_pool_store, ex. « 12:701,13:702 ») ;
  * PDF (devis, commande, facture, bon de livraison) : logo et pied de page
    Pool Store ; la raison sociale, l'adresse légale et la TVA restent celles de
    Srl Lolirine (mentions légales obligatoires).
  * factures : journal « Ventes Piscines » (numérotation propre au Pool Store).
Le garde-meuble n'est pas concerné.
"""
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

P = 'lolirine_pool_buypanel.'
SITE_POOL_STORE = 6

MARQUE = {
    'name': 'Lolirine Pool Store',
    'phone': '+32 497 44 41 46',
    'email': 'info@lolirinepoolstore.be',
    'website': 'https://www.lolirinepoolstore.be',
    'email_primary_color': '#FFFFFF',     # texte des boutons
    'email_secondary_color': '#0369a1',   # fond des boutons, lien « Odoo »
    'uses_default_logo': False,
}


class SocieteMarque:
    """Société « vue par le client » du Pool Store, pour les gabarits d'e-mail.

    Remplace quelques valeurs (nom, coordonnées, couleurs) et renvoie tout le
    reste à la vraie société (id, devise, adresse...).
    """

    def __init__(self, societe, valeurs):
        self._societe = societe
        self._valeurs = valeurs

    def __getattr__(self, nom):
        valeurs = self.__dict__.get('_valeurs') or {}
        if nom in valeurs:
            return valeurs[nom]
        return getattr(self.__dict__['_societe'], nom)

    def __bool__(self):
        return True

    @property
    def email_formatted(self):
        return '"%s" <%s>' % (self._valeurs['name'], self._valeurs['email'])

    def __repr__(self):
        return 'SocieteMarque(%r)' % (self._valeurs.get('name'),)


def _valeurs_marque(site):
    base = site.domain or 'https://www.lolirinepoolstore.be'
    if not base.startswith(('http://', 'https://')):
        base = 'https://' + base
    base = base.rstrip('/')
    valeurs = dict(MARQUE, website=base)
    return valeurs, '%s/web/image/website/%s/logo/300x100' % (base, site.id)


class Base(models.AbstractModel):
    _inherit = 'base'

    def _lp_site_pool_store(self):
        """Site web Pool Store (sudo) si cet enregistrement en dépend, sinon vide."""
        Site = self.env['website'].sudo()
        if len(self) != 1 or not self.id:
            return Site
        try:
            rec = self.sudo()
            site = Site
            if self._name == 'loyalty.card' and 'website_id' in rec.program_id._fields:
                site = rec.program_id.website_id
            elif self._name == 'payment.transaction' and 'sale_order_ids' in rec._fields:
                site = rec.sale_order_ids.website_id[:1]
            elif self._name in ('sale.order', 'account.move', 'stock.picking', 'loyalty.program') \
                    and 'website_id' in rec._fields:
                site = rec.website_id
                if not site and self._name == 'account.move':
                    site = rec.line_ids.sale_line_ids.order_id.website_id[:1]
                if not site and self._name == 'stock.picking' and 'sale_id' in rec._fields:
                    site = rec.sale_id.website_id
            if site and site.id == SITE_POOL_STORE:
                return site
            # Devis / commandes piscine faits dans Odoo (sans site web) :
            # case « Devis piscine » (lolirine_pool_sale) ou commande dropship (lolirine_pool_dropship)
            commandes = self.env['sale.order'].sudo()
            if self._name == 'sale.order':
                commandes = rec
            elif self._name == 'account.move':
                commandes = rec.line_ids.sale_line_ids.order_id
            elif self._name == 'stock.picking' and 'sale_id' in rec._fields:
                commandes = rec.sale_id
            elif self._name == 'payment.transaction' and 'sale_order_ids' in rec._fields:
                commandes = rec.sale_order_ids
            if commandes and any(
                    ('is_pool_quote' in c._fields and c.is_pool_quote)
                    or ('is_dropship_order' in c._fields and c.is_dropship_order)
                    for c in commandes):
                return Site.browse(SITE_POOL_STORE).exists()
            return Site
        except Exception:  # l'habillage ne doit jamais bloquer un envoi ou un PDF
            _logger.exception("Pool Store : détection du site impossible pour %s", self)
            return Site

    def _lp_modele_pool_store(self, modele):
        """Version « Pool Store » du modèle d'e-mail, si ce document est Pool Store."""
        if not modele or not self._lp_site_pool_store():
            return modele
        brut = self.env['ir.config_parameter'].sudo().get_param(P + 'modeles_pool_store') or ''
        correspondances = {}
        for paire in brut.split(','):
            if ':' in paire:
                a, b = paire.split(':', 1)
                if a.strip().isdigit() and b.strip().isdigit():
                    correspondances[int(a)] = int(b)
        cible = correspondances.get(modele.id)
        if cible:
            remplacant = self.env['mail.template'].browse(cible).exists()
            if remplacant:
                return remplacant
        return modele

    def _lp_contexte_marque(self, societe):
        """(société habillée, url du logo) si ce document est Pool Store, sinon (société, False)."""
        site = self._lp_site_pool_store()
        if not site or isinstance(societe, SocieteMarque):
            return societe, False
        valeurs, logo = _valeurs_marque(site)
        return SocieteMarque(societe, valeurs), logo


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals=False, model_description=False,
                                                   force_email_company=False, force_email_lang=False,
                                                   force_record_name=False):
        ctx = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals=msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang,
            force_record_name=force_record_name,
        )
        if len(self) == 1:
            societe, logo = self._lp_contexte_marque(ctx.get('company'))
            if logo:
                ctx['company'] = societe
                ctx['website_url'] = societe.website
                ctx['lp_logo'] = logo
        return ctx


class MailRenderMixin(models.AbstractModel):
    _inherit = 'mail.render.mixin'

    @api.model
    def _render_encapsulate(self, layout_xmlid, html, add_context=None, context_record=None):
        if context_record and len(context_record) == 1 and context_record._lp_site_pool_store():
            add_context = dict(add_context or {})
            societe = add_context.get('company') or \
                context_record._mail_get_companies(default=self.env.company)[context_record.id]
            societe, logo = context_record._lp_contexte_marque(societe)
            if logo:
                add_context.update({'company': societe, 'lp_logo': logo, 'website_url': societe.website})
        return super()._render_encapsulate(layout_xmlid, html, add_context=add_context,
                                           context_record=context_record)


class SaleOrderMarque(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        """Factures des commandes du site Pool Store dans le journal « Ventes Piscines »
        (numérotation distincte de celle du garde-meuble), sauf journal choisi sur la commande.
        Paramètre lolirine_pool_buypanel.journal_ventes_id (défaut 17)."""
        valeurs = super()._prepare_invoice()
        if not self.journal_id and self._lp_site_pool_store():
            jid = int(self.env['ir.config_parameter'].sudo().get_param(P + 'journal_ventes_id', 17) or 0)
            journal = self.env['account.journal'].sudo().browse(jid).exists()
            if journal and journal.type == 'sale' and journal.company_id == self.company_id:
                valeurs['journal_id'] = journal.id
        return valeurs

    def _find_mail_template(self):
        return self._lp_modele_pool_store(super()._find_mail_template())

    def _send_order_notification_mail(self, mail_template, allow_deferred_sending=True):
        return super()._send_order_notification_mail(
            self._lp_modele_pool_store(mail_template), allow_deferred_sending=allow_deferred_sending)


class AccountMoveMarque(models.Model):
    _inherit = 'account.move'

    def _get_mail_template(self):
        modele = super()._get_mail_template()
        if len(self) == 1:
            return self._lp_modele_pool_store(modele)
        return modele
