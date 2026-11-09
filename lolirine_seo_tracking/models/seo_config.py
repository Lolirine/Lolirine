# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError

P = 'lolirine_seo.'


class LolirineSeoConfig(models.TransientModel):
    _name = 'lolirine.seo.config'
    _description = 'Réglages SEO & Trafic'
    _rec_name = 'name'

    name = fields.Char(default='Réglages SEO & Trafic', readonly=True)

    website_ids_param = fields.Char(
        'ID des sites suivis', help="Identifiants des sites web suivis, séparés par des virgules (Pool Store = 6).")
    gsc_site = fields.Char(
        'Propriété Search Console',
        help="Ex. sc-domain:lolirinepoolstore.be (propriété domaine) "
             "ou https://www.lolirinepoolstore.be/ (préfixe d'URL).")
    gsc_credentials = fields.Text(
        'Clé JSON du compte de service Google',
        help="Contenu complet du fichier .json du compte de service Google Cloud "
             "(API Search Console activée). Ajoutez l'adresse client_email du compte "
             "de service comme utilisateur « Restreint » dans Search Console.")
    gsc_client_email = fields.Char('Compte de service', compute='_compute_gsc_client_email')
    gsc_backfill_days = fields.Integer('Historique au premier import (jours)', default=90)
    digest_email = fields.Char('Destinataire du rapport hebdomadaire')
    indexnow_enabled = fields.Boolean('IndexNow (Bing, Yandex, Seznam...)')
    indexnow_key = fields.Char('Clé IndexNow', readonly=True)
    gsc_last_import = fields.Char('Dernier import Search Console', readonly=True)
    indexnow_last = fields.Char('Dernier envoi IndexNow', readonly=True)
    audit_last = fields.Char('Dernier audit', readonly=True)

    # ------------------------------------------------------------------ utils
    @api.model
    def _get(self, key, default=False):
        return self.env['ir.config_parameter'].sudo().get_param(P + key, default)

    @api.model
    def _set(self, key, value):
        self.env['ir.config_parameter'].sudo().set_param(P + key, value or False)

    @api.model
    def _target_websites(self):
        raw = self._get('website_ids', '6') or '6'
        ids = [int(x) for x in raw.replace(' ', '').split(',') if x.isdigit()]
        return self.env['website'].sudo().browse(ids).exists()

    @api.model
    def _target_website_ids(self):
        return self._target_websites().ids

    @api.model
    def _digest_recipient(self):
        email = self._get('digest_email')
        if email:
            return email
        site = self._target_websites()[:1]
        return (site.company_id.email if site else False) or self.env.company.email

    # ------------------------------------------------------------- lifecycle
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res.update({
            'website_ids_param': self._get('website_ids', '6'),
            'gsc_site': self._get('gsc_site', ''),
            'gsc_credentials': self._get('gsc_credentials', ''),
            'gsc_backfill_days': int(self._get('gsc_backfill_days', 90) or 90),
            'digest_email': self._digest_recipient(),
            'indexnow_enabled': self._get('indexnow_enabled') == '1',
            'indexnow_key': self.env['lolirine.seo.indexnow']._key(),
            'gsc_last_import': self._get('gsc_last_import', '—'),
            'indexnow_last': self._get('indexnow_last', '—'),
            'audit_last': self._get('audit_last', '—'),
        })
        return res

    @api.depends('gsc_credentials')
    def _compute_gsc_client_email(self):
        for rec in self:
            email = False
            if rec.gsc_credentials:
                try:
                    email = json.loads(rec.gsc_credentials).get('client_email')
                except (ValueError, AttributeError):
                    email = _('JSON invalide')
            rec.gsc_client_email = email

    def action_save(self):
        self.ensure_one()
        if self.gsc_credentials:
            try:
                data = json.loads(self.gsc_credentials)
                assert data.get('client_email') and data.get('private_key')
            except Exception:
                raise UserError(_("La clé JSON du compte de service est invalide "
                                  "(client_email et private_key attendus)."))
        self._set('website_ids', self.website_ids_param or '6')
        self._set('gsc_site', (self.gsc_site or '').strip())
        self._set('gsc_credentials', self.gsc_credentials)
        self._set('gsc_backfill_days', str(self.gsc_backfill_days or 90))
        self._set('digest_email', self.digest_email)
        self._set('indexnow_enabled', '1' if self.indexnow_enabled else '0')
        return self._reopen(_("Réglages enregistrés."))

    def _reopen(self, message=None, kind='success'):
        action = {
            'type': 'ir.actions.act_window', 'res_model': self._name,
            'view_mode': 'form', 'views': [(False, 'form')], 'target': 'current',
            'name': _('Réglages SEO & Trafic'),
        }
        if not message:
            return action
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'message': message, 'type': kind, 'sticky': False,
                       'next': action},
        }

    # --------------------------------------------------------------- buttons
    def action_test_gsc(self):
        self.action_save()
        sites = self.env['lolirine.seo.gsc.line']._gsc_list_sites()
        wanted = self._get('gsc_site')
        if wanted and wanted not in sites:
            raise UserError(_(
                "Connexion OK mais la propriété « %(w)s » n'est pas accessible "
                "par ce compte de service.\nPropriétés visibles : %(s)s\n\n"
                "Ajoutez %(e)s comme utilisateur dans Search Console > Paramètres > "
                "Utilisateurs et autorisations.",
                w=wanted, s=', '.join(sites) or '(aucune)', e=self.gsc_client_email))
        return self._reopen(_("Search Console OK — propriétés : %s") % (', '.join(sites) or '—'))

    def action_import_gsc(self):
        self.action_save()
        n = self.env['lolirine.seo.gsc.line']._gsc_import()
        return self._reopen(_("%s lignes Search Console importées.") % n)

    def action_run_audit(self):
        n = self.env['lolirine.seo.issue']._run_audit()
        return self._reopen(_("Audit terminé : %s problèmes ouverts.") % n)

    def action_indexnow(self):
        self.action_save()
        n = self.env['lolirine.seo.indexnow']._submit_recent(hours=24 * 30, force=True)
        return self._reopen(_("%s URL soumises à IndexNow.") % n)

    def action_send_digest(self):
        self.action_save()
        self.env['lolirine.seo.dashboard']._send_digest()
        return self._reopen(_("Rapport envoyé à %s.") % self._digest_recipient())
