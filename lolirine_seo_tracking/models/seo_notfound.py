# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LolirineSeoNotFound(models.Model):
    _name = 'lolirine.seo.notfound'
    _description = 'Page introuvable (404)'
    _order = 'last_seen desc'
    _rec_name = 'url'

    website_id = fields.Many2one('website', 'Site', required=True, ondelete='cascade', index=True)
    url = fields.Char('URL demandée', required=True, index=True)
    hits_human = fields.Integer('Visiteurs')
    hits_bot = fields.Integer('Robots')
    last_bot = fields.Char('Dernier robot')
    last_referrer = fields.Char('Dernier référent')
    first_seen = fields.Datetime('Vue la 1re fois')
    last_seen = fields.Datetime('Vue la dernière fois', index=True)
    redirect_to = fields.Char('Rediriger vers (301)',
                              help="URL relative de destination, ex. /shop/category/pompes-12")
    rewrite_id = fields.Many2one('website.rewrite', 'Redirection', ondelete='set null')
    state = fields.Selection([('open', 'À traiter'), ('redirected', 'Redirigée'),
                              ('ignored', 'Ignorée')], default='open', required=True, index=True)

    _url_uniq = models.Constraint('unique(website_id, url)', 'URL déjà suivie pour ce site.')

    @api.model
    def _log(self, cr, website_id, url, referrer, bot):
        """Upsert SQL sur un curseur dédié (appelé pendant la gestion d'erreur)."""
        cr.execute("""
            INSERT INTO lolirine_seo_notfound
                (website_id, url, hits_human, hits_bot, last_bot, last_referrer,
                 first_seen, last_seen, state, create_uid, write_uid, create_date, write_date)
            VALUES (%(w)s, %(u)s, %(h)s, %(b)s, %(bn)s, %(r)s,
                    now() at time zone 'utc', now() at time zone 'utc', 'open',
                    1, 1, now() at time zone 'utc', now() at time zone 'utc')
            ON CONFLICT (website_id, url) DO UPDATE SET
                hits_human = lolirine_seo_notfound.hits_human + EXCLUDED.hits_human,
                hits_bot = lolirine_seo_notfound.hits_bot + EXCLUDED.hits_bot,
                last_bot = COALESCE(EXCLUDED.last_bot, lolirine_seo_notfound.last_bot),
                last_referrer = COALESCE(EXCLUDED.last_referrer, lolirine_seo_notfound.last_referrer),
                last_seen = EXCLUDED.last_seen,
                write_date = EXCLUDED.write_date
        """, {
            'w': website_id, 'u': url[:500], 'h': 0 if bot else 1, 'b': 1 if bot else 0,
            'bn': bot or None, 'r': (referrer or '')[:500] or None,
        })

    def action_create_redirect(self):
        Rewrite = self.env['website.rewrite'].sudo()
        for rec in self:
            target = (rec.redirect_to or '').strip()
            if not target.startswith('/'):
                raise UserError(_("Indiquez une URL de destination relative commençant par / pour %s.") % rec.url)
            rw = Rewrite.create({
                'name': 'SEO 404 : %s' % rec.url[:80],
                'website_id': rec.website_id.id,
                'redirect_type': '301',
                'url_from': rec.url,
                'url_to': target,
            })
            rec.write({'rewrite_id': rw.id, 'state': 'redirected'})
        return True

    def action_ignore(self):
        self.write({'state': 'ignored'})
        return True
