# -*- coding: utf-8 -*-
from datetime import timedelta
from html import escape

from odoo import api, fields, models, _

from . import seo_sources as S

BLUE = '#0284c7'
SRC_LABEL = dict(S.SOURCE_TYPES)


def _fmt_int(n):
    return '{:,}'.format(int(n or 0)).replace(',', ' ')


def _delta(cur, prev):
    if not prev:
        return '<span style="color:#64748b">nouveau</span>' if cur else '—'
    pct = (cur - prev) * 100.0 / prev
    color = '#16a34a' if pct >= 0 else '#dc2626'
    return '<span style="color:%s">%+.0f %%</span>' % (color, pct)


def _table(headers, rows, aligns=None):
    aligns = aligns or ['left'] + ['right'] * (len(headers) - 1)
    th = ''.join('<th style="text-align:%s;padding:6px 8px;border-bottom:2px solid %s;'
                 'font-size:12px;color:#334155">%s</th>' % (a, BLUE, escape(h))
                 for h, a in zip(headers, aligns))
    if not rows:
        return ('<p style="color:#64748b;font-style:italic;margin:4px 0 16px">'
                'Pas encore de données.</p>')
    body = ''
    for r in rows:
        body += '<tr>' + ''.join(
            '<td style="text-align:%s;padding:5px 8px;border-bottom:1px solid #e2e8f0;'
            'font-size:13px">%s</td>' % (a, c) for c, a in zip(r, aligns)) + '</tr>'
    return ('<table style="border-collapse:collapse;width:100%%;margin:4px 0 18px">'
            '<thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (th, body))


def _h(title, sub=''):
    return ('<h3 style="color:%s;margin:22px 0 4px;font-size:16px">%s</h3>%s' % (
        BLUE, escape(title),
        '<p style="color:#64748b;margin:0 0 6px;font-size:12px">%s</p>' % escape(sub) if sub else ''))


class LolirineSeoDashboard(models.TransientModel):
    _name = 'lolirine.seo.dashboard'
    _description = 'Tableau de bord SEO & Trafic'
    _rec_name = 'name'

    name = fields.Char(default='Tableau de bord SEO', readonly=True)

    period = fields.Selection([('7', '7 derniers jours'), ('28', '28 derniers jours'),
                               ('90', '90 derniers jours'), ('365', '12 derniers mois')],
                              default='28', required=True, string='Période')
    report_html = fields.Html(compute='_compute_report', sanitize=False, string='Rapport')

    @api.depends('period')
    def _compute_report(self):
        for rec in self:
            rec.report_html = self._build_report(int(rec.period or 28))

    def action_refresh(self):
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'view_mode': 'form', 'views': [(False, 'form')], 'target': 'current',
                'context': {'default_period': self.period}}

    # ---------------------------------------------------------------- données
    def _q(self, sql, params):
        self.env.cr.execute(sql, params)
        return self.env.cr.fetchall()

    @api.model
    def _build_report(self, days, for_email=False):
        sites = tuple(self.env['lolirine.seo.config']._target_website_ids() or [0])
        end = fields.Date.context_today(self) + timedelta(days=1)
        start = end - timedelta(days=days)
        pstart = start - timedelta(days=days)
        P = {'s': start, 'e': end, 'ps': pstart, 'w': sites}
        out = []

        # ------------------------------------------------------------ KPI
        (v, pv, conv, ca), = self._q("""
            SELECT COUNT(*) FILTER (WHERE is_landing), COUNT(*),
                   COUNT(*) FILTER (WHERE page_type='confirmation'),
                   COALESCE(SUM(amount) FILTER (WHERE page_type='confirmation'),0)
              FROM lolirine_seo_hit WHERE website_id IN %(w)s AND day >= %(s)s AND day < %(e)s""", P)
        (v0, pv0, conv0, ca0), = self._q("""
            SELECT COUNT(*) FILTER (WHERE is_landing), COUNT(*),
                   COUNT(*) FILTER (WHERE page_type='confirmation'),
                   COALESCE(SUM(amount) FILTER (WHERE page_type='confirmation'),0)
              FROM lolirine_seo_hit WHERE website_id IN %(w)s AND day >= %(ps)s AND day < %(s)s""", P)
        (org, org0), = self._q("""
            SELECT COUNT(*) FILTER (WHERE day >= %(s)s), COUNT(*) FILTER (WHERE day < %(s)s)
              FROM lolirine_seo_hit WHERE website_id IN %(w)s AND is_landing
               AND source_type='organic' AND day >= %(ps)s AND day < %(e)s""", P)
        (gclk, gimp, gpos), = self._q("""
            SELECT COALESCE(SUM(clicks),0), COALESCE(SUM(impressions),0),
                   CASE WHEN SUM(impressions)>0 THEN SUM(position_x_impr)/SUM(impressions) END
              FROM lolirine_seo_gsc_line WHERE date >= %(s)s AND date < %(e)s""", P)

        def tile(label, value, delta=''):
            return ('<td style="padding:10px 14px;background:#f0f9ff;border-radius:10px;'
                    'border:1px solid #bae6fd;vertical-align:top">'
                    '<div style="font-size:12px;color:#475569">%s</div>'
                    '<div style="font-size:22px;font-weight:700;color:#0f172a">%s</div>'
                    '<div style="font-size:12px">%s</div></td>' % (escape(label), value, delta))
        out.append('<table style="border-spacing:8px;border-collapse:separate;width:100%%"><tr>%s</tr></table>' % ''.join([
            tile('Visites', _fmt_int(v), _delta(v, v0)),
            tile('Pages vues', _fmt_int(pv), _delta(pv, pv0)),
            tile('Visites via moteurs', _fmt_int(org), _delta(org, org0)),
            tile('Commandes / CA TTC', '%s / %s €' % (_fmt_int(conv), _fmt_int(ca)), _delta(ca, ca0)),
            tile('Google : clics / impressions', '%s / %s' % (_fmt_int(gclk), _fmt_int(gimp)),
                 'position moy. %.1f' % gpos if gpos else 'Search Console non reliée'),
        ]))

        # ------------------------------------------------------- sources
        rows = self._q("""
            SELECT source_type,
                   COUNT(*) FILTER (WHERE day >= %(s)s AND is_landing),
                   COUNT(*) FILTER (WHERE day < %(s)s AND is_landing),
                   COUNT(*) FILTER (WHERE day >= %(s)s AND page_type='confirmation'),
                   COALESCE(SUM(amount) FILTER (WHERE day >= %(s)s AND page_type='confirmation'),0)
              FROM lolirine_seo_hit WHERE website_id IN %(w)s AND day >= %(ps)s AND day < %(e)s
             GROUP BY source_type ORDER BY 2 DESC""", P)
        out.append(_h('D\'où viennent les visiteurs', 'Visites = entrées sur le site ; '
                                                       'commandes attribuées à la source d\'entrée'))
        out.append(_table(['Source', 'Visites', '%', 'Évolution', 'Commandes', 'CA TTC'], [
            (escape(SRC_LABEL.get(t, t or '?')), _fmt_int(c), '%.0f %%' % (c * 100.0 / v if v else 0),
             _delta(c, c0), _fmt_int(o), '%s €' % _fmt_int(a))
            for t, c, c0, o, a in rows if c or c0]))

        # --------------------------------------------- moteurs / IA / social
        for stype, title, sub in [
            ('organic', 'Moteurs de recherche utilisés', 'Google, Bing, Ecosia, Qwant, DuckDuckGo...'),
            ('ai', 'Assistants IA', 'Visiteurs envoyés par ChatGPT, Perplexity, Gemini, Copilot...'),
            ('social', 'Réseaux sociaux', ''),
            ('referral', 'Sites référents', 'Liens depuis d\'autres sites (backlinks qui apportent des visites)'),
        ]:
            rows = self._q("""
                SELECT COALESCE(source_name,'?'),
                       COUNT(*) FILTER (WHERE day >= %(s)s), COUNT(*) FILTER (WHERE day < %(s)s)
                  FROM lolirine_seo_hit WHERE website_id IN %(w)s AND is_landing
                   AND source_type = %(t)s AND day >= %(ps)s AND day < %(e)s
                 GROUP BY 1 ORDER BY 2 DESC LIMIT 12""", dict(P, t=stype))
            rows = [r for r in rows if r[1] or r[2]]
            if rows or stype in ('organic', 'ai'):
                out.append(_h(title, sub))
                out.append(_table(['Source', 'Visites', 'Période précédente', 'Évolution'], [
                    (escape(n), _fmt_int(c), _fmt_int(c0), _delta(c, c0)) for n, c, c0 in rows]))

        # ------------------------------------------ pages d'entrée Google
        rows = self._q("""
            SELECT landing_path, COUNT(*),
                   COUNT(*) FILTER (WHERE source_name='Google'),
                   COUNT(*) FILTER (WHERE source_name<>'Google')
              FROM lolirine_seo_hit WHERE website_id IN %(w)s AND is_landing
               AND source_type='organic' AND day >= %(s)s AND day < %(e)s
             GROUP BY 1 ORDER BY 2 DESC LIMIT 15""", P)
        out.append(_h('Pages qui attirent les visiteurs des moteurs'))
        out.append(_table(['Page d\'entrée', 'Visites', 'dont Google', 'autres moteurs'], [
            (escape(p or '/'), _fmt_int(c), _fmt_int(g), _fmt_int(o)) for p, c, g, o in rows]))

        # ------------------------------------------------- requêtes Google
        rows = self._q("""
            SELECT query, SUM(clicks), SUM(impressions),
                   CASE WHEN SUM(impressions)>0 THEN SUM(position_x_impr)/SUM(impressions) END
              FROM lolirine_seo_gsc_line WHERE date >= %(s)s AND date < %(e)s AND query IS NOT NULL
             GROUP BY 1 ORDER BY 2 DESC, 3 DESC LIMIT 20""", P)
        out.append(_h('Mots-clés tapés dans Google', 'Source : Google Search Console'))
        out.append(_table(['Requête', 'Clics', 'Impressions', 'CTR', 'Position'], [
            (escape(q), _fmt_int(c), _fmt_int(i), '%.1f %%' % (c * 100.0 / i if i else 0),
             '%.1f' % (pos or 0)) for q, c, i, pos in rows]))

        rows = self._q("""
            SELECT query, page, impressions, clicks, position, kind, score
              FROM lolirine_seo_opportunity WHERE kind IN ('low_ctr','striking','page2')
             ORDER BY score DESC LIMIT 15""", {})
        kinds = dict(self.env['lolirine.seo.opportunity']._fields['kind'].selection)
        out.append(_h('Opportunités SEO prioritaires (28 j)',
                      'Requêtes où un petit effort (titre, description, contenu, liens internes) '
                      'peut rapporter le plus de clics'))
        out.append(_table(['Requête', 'Page', 'Impr.', 'Clics', 'Pos.', 'Action', '+ clics/mois'], [
            (escape(q), escape((pg or '').split('.be', 1)[-1][:60]), _fmt_int(i), _fmt_int(c),
             '%.1f' % pos, escape(kinds.get(k, k)), '%.0f' % sc)
            for q, pg, i, c, pos, k, sc in rows],
            aligns=['left', 'left', 'right', 'right', 'right', 'left', 'right']))

        # ---------------------------------------------------------- 404
        rows = self._q("""
            SELECT url, hits_human, hits_bot, COALESCE(last_bot,'') FROM lolirine_seo_notfound
             WHERE website_id IN %(w)s AND state='open' AND last_seen >= %(s)s
             ORDER BY hits_human DESC, hits_bot DESC LIMIT 10""", P)
        out.append(_h('Pages introuvables (404) à rediriger'))
        out.append(_table(['URL', 'Visiteurs', 'Robots', 'Dernier robot'], [
            (escape(u[:90]), _fmt_int(h), _fmt_int(b), escape(bn)) for u, h, b, bn in rows]))

        # -------------------------------------------------------- audit
        rows = self._q("""
            SELECT issue_type, severity, COUNT(*), COALESCE(SUM(impressions_28d),0)
              FROM lolirine_seo_issue WHERE state='open' AND website_id IN %(w)s
             GROUP BY 1,2 ORDER BY CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                      3 DESC""", P)
        types = dict(self.env['lolirine.seo.issue']._fields['issue_type'].selection)
        sev = {'high': '🔴 Élevée', 'medium': '🟠 Moyenne', 'low': '⚪ Faible'}
        out.append(_h('Audit SEO du catalogue et des pages'))
        out.append(_table(['Problème', 'Gravité', 'Éléments', 'Impressions Google concernées'], [
            (escape(types.get(t, t)), sev.get(s, s), _fmt_int(n), _fmt_int(i))
            for t, s, n, i in rows]))

        # ------------------------------------------------------ appareils
        rows = self._q("""
            SELECT device, COUNT(*) FROM lolirine_seo_hit WHERE website_id IN %(w)s AND is_landing
               AND day >= %(s)s AND day < %(e)s GROUP BY 1 ORDER BY 2 DESC""", P)
        dev = {'desktop': 'Ordinateur', 'mobile': 'Mobile', 'tablet': 'Tablette'}
        out.append(_h('Appareils'))
        out.append(_table(['Appareil', 'Visites', '%'], [
            (dev.get(d, d or '?'), _fmt_int(c), '%.0f %%' % (c * 100.0 / v if v else 0))
            for d, c in rows]))

        head = ('<div style="font-family:Arial,Helvetica,sans-serif;color:#0f172a;max-width:980px">'
                '<p style="color:#475569;margin:0 0 6px">Période du <b>%s</b> au <b>%s</b> '
                '(comparée aux %s jours précédents)</p>' % (
                    start.strftime('%d/%m/%Y'), (end - timedelta(days=1)).strftime('%d/%m/%Y'), days))
        return head + ''.join(out) + '</div>'

    # ---------------------------------------------------------- e-mail hebdo
    @api.model
    def _send_digest(self):
        cfg = self.env['lolirine.seo.config']
        to = cfg._digest_recipient()
        if not to:
            return False
        site = cfg._target_websites()[:1]
        body = ('<p>Bonjour,</p><p>Voici le rapport SEO & trafic de la semaine pour '
                '<b>%s</b>.</p>%s<p style="color:#64748b;font-size:12px">Détails dans Odoo : '
                'Site Web &gt; SEO &amp; Trafic.</p>' % (
                    escape(site.name or ''), self._build_report(7, for_email=True)))
        mail = self.env['mail.mail'].sudo().create({
            'subject': _('Rapport SEO hebdomadaire — %s') % (site.name or ''),
            'email_to': to,
            'email_from': (site.company_id.email_formatted if site else False)
                          or self.env.company.email_formatted,
            'body_html': body,
            'auto_delete': True,
        })
        mail.send()
        return True

    @api.model
    def _cron_weekly(self):
        """Lundi : audit, puis rapport hebdomadaire."""
        self.env['lolirine.seo.issue']._run_audit()
        self._send_digest()
