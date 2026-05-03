# -*- coding: utf-8 -*-
"""Patch du modèle storage.indexation.line pour améliorer l'affichage
dans les champs Many2one (notamment dans le wizard d'envoi).

Sans ce patch, Odoo affiche 'storage.indexation.line,123' au lieu d'un
nom lisible. On surcharge _compute_display_name pour afficher quelque
chose comme 'CARPENTIER Ludwine — Box 1D26 (61.51€)'.
"""

from odoo import models, api


class StorageIndexationLine(models.Model):
    _inherit = 'storage.indexation.line'

    @api.depends('partner_id', 'product_id', 'new_price', 'subscription_id')
    def _compute_display_name(self):
        """Affichage lisible : 'CLIENT — Box (NOUVEAU PRIX €)'"""
        for line in self:
            parts = []

            # Nom du client
            if line.partner_id:
                parts.append(line.partner_id.name or '?')
            else:
                parts.append('(sans client)')

            # Box / produit
            if line.product_id:
                # Utilise le default_code (ex "1D26") s'il existe, sinon le nom
                code = line.product_id.default_code
                if code:
                    parts.append(f"Box {code}")
                else:
                    # Tronque le nom du produit s'il est trop long
                    name = line.product_id.name or ''
                    if len(name) > 40:
                        name = name[:37] + '...'
                    parts.append(name)

            # Nouveau prix
            try:
                if line.new_price:
                    parts.append(f"({line.new_price:.2f}€)")
            except Exception:
                pass

            line.display_name = ' — '.join(parts) if parts else f"Ligne #{line.id}"
