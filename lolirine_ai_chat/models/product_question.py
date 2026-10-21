import logging
import re

import requests
from lxml import html as lxml_html

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

API_URL = 'https://api.anthropic.com/v1/messages'
P = 'lolirine_ai_chat.'

CONSIGNE = (
    "Tu rédiges, pour Lolirine Pool Store (Boninne, Belgique), la réponse publique à une question posée "
    "par un visiteur sous une fiche produit. Un membre de l'équipe relira avant publication.\n"
    "Règles :\n"
    "- Réponds dans la langue de la question, en 1 à 4 phrases, ton aimable et précis, sans formule de politesse.\n"
    "- Appuie-toi uniquement sur la FICHE PRODUIT et le CONTENU DU SITE fournis. N'invente jamais une "
    "caractéristique, une compatibilité, un délai, un stock ou un prix.\n"
    "- Si l'information manque, commence la réponse par « [À VÉRIFIER] » puis propose une réponse prudente "
    "(par exemple : « Nous vérifions auprès du fabricant et revenons vers vous »).\n"
    "- Ne cite aucun autre vendeur. Pas de liens sauf ceux de la fiche.\n"
    "- Réponds uniquement par le texte de la réponse."
)


def texte_brut(html_ou_texte, limite=3000):
    if not html_ou_texte:
        return ''
    try:
        txt = lxml_html.fromstring(str(html_ou_texte)).text_content()
    except Exception:
        txt = str(html_ou_texte)
    return re.sub(r'\s+', ' ', txt).strip()[:limite]


