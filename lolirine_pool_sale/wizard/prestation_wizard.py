# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.pool_prestation import CATEGORIES, calcul_prix

SECTION_MO = "Main-d'œuvre et déplacements"
SECTION_OPTIONS = "Options proposées"


def _fin_de_bloc(ordre, section):
    """Index juste après la dernière ligne de la section (avant la section suivante)."""
    i = ordre.index(section) + 1
    while i < len(ordre) and ordre[i].display_type != 'line_section':
        i += 1
    return i


def _renumeroter(ordre):
    for n, ligne in enumerate(ordre, start=1):
        if ligne.sequence != n * 10:
            ligne.sequence = n * 10


class PoolPrestationWizard(models.TransientModel):
    _name = 'lolirine.pool.prestation.wizard'
    _description = "Ajouter une prestation (ou un ouvrage complet) au devis"

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    prestation_id = fields.Many2one('lolirine.pool.prestation', string='Prestation', required=True)
    titre = fields.Char("Titre sur le devis", required=True)
    description_client = fields.Text("Travaux décrits au client")
    detail_interne = fields.Text("Détail interne (étapes et heures)")
    mode_prix = fields.Selection([('heures', 'Au temps passé (heures × taux)'), ('forfait', 'Prix au forfait')],
                                 string="Mode de prix", required=True, default='heures')
    forfait_fixe = fields.Float("Prix au forfait HT (€)", digits=(10, 2))
    heures = fields.Float("Heures", digits=(10, 2))
    taux_horaire = fields.Float("Taux horaire HT (€)", digits=(10, 2))
    coef_difficulte = fields.Float("Coefficient de difficulté", digits=(10, 2), default=1.0)
    motif_coef = fields.Char("Motif du coefficient")
    prix = fields.Float("Forfait HT (€)", digits=(10, 2), compute='_compute_prix', store=True, readonly=False)

    # Ouvrage
    nb_fournitures = fields.Integer(related='prestation_id.nb_fournitures')
    total_fournitures = fields.Float(related='prestation_id.total_fournitures')
    avec_fournitures = fields.Boolean("Ajouter les fournitures de l'ouvrage", default=True)
    avec_options = fields.Boolean("Proposer les options au client", default=True)
    multiplicateur = fields.Float(
        "Quantités × ", digits=(10, 2), default=1.0,
        help="Multiplie les quantités des fournitures (ex. 2 pour deux pompes à chaleur).")

    @api.onchange('prestation_id')
    def _onchange_prestation(self):
        p = self.prestation_id
        if p:
            self.titre = p.name
            self.description_client = p.description_client
            self.detail_interne = p.detail_interne
            self.mode_prix = p.mode_prix
            self.forfait_fixe = p.forfait_fixe
            self.heures = p.heures
            self.taux_horaire = p.taux_horaire
            self.coef_difficulte = p.coef_difficulte or 1.0

    @api.depends('mode_prix', 'forfait_fixe', 'heures', 'taux_horaire', 'coef_difficulte')
    def _compute_prix(self):
        for w in self:
            w.prix = calcul_prix(w.mode_prix, w.forfait_fixe, w.heures, w.taux_horaire, w.coef_difficulte)

    def _detail_interne_ligne(self):
        if self.mode_prix == 'forfait':
            detail = "Forfait %.2f € HT" % self.prix
            if self.heures:
                detail += " (temps estimé %g h)" % self.heures
        else:
            detail = "%s h × %.2f €/h" % (('%g' % self.heures), self.taux_horaire)
            if (self.coef_difficulte or 1.0) != 1.0:
                detail += " × coef. %g" % self.coef_difficulte
                if self.motif_coef:
                    detail += " (%s)" % self.motif_coef
            detail += " = %.2f € HT" % self.prix
        if (self.detail_interne or '').strip():
            detail += "\n" + self.detail_interne.strip()
        return detail

    def _vals_fourniture(self, order, f, optionnel=False):
        vals = {
            'order_id': order.id,
            'product_id': f.product_id.id,
            'product_uom_qty': 0.0 if optionnel else f.quantite * (self.multiplicateur or 1.0),
            'price_unit': f.prix_unitaire,
        }
        if (f.name or '').strip():
            vals['name'] = f.name.strip()
        return vals

    def action_ajouter(self):
        self.ensure_one()
        order = self.order_id
        if order.state not in ('draft', 'sent'):
            raise UserError(_("Le devis n'est plus modifiable."))
        p = self.prestation_id
        fournitures = p.fourniture_ids.filtered(lambda f: not f.optionnel) if self.avec_fournitures else p.fourniture_ids.browse()
        options = p.fourniture_ids.filtered('optionnel') if self.avec_options else p.fourniture_ids.browse()
        if self.prix <= 0 and not fournitures:
            raise UserError(_("Le prix est à 0 € : indiquez un forfait, ou les heures et le taux horaire."))
        product = p.product_id or self.env['product.product'].search([('default_code', '=', 'MO-FORFAIT')], limit=1)
        if self.prix > 0 and not product:
            raise UserError(_("Article de main-d'œuvre introuvable (référence MO-FORFAIT)."))

        Line = self.env['sale.order.line']
        ordre = list(order.order_line.sorted(lambda l: (l.sequence, l.id)))
        sections = [l for l in ordre if l.display_type == 'line_section']
        section_mo = next((l for l in sections if "main" in (l.name or '').lower()), None)

        # 1) Fournitures : section de l'ouvrage, placée avant la main-d'œuvre
        if fournitures:
            titre_section = (p.section_fournitures or p.name).strip()
            section_f = next((l for l in sections if (l.name or '').strip() == titre_section), None)
            if not section_f:
                section_f = Line.create({'order_id': order.id, 'display_type': 'line_section', 'name': titre_section})
                ordre.insert(ordre.index(section_mo) if section_mo else len(ordre), section_f)
            i = _fin_de_bloc(ordre, section_f)
            for f in fournitures:
                ligne = Line.create(self._vals_fourniture(order, f))
                if f.cout_unitaire:
                    ligne.purchase_price = f.cout_unitaire
                ordre.insert(i, ligne)
                i += 1

        # 2) Main-d'œuvre : en fin de section main-d'œuvre
        if self.prix > 0:
            if not section_mo:
                section_mo = Line.create({'order_id': order.id, 'display_type': 'line_section', 'name': SECTION_MO})
                ordre.append(section_mo)
            nom = self.titre.strip()
            if (self.description_client or '').strip():
                nom += "\n" + self.description_client.strip()
            mo = Line.create({
                'order_id': order.id,
                'product_id': product.id,
                'name': nom,
                'product_uom_qty': 1.0,
                'price_unit': self.prix,
                'pool_mo_detail': self._detail_interne_ligne(),
                'pool_prestation_id': p.id,
            })
            ordre.insert(_fin_de_bloc(ordre, section_mo), mo)

        # 3) Options : section optionnelle en fin de devis (quantité 0, le client choisit en ligne)
        if options:
            section_o = next((l for l in sections if l.is_optional), None)
            if not section_o:
                section_o = Line.create({'order_id': order.id, 'display_type': 'line_section',
                                         'name': SECTION_OPTIONS, 'is_optional': True})
                ordre.append(section_o)
            i = _fin_de_bloc(ordre, section_o)
            for f in options:
                ligne = Line.create(self._vals_fourniture(order, f, optionnel=True))
                if f.cout_unitaire:
                    ligne.purchase_price = f.cout_unitaire
                ordre.insert(i, ligne)
                i += 1

        _renumeroter(ordre)
        return {'type': 'ir.actions.act_window_close'}


