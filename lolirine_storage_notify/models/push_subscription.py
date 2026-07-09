from odoo import models, fields, api


class LolirineStoragePushSubscription(models.Model):
    _name = 'lolirine.push.subscription'
    _description = 'Web Push Subscription (abonnements navigateur)'
    _order = 'create_date desc'

    user_id = fields.Many2one(
        'res.users', string='Utilisateur',
        required=True, ondelete='cascade', index=True,
    )
    partner_id = fields.Many2one(
        'res.partner', related='user_id.partner_id', store=True, string='Partenaire',
    )
    endpoint = fields.Char(string='Endpoint', required=True)
    p256dh    = fields.Char(string='Clé p256dh', required=True)
    auth      = fields.Char(string='Clé auth', required=True)
    user_agent = fields.Char(string='Navigateur / Appareil')
    active     = fields.Boolean(default=True, string='Actif')
    last_push  = fields.Datetime(string='Dernier push envoyé')
    last_seen  = fields.Datetime(string='Dernière activité')

    _endpoint_uniq = models.Constraint(
        'unique(endpoint)',
        "Un abonnement identique existe déjà.",
    )

    @api.model
    def register(self, endpoint, p256dh, auth, user_agent=None):
        """
        Appelé par le JS frontend pour enregistrer ou rafraîchir un abonnement.
        Retourne l'ID de l'abonnement.
        """
        existing = self.sudo().search([('endpoint', '=', endpoint)], limit=1)
        vals = {
            'endpoint': endpoint,
            'p256dh': p256dh,
            'auth': auth,
            'user_agent': user_agent or '',
            'last_seen': fields.Datetime.now(),
            'active': True,
        }
        if existing:
            existing.sudo().write(vals)
            return existing.id
        else:
            vals['user_id'] = self.env.user.id
            return self.sudo().create(vals).id

    @api.model
    def unregister(self, endpoint):
        """Désactive un abonnement révoqué par l'utilisateur."""
        rec = self.sudo().search([('endpoint', '=', endpoint)], limit=1)
        if rec:
            rec.active = False
        return True
