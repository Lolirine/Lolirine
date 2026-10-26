# -*- coding: utf-8 -*-
"""Visionneuse des catalogues fournisseurs (SCP, Fluidra) depuis les devis piscine
et les bons de commande fournisseur : vérification visuelle des références et
des prix catalogue avant envoi.

- SCP : catalogue PDF affiché page par page (pdf.js, lecture partielle du PDF).
  L'index « référence → page / lettre / prix » est construit une fois dans le
  navigateur (bouton « Indexer ») puis enregistré dans une pièce jointe.
- Fluidra : catalogue en ligne (flipbook) affiché dans un cadre à la bonne page.
  L'index est lu côté serveur depuis le texte de recherche du flipbook.
Aucun nouveau champ en base : configuration dans les paramètres système,
index dans des pièces jointes.
"""
import json
import logging
import re

import requests

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CATALOGUES = {
    'scp': {
        'label': 'SCP Benelux 2026',
        'type': 'pdf',
        'param': 'lolirine_pool.catalogue_scp_url',
        'url': 'https://it2resources.interactiv-doc.fr/downloads/scp_benelux_1196_enrich.pdf',
    },
    'fluidra': {
        'label': 'Fluidra Benelux 2026',
        'type': 'flipbook',
        'param': 'lolirine_pool.catalogue_fluidra_url',
        'url': 'https://fluidrabenelux.com/catalogus/2026/fr-be/',
    },
}
RE_CODE_FLUIDRA = re.compile(r'(?<![A-Za-z0-9])([A-Z0-9][A-Z0-9\-/\.]{3,24})(?![A-Za-z0-9])')
RE_PRIX_FLUIDRA = re.compile(r'€\s?(\d{1,3}(?:\.\d{3})*,\d{2})')
NAVIGATEUR = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')


def _norm(code):
    code = (code or '').strip().upper()
    if code.startswith('POOL-'):
        code = code[5:]
    return re.sub(r'[\s\-/\.]', '', code)