class ProductQuestion(models.Model):
    """Questions des visiteurs sur une fiche produit, réponse préparée par l'IA puis validée."""
    _name = 'lolirine.product.question'
    _description = 'Question sur un produit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'question'

    product_tmpl_id = fields.Many2one('product.template', string='Produit', required=True, ondelete='cascade',
                                      index=True)
    website_id = fields.Many2one('website', string='Site web')
    question = fields.Text(string='Question', required=True, tracking=True)
    auteur = fields.Char(string='Prénom affiché')
    email = fields.Char(string='E-mail (non publié)')
    partner_id = fields.Many2one('res.partner', string='Client')
    lang = fields.Char(string='Langue')
    state = fields.Selection([
        ('nouvelle', 'Nouvelle'),
        ('brouillon', 'Réponse IA prête'),
        ('publiee', 'Publiée'),
        ('refusee', 'Refusée'),
    ], string='État', default='nouvelle', required=True, tracking=True, index=True)
    reponse_ia = fields.Text(string='Proposition de l\'IA', readonly=True)
    a_verifier = fields.Boolean(string='À vérifier', readonly=True,
                                help="L'IA n'a pas trouvé l'information dans la fiche : relisez avant de publier.")
    reponse = fields.Text(string='Réponse publiée', tracking=True,
                          help="Vide = la proposition de l'IA est publiée telle quelle.")
    date_reponse = fields.Datetime(string='Répondu le', readonly=True)
    votes_utiles = fields.Integer(string='Votes « utile »', default=0)
    knowledge_id = fields.Many2one('ai.chat.knowledge', string='Fiche du chatbot', readonly=True, ondelete='set null')
    erreur_ia = fields.Char(string='Erreur IA', readonly=True)

    # ------------------------------------------------------------------ création
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            rec._planifier_activite()
        return recs

    def _responsable(self):
        self.ensure_one()
        user = self.website_id.salesperson_id if self.website_id else False
        if not user:
            user = self.env.ref('base.user_admin', raise_if_not_found=False)
        return user

    def _planifier_activite(self):
        user = self._responsable()
        if not user:
            return
        self.activity_schedule(
            'mail.mail_activity_data_todo', user_id=user.id,
            summary=_("Question sur %s", self.product_tmpl_id.name),
            note=self.question)

    # ------------------------------------------------------------------ brouillon IA
    def _param(self, key, default=''):
        return self.env['ir.config_parameter'].sudo().get_param(P + key, default)

    def _contexte_produit(self):
        self.ensure_one()
        t = self.product_tmpl_id.sudo()
        lignes = ['FICHE PRODUIT', 'Nom : %s' % t.name]
        if t.default_code:
            lignes.append('Référence : %s' % t.default_code)
        if t.website_url:
            lignes.append('Lien : %s' % t.website_url)
        if t.public_categ_ids:
            lignes.append('Catégories : %s' % ', '.join(t.public_categ_ids.mapped('display_name')))
        for ligne in t.attribute_line_ids:
            lignes.append('%s : %s' % (ligne.attribute_id.name, ', '.join(ligne.value_ids.mapped('name'))))
        for champ in ('description_ecommerce', 'description_sale', 'website_description'):
            if champ in t._fields and t[champ]:
                lignes.append(texte_brut(t[champ]))
        anciennes = self.search([('product_tmpl_id', '=', t.id), ('state', '=', 'publiee'), ('id', '!=', self.id)],
                                limit=8)
        if anciennes:
            lignes.append('\nQUESTIONS DÉJÀ PUBLIÉES SUR CE PRODUIT')
            for q in anciennes:
                lignes.append('Q : %s\nR : %s' % (q.question, q.reponse or q.reponse_ia))
        Know = self.env.get('ai.chat.knowledge')
        if Know is not None:
            essentiels, pertinentes = Know.sudo().chercher(
                '%s %s' % (t.name, self.question), website_id=self.website_id.id or None, limite=3)
            if essentiels or pertinentes:
                lignes.append('\nCONTENU DU SITE')
                for k in essentiels | pertinentes:
                    lignes.append('### %s\n%s' % (k.name, (k.content or '')[:1200]))
        return '\n'.join(lignes)[:12000]

    def _generer_brouillon(self):
        api_key = self._param('api_key')
        if not api_key:
            raise UserError(_("Clé API de l'assistant IA non configurée."))
        from ..controllers.main import MODELE_DEFAUT, MODELES_RETIRES
        modele = self._param('model', MODELE_DEFAUT) or MODELE_DEFAUT
        modele = MODELES_RETIRES.get(modele, modele)
        for rec in self:
            try:
                resp = requests.post(API_URL, timeout=60, headers={
                    'Content-Type': 'application/json', 'x-api-key': api_key, 'anthropic-version': '2023-06-01',
                }, json={
                    'model': modele, 'max_tokens': 500, 'system': CONSIGNE,
                    'messages': [{'role': 'user', 'content': '%s\n\nQUESTION DU VISITEUR :\n%s' % (
                        rec._contexte_produit(), rec.question)}],
                })
                data = resp.json()
                if resp.status_code != 200:
                    raise ValueError(str(data.get('error', data))[:200])
                texte = '\n'.join(b['text'] for b in data.get('content', []) if b.get('type') == 'text').strip()
            except Exception as e:
                _logger.warning('Question produit %s : brouillon IA impossible (%s)', rec.id, e)
                rec.erreur_ia = str(e)[:250]
                continue
            a_verifier = texte.startswith('[À VÉRIFIER]')
            rec.write({
                'reponse_ia': texte.replace('[À VÉRIFIER]', '').strip(),
                'a_verifier': a_verifier,
                'erreur_ia': False,
                'state': 'brouillon' if rec.state == 'nouvelle' else rec.state,
            })
        return True

    def action_generer_brouillon(self):
        self._generer_brouillon()
        return True

    @api.model
    def _cron_brouillons(self):
        nouvelles = self.search([('state', '=', 'nouvelle'), ('erreur_ia', '=', False)], limit=20)
        if nouvelles and self._param('api_key'):
            nouvelles._generer_brouillon()
            self.env.cr.commit()

    # ------------------------------------------------------------------ publication
    def action_publier(self):
        for rec in self:
            texte = (rec.reponse or rec.reponse_ia or '').strip()
            if not texte:
                raise UserError(_("Écrivez une réponse (ou générez la proposition de l'IA) avant de publier."))
            rec.write({'reponse': texte, 'state': 'publiee', 'date_reponse': fields.Datetime.now()})
            rec._alimenter_chatbot()
            rec.activity_ids.action_feedback(feedback=_("Réponse publiée."))
            rec._prevenir_auteur()
        return True

    def action_refuser(self):
        self.write({'state': 'refusee'})
        self.activity_ids.action_feedback(feedback=_("Question refusée."))
        self.knowledge_id.write({'active': False})
        return True

    def action_remettre(self):
        for rec in self:
            rec.state = 'brouillon' if rec.reponse_ia else 'nouvelle'
        self.knowledge_id.write({'active': False})
        return True

    def _alimenter_chatbot(self):
        """Chaque réponse publiée devient une fiche « Question / réponse » de la base du chatbot."""
        Know = self.env.get('ai.chat.knowledge')
        if Know is None:
            return
        for rec in self:
            t = rec.product_tmpl_id
            vals = {
                'name': '%s — %s' % (t.name, rec.question[:120]),
                'kind': 'faq',
                'url': t.website_url or False,
                'content': 'Produit : %s\nQuestion : %s\nRéponse : %s' % (t.name, rec.question, rec.reponse),
                'keywords': ' '.join(filter(None, [t.name, t.default_code])),
                'manual': True,
                'website_id': rec.website_id.id or False,
                'active': True,
            }
            if rec.knowledge_id:
                rec.knowledge_id.sudo().write(vals)
            else:
                rec.knowledge_id = Know.sudo().create(vals)

    def _prevenir_auteur(self):
        modele = self.env.ref('lolirine_ai_chat.mail_question_repondue', raise_if_not_found=False)
        if not modele:
            return
        for rec in self.filtered('email'):
            modele.sudo().send_mail(rec.id, force_send=False)
