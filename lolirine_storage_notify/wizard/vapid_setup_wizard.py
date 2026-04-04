import base64
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class VapidSetupWizard(models.TransientModel):
    _name = 'lolirine.vapid.setup.wizard'
    _description = 'Assistant de génération des clés VAPID'

    vapid_public_key  = fields.Char(string='Clé publique VAPID', readonly=True)
    vapid_private_key = fields.Char(string='Clé privée VAPID', readonly=True)
    vapid_email = fields.Char(
        string='Email de contact VAPID',
        default='admin@lolirine.be',
        required=True,
    )
    state = fields.Selection([
        ('init', 'Initialisation'),
        ('generated', 'Clés générées'),
        ('saved', 'Sauvegardé'),
    ], default='init', string='État')

    def action_generate_keys(self):
        """
        Génère une paire de clés VAPID (ECDH P-256) via la librairie
        'cryptography' (toujours disponible dans Odoo), sans dépendre
        de l'API interne de pywebpush qui change selon les versions.
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import serialization
        except ImportError:
            raise UserError(_(
                "La librairie 'cryptography' n'est pas disponible. "
                "Elle est normalement incluse avec Odoo."
            ))

        try:
            # Génération de la clé privée ECDH P-256 (courbe requise par VAPID)
            private_key = ec.generate_private_key(ec.SECP256R1())
            public_key  = private_key.public_key()

            # Clé privée → bytes bruts → base64url sans padding
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )
            private_b64 = base64.urlsafe_b64encode(private_bytes).rstrip(b'=').decode('utf-8')

            # Clé publique → format non-compressé (04 + X + Y) → base64url sans padding
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint,
            )
            public_b64 = base64.urlsafe_b64encode(public_bytes).rstrip(b'=').decode('utf-8')

            self.write({
                'vapid_public_key':  public_b64,
                'vapid_private_key': private_b64,
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
            'view_id': self.env.ref(
                'lolirine_storage_notify.view_vapid_setup_wizard_form'
            ).id,
            'target': 'new',
        }

    def action_save_keys(self):
        """Sauvegarde les clés VAPID dans lolirine.notify.config."""
        if not self.vapid_public_key or not self.vapid_private_key:
            raise UserError(_("Veuillez d'abord générer les clés VAPID."))

        cfg = self.env['lolirine.notify.config'].sudo().get_config()
        cfg.write({
            'vapid_public_key':  self.vapid_public_key,
            'vapid_private_key': self.vapid_private_key,
            'vapid_email':       self.vapid_email,
        })

        self.state = 'saved'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Clés VAPID sauvegardées'),
                'message': _(
                    'Les clés ont été enregistrées. '
                    'Rechargez le backend pour activer les Web Push.'
                ),
                'type': 'success',
                'sticky': False,
            },
        }
