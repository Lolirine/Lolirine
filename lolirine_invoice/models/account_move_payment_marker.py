from odoo import models, fields, api


class AccountMovePaymentMarker(models.Model):
    _inherit = 'account.move'

    lolirine_payment_override = fields.Selection(
        selection=[
            ('auto', "Hériter du fournisseur"),
            ('manual', "Forcer paiement manuel"),
            ('automatic', "Forcer paiement automatique"),
        ],
        string="Mode de paiement",
        default='auto',
        help="Surcharge le mode de paiement par défaut du fournisseur pour cette "
             "facture. 'Hériter' utilise le réglage du fournisseur, 'Forcer manuel' "
             "active l'alerte même si le fournisseur est en domiciliation, "
             "'Forcer automatique' désactive l'alerte même si le fournisseur "
             "est marqué en paiement manuel.",
    )

    lolirine_manual_payment = fields.Boolean(
        string="Paiement manuel",
        compute='_compute_lolirine_manual_payment',
        store=True,
        help="Calculé : True si cette facture nécessite un paiement manuel "
             "(virement à effectuer).",
    )

    @api.depends('partner_id.lolirine_manual_payment', 'lolirine_payment_override')
    def _compute_lolirine_manual_payment(self):
        for move in self:
            override = move.lolirine_payment_override
            if override == 'manual':
                move.lolirine_manual_payment = True
            elif override == 'automatic':
                move.lolirine_manual_payment = False
            else:  # 'auto' (par défaut) ou False
                move.lolirine_manual_payment = move.partner_id.lolirine_manual_payment
