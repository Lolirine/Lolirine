"""Promesse de livraison du Pool Store : jours ouvrables belges, heure limite,
délai fournisseur (dropshipping) et seuil de livraison offerte."""
from datetime import date, datetime, timedelta

import pytz

from odoo import api, models

P = 'lolirine_pool_buypanel.'
JOURS = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.']
MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']


def _paques(annee):
    """Dimanche de Pâques (algorithme de Meeus/Jones/Butcher)."""
    a, b, c = annee % 19, annee // 100, annee % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois = (h + l - 7 * m + 114) // 31
    jour = ((h + l - 7 * m + 114) % 31) + 1
    return date(annee, mois, jour)


def jours_feries_be(annee):
    p = _paques(annee)
    return {
        date(annee, 1, 1), p + timedelta(days=1), date(annee, 5, 1), p + timedelta(days=39),
        p + timedelta(days=50), date(annee, 7, 21), date(annee, 8, 15), date(annee, 11, 1),
        date(annee, 11, 11), date(annee, 12, 25),
    }


def est_ouvrable(d):
    return d.weekday() < 5 and d not in jours_feries_be(d.year)


def ajouter_ouvrables(d, n):
    while n > 0:
        d += timedelta(days=1)
        if est_ouvrable(d):
            n -= 1
    return d


def fmt_jour(d):
    return '%s %s %s' % (JOURS[d.weekday()], d.day, MOIS[d.month - 1])


class LolirineLivraison(models.AbstractModel):
    _name = 'lolirine.livraison'
    _description = 'Promesse de livraison Pool Store'

    @api.model
    def _param(self, key, default):
        val = self.env['ir.config_parameter'].sudo().get_param(P + key)
        try:
            return type(default)(val) if val not in (None, '', False) else default
        except (TypeError, ValueError):
            return default

    @api.model
    def delai_fournisseur(self, tmpl):
        """Délai (jours ouvrables) du fournisseur le plus rapide, sinon défaut."""
        delais = []
        if 'dropship_supplier_ids' in tmpl._fields:
            delais = [s.delay for s in tmpl.dropship_supplier_ids if s.is_active and (s.delay or 0) > 0]
        if not delais:
            delais = [s.delay for s in tmpl.seller_ids if (s.delay or 0) > 0]
        return min(delais) if delais else self._param('delai_defaut', 3)

    @api.model
    def promesse(self, delai_min, marge=None, maintenant=None):
        """Dates de livraison et compte à rebours avant l'heure limite (heure de Bruxelles)."""
        marge = self._param('marge_jours', 2) if marge is None else marge
        heure_limite = self._param('heure_limite', 14)
        tz = pytz.timezone('Europe/Brussels')
        maintenant = maintenant or datetime.now(pytz.utc).astimezone(tz)
        aujourdhui = maintenant.date()
        avant_limite = est_ouvrable(aujourdhui) and maintenant.hour < heure_limite
        depart = aujourdhui if avant_limite else ajouter_ouvrables(aujourdhui, 1)
        d_min = ajouter_ouvrables(depart, delai_min)
        d_max = ajouter_ouvrables(d_min, marge)
        minutes = 0
        if avant_limite:
            limite = maintenant.replace(hour=heure_limite, minute=0, second=0, microsecond=0)
            minutes = int((limite - maintenant).total_seconds() // 60)
        if d_min == d_max:
            texte = fmt_jour(d_min)
        elif d_min.month == d_max.month:
            texte = 'entre le %s %s et le %s' % (JOURS[d_min.weekday()], d_min.day, fmt_jour(d_max))
        else:
            texte = 'entre le %s et le %s' % (fmt_jour(d_min), fmt_jour(d_max))
        compte = ''
        if minutes > 0:
            h, m = divmod(minutes, 60)
            compte = ('%d h %02d min' % (h, m)) if h else ('%d min' % m)
        return {'min': d_min, 'max': d_max, 'texte': texte, 'compte_a_rebours': compte,
                'expedition': depart}

    @api.model
    def seuil_franco(self, website=None):
        """(montant, base) : base 'ht' ou 'ttc'. Priorité à la règle « gratuit au-delà de »
        d'un mode de livraison publié du site, sinon le paramètre (HT)."""
        website = website or self.env['website'].get_current_website()
        if 'delivery.carrier' not in self.env:
            return self._param('franco_ht', 499.0), 'ht'
        Carrier = self.env['delivery.carrier'].sudo()
        dom = [('free_over', '=', True), ('amount', '>', 0), ('is_published', '=', True)]
        if 'website_id' in Carrier._fields and website:
            dom += ['|', ('website_id', '=', False), ('website_id', '=', website.id)]
        carrier = Carrier.search(dom, order='amount', limit=1)
        if carrier:
            return carrier.amount, 'ttc'
        return self._param('franco_ht', 499.0), 'ht'
