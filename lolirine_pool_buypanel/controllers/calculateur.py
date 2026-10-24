"""Calculateur de volume et sélecteur de pompe à chaleur (Pool Store).

Page /calculateur-piscine : le visiteur calcule le volume de son bassin, puis
la puissance de pompe à chaleur conseillée ; la page interroge
/calculateur-piscine/pac pour proposer les modèles du catalogue adaptés.

La puissance (kW) et la plage de volume (m³) de chaque modèle sont lues dans
le nom de ses déclinaisons, ex. « 13,5 kW (30-50 m³) » ou « 17 kW (<70 m³) ».
Si la déclinaison porte les champs « Puissance de chauffe (kW) », « Volume
conseillé » et « Triphasé » (models/pac.py), ils sont prioritaires sur le nom.
Les déclinaisons sans ces informations ne sont pas proposées.
"""
import re

from odoo import http
from odoo.http import request

from ..models.livraison import langue, tr

SITE_POOL_STORE = 6
CATEGORIE_PAC = 127  # Équipements & Pièces / Chauffage & PAC / Pompes à chaleur

RE_KW = re.compile(r'(\d+(?:[.,]\d+)?)(?:\s*-\s*(\d+(?:[.,]\d+)?))?\s*kW', re.I)
RE_M3 = re.compile(r'\(\s*(<)?\s*(\d+)(?:\s*-\s*(\d+))?\s*m³\s*\)')


def _nombre(txt):
    return float(txt.replace(',', '.')) if txt else 0.0


class CalculateurPiscine(http.Controller):

    @http.route('/calculateur-piscine', type='http', auth='public', website=True, sitemap=True)
    def calculateur(self, **kw):
        if request.website.id != SITE_POOL_STORE:
            return request.not_found()
        return request.render('lolirine_pool_buypanel.calculateur_piscine', {})

    @http.route('/calculateur-piscine/pac', type='jsonrpc', auth='public', website=True)
    def calculateur_pac(self, kw=0, volume=0, triphase=False, **kwargs):
        if request.website.id != SITE_POOL_STORE:
            return {'modeles': []}
        try:
            besoin = float(kw or 0)
            volume = float(volume or 0)
        except (TypeError, ValueError):
            return {'modeles': []}
        if besoin <= 0:
            return {'modeles': []}

        Product = request.env['product.product']
        variantes = Product.search([
            ('product_tmpl_id.public_categ_ids', 'child_of', CATEGORIE_PAC),
            ('product_tmpl_id.is_published', '=', True),
            ('product_tmpl_id.sale_ok', '=', True),
            ('product_tmpl_id.website_id', 'in', (False, SITE_POOL_STORE)),
        ])
        candidats = []
        for v in variantes:
            libelle = ' '.join(v.product_template_attribute_value_ids.mapped('name'))
            vs = v.sudo()
            if vs.x_lp_puissance_kw:
                # Données fabricant posées sur la déclinaison (prioritaires sur le nom)
                puissance = vs.x_lp_puissance_kw
                tri = vs.x_lp_triphase
                vmin, vmax = vs.x_lp_volume_min or 0.0, vs.x_lp_volume_max or 0.0
                libelle = '%s — %s kW' % (libelle, ('%g' % puissance).replace('.', ','))
            else:
                m_kw = RE_KW.search(libelle)
                if not m_kw:
                    continue
                puissance = _nombre(m_kw.group(2) or m_kw.group(1))  # « 6-8 kW » → 8 kW
                tri = '3~' in libelle
                vmin = vmax = 0.0
                m_m3 = RE_M3.search(libelle)
                if m_m3:
                    if m_m3.group(1):  # « <70 m³ »
                        vmax = _nombre(m_m3.group(2))
                    else:
                        vmin = _nombre(m_m3.group(2))
                        vmax = _nombre(m_m3.group(3) or m_m3.group(2))
            if bool(tri) != bool(triphase):
                continue
            # Puissance suffisante, sans surdimensionner de plus de 60 %
            if puissance < besoin or puissance > besoin * 1.6:
                continue
            if volume and vmax and volume > vmax:
                continue
            tmpl = v.product_tmpl_id
            info = tmpl._get_combination_info(product_id=v.id, add_qty=1)
            candidats.append({
                'nom': tmpl.name,
                'variante': libelle,
                'kw': puissance,
                'plage': ('%d–%d m³' % (vmin, vmax)) if vmin and vmax and vmin != vmax else (
                    (tr(langue(request.env), 'jusqu\'à %d m³', 'tot %d m³', 'up to %d m³') % vmax) if vmax else ''),
                'prix': info.get('price', 0.0),
                'url': v.website_url,
                'image': '/web/image/product.product/%s/image_256' % v.id,
            })
        # Un modèle par gamme (la plus petite puissance suffisante), puis par prix
        par_gamme = {}
        for c in sorted(candidats, key=lambda c: (c['kw'], c['prix'])):
            par_gamme.setdefault(c['nom'], c)
        modeles = sorted(par_gamme.values(), key=lambda c: c['prix'])[:6]
        devise = request.website.currency_id
        for m in modeles:
            m['prix_txt'] = ('%s %s' % (('{:,.2f}'.format(m['prix'])).replace(',', ' ').replace('.', ',')
                                        .replace(' ', '.'), devise.symbol or '€'))
        return {'modeles': modeles}