class PoolOuvrageWizard(models.TransientModel):
    """Enregistre des lignes d'un devis comme ouvrage réutilisable du tableau de main-d'œuvre."""
    _name = 'lolirine.pool.ouvrage.wizard'
    _description = "Enregistrer un ouvrage depuis un devis"

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    section_ids = fields.Many2many(
        'sale.order.line', 'pool_ouvrage_wiz_section_rel', 'wizard_id', 'line_id',
        string="Sections de fournitures à reprendre",
        domain="[('order_id', '=', order_id), ('display_type', '=', 'line_section')]")
    mo_line_id = fields.Many2one(
        'sale.order.line', string="Ligne de main-d'œuvre",
        domain="[('order_id', '=', order_id), ('display_type', '=', False)]",
        help="Son titre, sa description, son prix et son détail interne deviennent la prestation.")
    prestation_id = fields.Many2one(
        'lolirine.pool.prestation', string="Remplacer l'ouvrage existant",
        help="Vide : un nouvel ouvrage est créé.")
    nom = fields.Char("Nom de l'ouvrage")
    categorie_nouvelle = fields.Selection(CATEGORIES, string="Catégorie", default='autre')
    section_fournitures = fields.Char("Titre de la section fournitures")

    @api.onchange('mo_line_id')
    def _onchange_mo_line(self):
        if self.mo_line_id and not self.nom:
            self.nom = (self.mo_line_id.name or '').split('\n')[0].strip()

    @api.onchange('section_ids')
    def _onchange_sections(self):
        if len(self.section_ids) == 1 and not self.section_fournitures:
            self.section_fournitures = self.section_ids.name

    def _lignes_des_sections(self):
        lignes = self.env['sale.order.line']
        ordre = self.order_id.order_line.sorted(lambda l: (l.sequence, l.id))
        dans = False
        for l in ordre:
            if l.display_type == 'line_section':
                dans = l in self.section_ids
                continue
            if dans and not l.display_type and l != self.mo_line_id and not l._pool_ligne_mo():
                lignes |= l
        return lignes

    def action_enregistrer(self):
        self.ensure_one()
        lignes = self._lignes_des_sections()
        if not lignes and not self.mo_line_id:
            raise UserError(_("Rien à enregistrer : choisissez au moins une section ou une ligne de main-d'œuvre."))
        nom = (self.nom or '').strip() or (self.prestation_id.name if self.prestation_id else '')
        if not nom:
            raise UserError(_("Donnez un nom à l'ouvrage."))
        vals = {
            'name': nom,
            'section_fournitures': (self.section_fournitures or '').strip() or False,
            'fourniture_ids': [(5, 0, 0)] + [(0, 0, {
                'sequence': n * 10,
                'product_id': l.product_id.id,
                'name': l.name,
                'quantite': l.product_uom_qty or 1.0,
                'prix_unitaire': l.price_unit,
                'cout_unitaire': l.purchase_price,
                'optionnel': bool(l.parent_id.is_optional),
            }) for n, l in enumerate(lignes, start=1)],
        }
        mo = self.mo_line_id
        if mo:
            texte = (mo.name or '').split('\n')
            vals.update({
                'description_client': "\n".join(texte[1:]).strip() or False,
                'mode_prix': 'forfait',
                'forfait_fixe': mo.price_unit * (mo.product_uom_qty or 1.0),
                'detail_interne': mo.pool_mo_detail or False,
                'product_id': mo.product_id.id,
            })
        if self.prestation_id:
            self.prestation_id.write(vals)
            ouvrage = self.prestation_id
        else:
            vals['categorie'] = self.categorie_nouvelle or 'autre'
            ouvrage = self.env['lolirine.pool.prestation'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.pool.prestation',
            'res_id': ouvrage.id,
            'view_mode': 'form',
            'target': 'current',
        }
