import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class VapidSetupWizard(models.TransientModel):
    _name = 'lolirine.vapid.setup.wizard'
    _description = 'Assistant de génération des clés VAPID'

    vapid_public_key  = fields.Char(string='Clé publique VAPID', readonly=True)
    vapid_private_key = fields.Char(string='Clé privée VAPID', readonly=True)
    vapid_email       = fields.Char(
        string='Email de contact VAPID',
        default='admin@lolirine.be',
        required=True,
    )
    state = fields.Selection([
        ('init', 'Initialisation'),
        ('generated', 'Clés générées'),
        ('saved', 'Sauvegardé'),
    ], default='init', string='État')

    info_text = fields.Text(
        string='Information',
        readonly=True,
        default=(
            "Cet assistant va générer une paire de clés VAPID nécessaires "
            "pour les Web Push Notifications.\n\n"
            "Les clés sont propres à votre instance Odoo. "
            "Ne partagez jamais la clé privée.\n\n"
            "Prérequis : le paquet Python 'pywebpush' doit être installé "
            "(ajoutez-le dans requirements.txt sur Odoo.sh)."
        )
    )

    def action_generate_keys(self):
        """Génère une paire de clés VAPID via py_vapid."""
        try:
            from py_vapid import Vapid
        except ImportError:
            try:
                from pywebpush import Vapid
            except ImportError:
                raise UserError(_(
                    "Le paquet 'pywebpush' n'est pas installé.\n"
                    "Ajoutez 'pywebpush' dans votre fichier requirements.txt "
                    "et redéployez sur Odoo.sh."
                ))

        try:
            vapid = Vapid()
            vapid.generate_keys()
            public_key  = vapid.public_key_urlsafe_base64
            private_key = vapid.private_key_urlsafe_base64

            self.write({
                'vapid_public_key':  public_key,
                'vapid_private_key': private_key,
                'state': 'generated',
            })
        except Exception as e:
            _logger.error("VAPID key generation error: %s", e)
            raise UserError(_(
                "Erreur lors de la génération des clés VAPID : %s", str(e)
            ))

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('lolirine_storage_notify.view_vapid_setup_wizard_form').id,
            'target': 'new',
        }

    def action_save_keys(self):
        """Sauvegarde les clés VAPID dans ir.config_parameter."""
        if not self.vapid_public_key or not self.vapid_private_key:
            raise UserError(_("Veuillez d'abord générer les clés VAPID."))

        cfg = self.env['lolirine.notify.config'].sudo().get_config()
        cfg.write({
            'vapid_public_key':  self.vapid_public_key,
            'vapid_private_key': self.vapid_private_key,
            'vapid_email':       self.vapid_email,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Clés VAPID sauvegardées'),
                'message': _(
                    'Les clés VAPID ont été enregistrées. '
                    'Rechargez le backend pour activer les Web Push.'
                ),
                'type': 'success',
                'sticky': False,
            },
        }