class PoolCatalogueMixin(models.AbstractModel):
    _name = 'pool.catalogue.mixin'
    _description = 'Pool Store — visionneuse des catalogues fournisseurs'

    # ------------------------------------------------------------ configuration
    @api.model
    def _pool_catalogue_url(self, key):
        conf = CATALOGUES[key]
        return self.env['ir.config_parameter'].sudo().get_param(conf['param']) or conf['url']

    @api.model
    def _pool_catalogue_cle_fournisseur(self, partner):
        nom = (partner.commercial_partner_id.name or partner.name or '').upper() if partner else ''
        if 'SCP' in nom or 'POOLCORP' in nom:
            return 'scp'
        if 'FLUIDRA' in nom or 'SIBO' in nom:
            return 'fluidra'
        return False

    @api.model
    def _pool_catalogue_piece(self, key):
        return self.env['ir.attachment'].sudo().search(
            [('name', '=', 'pool_catalogue_%s.json' % key), ('res_model', '=', 'pool.catalogue.mixin')],
            limit=1, order='id desc')

    # ------------------------------------------------------------ index
    @api.model
    def pool_catalogue_index(self, key):
        """Index enregistré : {'url', 'codes': {CODE: [page, lettre, prix]}, 'toc': [...], 'date'}."""
        if key not in CATALOGUES:
            return {}
        piece = self._pool_catalogue_piece(key)
        if not piece or not piece.raw:
            return {}
        try:
            data = json.loads(piece.raw.decode('utf-8'))
        except Exception:
            return {}
        if data.get('url') != self._pool_catalogue_url(key):
            return {}          # index d'un autre millésime
        return data

    @api.model
    def pool_catalogue_index_save(self, key, data):
        """Enregistre l'index construit dans le navigateur (catalogue SCP)."""
        if key not in CATALOGUES or not isinstance(data, dict):
            raise UserError("Index de catalogue invalide.")
        if not (self.env.user.has_group('purchase.group_purchase_user')
                or self.env.user.has_group('sales_team.group_sale_salesman')):
            raise UserError("Accès refusé.")
        data = dict(data, url=self._pool_catalogue_url(key), date=str(self.env.cr.now())[:16])
        raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
        piece = self._pool_catalogue_piece(key)
        vals = {'raw': raw, 'mimetype': 'application/json'}
        if piece:
            piece.write(vals)
        else:
            self.env['ir.attachment'].sudo().create(dict(
                vals, name='pool_catalogue_%s.json' % key, res_model='pool.catalogue.mixin', res_id=0))
        return {'codes': len(data.get('codes') or {}), 'date': data['date']}

    @api.model
    def pool_catalogue_index_fluidra(self):
        """Lit le texte de recherche et la table des matières du flipbook Fluidra et
        enregistre l'index « référence → page / prix ». Renvoie l'index."""
        base = self._pool_catalogue_url('fluidra').rstrip('/') + '/'
        entetes = {'User-Agent': NAVIGATEUR, 'Accept': '*/*', 'Referer': base}
        try:
            r = requests.get(base + 'files/assets/mobile/search/searchtext.js', headers=entetes, timeout=60)
            r.raise_for_status()
            pages = json.loads(r.text)['pages']['page']
            toc = []
            try:
                w = requests.get(base + 'files/assets/workspace.js', headers=entetes, timeout=30)
                toc = [{'title': c.get('title'), 'page': c.get('page'), 'level': 0}
                       for c in (json.loads(w.text).get('toc') or {}).get('children') or []]
            except Exception:
                _logger.warning("Catalogue Fluidra : table des matières illisible", exc_info=True)
        except Exception as e:
            _logger.warning("Catalogue Fluidra : texte de recherche illisible", exc_info=True)
            raise UserError("Le catalogue Fluidra n'a pas pu être lu depuis le serveur (%s). "
                            "La visionneuse reste utilisable, sans recherche automatique de la page." % e)
        codes = {}
        for p in sorted(pages, key=lambda x: int(x.get('@ID') or 0)):
            num, texte = int(p.get('@ID') or 0), p.get('#text') or ''
            for m in RE_CODE_FLUIDRA.finditer(texte):
                code = m.group(1).rstrip('.-/')
                if len(code) < 4 or not re.search(r'\d', code) or re.fullmatch(r'\d{1,3}(\.\d{3})*|\d+\.\d+|(19|20)\d\d', code):
                    continue
                cle = _norm(code)
                if cle in codes:
                    continue
                pm = RE_PRIX_FLUIDRA.search(texte, m.end(), m.end() + 90)
                prix = float(pm.group(1).replace('.', '').replace(',', '.')) if pm else None
                if prix is None and not (re.search(r'[A-Z]', code) or re.fullmatch(r'\d{5,}[A-Z]{0,3}', code)):
                    continue
                codes[cle] = [num, '', prix]
        self.pool_catalogue_index_save('fluidra', {'codes': codes, 'toc': toc, 'pages': len(pages)})
        return self.pool_catalogue_index('fluidra')

    # ------------------------------------------------------------ données de la visionneuse
    @api.model
    def pool_catalogue_donnees(self, res_model, res_id):
        """Lignes du devis / bon à vérifier et configuration des catalogues."""
        if res_model not in ('sale.order', 'purchase.order'):
            raise UserError("Document non pris en charge.")
        doc = self.env[res_model].browse(int(res_id)).exists()
        if not doc:
            raise UserError("Document introuvable.")
        doc.check_access('read')
        Info = self.env['supplier.dropship.info'].sudo()
        lignes = []
        if res_model == 'purchase.order':
            cle = self._pool_catalogue_cle_fournisseur(doc.partner_id)
            for l in doc.order_line.filtered(lambda x: not x.display_type and x.product_id):
                ref = getattr(l, 'supplier_product_ref', False) or ''
                if not ref:
                    info = Info.search([('product_tmpl_id', '=', l.product_id.product_tmpl_id.id),
                                        ('supplier_id', '=', doc.partner_id.commercial_partner_id.id)], limit=1)
                    ref = info._pool_ligne_bc(l.product_id)[0] if info else ''
                lignes.append({
                    'id': l.id, 'nom': l.product_id.display_name, 'qte': l.product_qty,
                    'ref': ref, 'fournisseur': cle, 'fournisseur_nom': doc.partner_id.name,
                    'prix_catalogue': l.price_unit, 'remise': l.discount,
                    'prix_net': l.price_unit * (1 - (l.discount or 0) / 100.0),
                    'prix_vente': False,
                })
        else:
            for l in doc.order_line.filtered(lambda x: not x.display_type and x.product_id):
                tmpl = l.product_id.product_tmpl_id
                info = Info.search([('product_tmpl_id', '=', tmpl.id), ('is_active', '=', True)], limit=1)
                ref, prix, remise = info._pool_ligne_bc(l.product_id) if info else ('', 0.0, 0.0)
                lignes.append({
                    'id': l.id, 'nom': l.product_id.display_name, 'qte': l.product_uom_qty,
                    'ref': ref, 'fournisseur': self._pool_catalogue_cle_fournisseur(info.supplier_id) if info else False,
                    'fournisseur_nom': info.supplier_id.name if info else '',
                    'prix_catalogue': prix, 'remise': remise,
                    'prix_net': prix * (1 - (remise or 0) / 100.0),
                    'prix_vente': l.price_unit,
                })
        return {
            'document': doc.display_name,
            'res_model': res_model,
            'lignes': lignes,
            'catalogues': {k: {'label': v['label'], 'type': v['type'], 'url': self._pool_catalogue_url(k)}
                           for k, v in CATALOGUES.items()},
        }


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_pool_catalogues(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'lolirine_pool_catalogue',
            'name': 'Catalogues — %s' % self.name,
            'params': {'res_model': 'sale.order', 'res_id': self.id},
            'target': 'current',
        }


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_pool_catalogues(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'lolirine_pool_catalogue',
            'name': 'Catalogues — %s' % self.name,
            'params': {'res_model': 'purchase.order', 'res_id': self.id},
            'target': 'current',
        }
