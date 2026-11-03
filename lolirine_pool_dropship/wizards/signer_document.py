# -*- coding: utf-8 -*-
"""Signer un document du fournisseur (sa confirmation de commande en PDF) : la signature
dessinée dans l'onglet « ✍ Signature » du bon est apposée sur le PDF, qui est joint au bon
puis renvoyé au fournisseur par e-mail (relu avant l'envoi)."""
import base64
import io

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.pdf import PdfFileReader, PdfFileWriter

POSITIONS = [('bas_droite', 'En bas à droite'), ('bas_gauche', 'En bas à gauche'),
             ('haut_droite', 'En haut à droite'), ('milieu_droite', 'Au milieu à droite')]
PAGES = [('derniere', 'Dernière page'), ('premiere', 'Première page'), ('toutes', 'Toutes les pages')]


class PoolSignerDocument(models.TransientModel):
    _name = 'lolirine.pool.signer.document'
    _description = "Signer un document du fournisseur"

    po_id = fields.Many2one('purchase.order', required=True, readonly=True)
    attachment_id = fields.Many2one(
        'ir.attachment', "Document à signer", required=True,
        domain="[('res_model', '=', 'purchase.order'), ('res_id', '=', po_id), ('mimetype', '=', 'application/pdf')]")
    mention = fields.Char("Mention", default="Bon pour accord")
    page = fields.Selection(PAGES, string="Page", default='derniere', required=True)
    position = fields.Selection(POSITIONS, string="Emplacement", default='bas_droite', required=True)
    signe_id = fields.Many2one('ir.attachment', "Document signé", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        po = self.env['purchase.order'].browse(res.get('po_id') or self.env.context.get('default_po_id'))
        if po and 'attachment_id' in fields_list:
            pdfs = self.env['ir.attachment'].search(
                [('res_model', '=', 'purchase.order'), ('res_id', '=', po.id), ('mimetype', '=', 'application/pdf'),
                 ('name', 'not ilike', 'signé')], order='id desc')
            # de préférence le document du fournisseur (pas notre propre bon de commande)
            choix = pdfs.filtered(lambda a: po.name.lower() not in (a.name or '').lower() or 'confirmation' in (a.name or '').lower())
            res['attachment_id'] = (choix or pdfs)[:1].id
        return res

    def _tampon(self, largeur, hauteur):
        """Page PDF transparente portant la signature, la mention, le nom et la date."""
        po = self.po_id
        image = ImageReader(io.BytesIO(base64.b64decode(po.pool_signature)))
        iw, ih = image.getSize()
        w = 150.0
        h = w * ih / iw if iw else 60.0
        if h > 70:
            h, w = 70.0, 70.0 * iw / ih
        bloc_w, bloc_h = max(w, 170.0), h + 46
        marge = 28
        x = largeur - bloc_w - marge if 'droite' in self.position else marge
        if self.position.startswith('bas'):
            y = 175          # au-dessus des pieds de page et tableaux de totaux habituels
        elif self.position.startswith('haut'):
            y = hauteur - bloc_h - 90
        else:
            y = (hauteur - bloc_h) / 2
        flux = io.BytesIO()
        c = canvas.Canvas(flux, pagesize=(largeur, hauteur))
        c.setFont('Helvetica-Bold', 9)
        c.drawCentredString(x + bloc_w / 2, y + bloc_h - 10, "%s — %s" % (self.mention or '', po.company_id.name))
        c.drawImage(image, x + (bloc_w - w) / 2, y + 26, width=w, height=h, mask='auto')
        c.setFont('Helvetica', 8)
        c.drawCentredString(x + bloc_w / 2, y + 14, po.pool_signe_par or self.env.user.name)
        date = fields.Datetime.context_timestamp(self, po.pool_signe_le or fields.Datetime.now()).strftime('%d/%m/%Y')
        c.drawCentredString(x + bloc_w / 2, y + 4, "Signé le %s — réf. %s" % (date, po.name))
        c.save()
        flux.seek(0)
        return PdfFileReader(flux).pages[0]

    def action_signer(self):
        self.ensure_one()
        po = self.po_id
        if not po.pool_signature:
            raise UserError(_("Signe d'abord le bon dans l'onglet « ✍ Signature », puis recommence."))
        try:
            lecteur = PdfFileReader(io.BytesIO(base64.b64decode(self.attachment_id.datas)), strict=False)
            nb = len(lecteur.pages)
        except Exception as e:
            raise UserError(_("Ce document n'est pas un PDF lisible : %s") % e)
        cibles = set(range(nb)) if self.page == 'toutes' else {0 if self.page == 'premiere' else nb - 1}
        ecrivain = PdfFileWriter()
        for i, page in enumerate(lecteur.pages):
            if i in cibles:
                box = page.mediabox
                page.merge_page(self._tampon(float(box.width), float(box.height)))
            ecrivain.add_page(page)
        sortie = io.BytesIO()
        ecrivain.write(sortie)
        nom = (self.attachment_id.name or 'document.pdf')
        nom = (nom[:-4] if nom.lower().endswith('.pdf') else nom) + ' - signé.pdf'
        signe = self.env['ir.attachment'].create({
            'name': nom, 'raw': sortie.getvalue(), 'mimetype': 'application/pdf',
            'res_model': 'purchase.order', 'res_id': po.id})
        self.signe_id = signe
        po.message_post(body=_("Document du fournisseur signé : %s") % nom, attachment_ids=signe.ids,
                        message_type='comment', subtype_xmlid='mail.mt_note')
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
                'view_mode': 'form', 'target': 'new', 'name': _("Document signé")}

    def action_apercu(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'target': 'new',
                'url': '/web/content/%s?download=false' % self.signe_id.id}

    def action_envoyer(self):
        """E-mail au fournisseur avec le document signé, relu avant l'envoi."""
        self.ensure_one()
        po = self.po_id
        dest = po.partner_id.commercial_partner_id
        corps = _(
            "<p>Bonjour,</p><p>Veuillez trouver ci-joint votre document <strong>%(doc)s</strong> signé pour accord, "
            "concernant notre commande <strong>%(po)s</strong>%(ref)s.</p>"
            "<p>Cordialement,<br/>%(user)s<br/>Lolirine Pool Store — %(soc)s<br/>+32 497 44 41 46 — info@lolirinepoolstore.be</p>"
        ) % {'doc': self.attachment_id.name, 'po': po.name,
             'ref': (_(" (votre référence %s)") % po.partner_ref) if po.partner_ref else '',
             'user': self.env.user.name, 'soc': po.company_id.name}
        return {
            'type': 'ir.actions.act_window', 'res_model': 'mail.compose.message', 'view_mode': 'form',
            'views': [(False, 'form')], 'target': 'new', 'name': _("Renvoyer le document signé"),
            'context': {
                'default_model': 'purchase.order', 'default_res_ids': po.ids,
                'default_composition_mode': 'comment',
                'default_subject': _("%(po)s — document signé%(ref)s — %(soc)s") % {
                    'po': po.name, 'ref': (" (%s)" % po.partner_ref) if po.partner_ref else '', 'soc': po.company_id.name},
                'default_body': corps,
                'default_partner_ids': dest.ids,
                'default_attachment_ids': self.signe_id.ids,
                'default_email_layout_xmlid': 'mail.mail_notification_light',
                'force_email': True,
            },
        }


class PurchaseOrderSignerDocument(models.Model):
    _inherit = 'purchase.order'

    def action_pool_signer_document(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'lolirine.pool.signer.document',
                'view_mode': 'form', 'target': 'new', 'name': _("Signer un document du fournisseur"),
                'context': {'default_po_id': self.id}}
