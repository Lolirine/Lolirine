# -*- coding: utf-8 -*-
"""Récupération des médias Allforpools (images, fiches PDF) côté serveur.

Le site www.allforpools.be est une boutique Odoo : les images produits sont
publiques (/web/image/...), les documents se téléchargent par POST sur
/download/attachment avec le jeton CSRF de la page produit.
Les appels sont limités au domaine allforpools.be.
"""
import base64
import logging
import re
from urllib.parse import urljoin, urlparse

import requests

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

AFP_BASE = 'https://www.allforpools.be'
AFP_HOSTS = {'www.allforpools.be', 'allforpools.be'}
TIMEOUT = 40
UA = {'User-Agent': 'Mozilla/5.0 (Lolirine Pool Store catalogue sync)'}


def _afp_url(url):
    full = urljoin(AFP_BASE, url or '')
    if urlparse(full).hostname not in AFP_HOSTS:
        raise UserError("URL refusée (domaine Allforpools uniquement) : %s" % url)
    return full


def _get_b64(session, url):
    resp = session.get(_afp_url(url), timeout=TIMEOUT, headers=UA)
    resp.raise_for_status()
    ctype = resp.headers.get('content-type', '')
    if 'image' not in ctype and 'pdf' not in ctype and 'octet' not in ctype:
        raise UserError("Contenu inattendu (%s) pour %s" % (ctype, url))
    return base64.b64encode(resp.content)


def _image_url(path):
    """/web/image/product.product/8602 -> .../image_1920"""
    path = re.sub(r'/image_\d+.*$', '', path or '')
    return path.rstrip('/') + '/image_1920'


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def pool_afp_apply_media(self, media):
        """Pose les médias Allforpools sur la fiche.

        media = {
            'page': '/shop/...',                 # page produit AFP (pour les PDF)
            'images': ['/web/image/product.product/8602', '/web/image/product.image/2434', ...],
            'docs': [{'id': 322, 'name': 'Fiche technique.pdf'}, ...],
            'variant_images': {<id product.product Lolirine>: '/web/image/product.product/1234'},
            'replace': False,                     # True : remplace image et extras existants
        }
        Retourne un résumé des opérations.
        """
        self.ensure_one()
        out = {'image': False, 'extras': 0, 'docs': 0, 'variants': 0, 'errors': []}
        session = requests.Session()
        replace = media.get('replace')
        images = media.get('images') or []

        # Image principale + images supplémentaires
        if images and (replace or not self.image_1920):
            try:
                self.image_1920 = _get_b64(session, _image_url(images[0]))
                out['image'] = True
            except Exception as e:  # noqa: BLE001
                out['errors'].append('image %s : %s' % (images[0], e))
        if images[1:] and (replace or not self.product_template_image_ids):
            if replace:
                self.product_template_image_ids.unlink()
            for seq, path in enumerate(images[1:], start=10):
                try:
                    self.env['product.image'].create({
                        'name': self.name[:120],
                        'product_tmpl_id': self.id,
                        'image_1920': _get_b64(session, _image_url(path)),
                        'sequence': seq,
                    })
                    out['extras'] += 1
                except Exception as e:  # noqa: BLE001
                    out['errors'].append('extra %s : %s' % (path, e))

        # Images de variantes
        for pid, path in (media.get('variant_images') or {}).items():
            variant = self.env['product.product'].browse(int(pid)).exists()
            if not variant or variant.product_tmpl_id != self:
                continue
            if variant.image_variant_1920 and not replace:
                continue
            try:
                variant.image_variant_1920 = _get_b64(session, _image_url(path))
                out['variants'] += 1
            except Exception as e:  # noqa: BLE001
                out['errors'].append('variante %s : %s' % (path, e))

        # Fiches techniques PDF
        docs = media.get('docs') or []
        if docs and media.get('page'):
            existing = set(self.env['product.document'].search([
                ('res_model', '=', 'product.template'), ('res_id', '=', self.id),
            ]).mapped('name'))
            try:
                page = session.get(_afp_url(media['page']), timeout=TIMEOUT, headers=UA)
                page.raise_for_status()
                m = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.text)
                token = m and m.group(1)
            except Exception as e:  # noqa: BLE001
                token = None
                out['errors'].append('page %s : %s' % (media['page'], e))
            for doc in docs:
                name = (doc.get('name') or 'Fiche technique.pdf').strip()
                if name in existing:
                    continue
                try:
                    resp = session.post(
                        _afp_url('/download/attachment?attachment_id=%s' % int(doc['id'])),
                        data={'csrf_token': token or ''}, timeout=TIMEOUT, headers=UA)
                    resp.raise_for_status()
                    if not resp.content.startswith(b'%PDF'):
                        raise UserError('réponse non PDF')
                    self.env['product.document'].create({
                        'name': name,
                        'res_model': 'product.template',
                        'res_id': self.id,
                        'datas': base64.b64encode(resp.content),
                        'mimetype': 'application/pdf',
                        'shown_on_product_page': True,
                    })
                    out['docs'] += 1
                except Exception as e:  # noqa: BLE001
                    out['errors'].append('doc %s : %s' % (doc.get('id'), e))
        if out['errors']:
            _logger.warning('AFP media %s : %s', self.id, out['errors'])
        return out
