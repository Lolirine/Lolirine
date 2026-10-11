import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.readonly
    @api.model
    def render_public_asset(self, template, values=None):
        """Ajoute les aperçus des blocs Lolirine à la liste des blocs du constructeur."""
        if template == 'website.snippets':
            values = dict(values or {})
            try:
                values['pu_previews'] = self.env['website']._lolirine_snippet_previews()
            except Exception:
                _logger.exception("Lolirine : aperçus des blocs indisponibles")
                values['pu_previews'] = {}
        return super().render_public_asset(template, values=values)
