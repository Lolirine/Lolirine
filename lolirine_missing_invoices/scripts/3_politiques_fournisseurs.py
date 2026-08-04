# ═══════════════════════════════════════════════════════════════════
# Amorçage des politiques fournisseurs — à lancer APRÈS mise à jour
# du module en 19.0.5.0.0
#
# Les fournisseurs sont recherchés par nom : ceux qui n'existent pas
# encore dans la base sont simplement signalés, sans erreur.
# ═══════════════════════════════════════════════════════════════════
P = env['res.partner']

# (nom recherché, politique, motif de libellé bancaire)
CONFIG = [
    # ── Facture attendue : à récupérer sur le portail du fournisseur ──
    ('OVH',                     'expected', 'OVHCLOUD|OVH SAS'),
    ('Anthropic',               'expected', 'ANTHROPIC|CLAUDE.AI'),
    ('OpenAi',                  'expected', 'OPENAI'),
    ('Adobe Ireland',           'expected', 'ADOBE'),
    ('GOOGLE CLOUD',            'expected', 'GOOGLE CLOUD'),
    ('Canva',                   'expected', 'CANVA'),
    ('Aftersalesnl',            'expected', 'ST PREMIE INCASSO|STICHTING PREMIE'),
    ('Starlink',                'expected', 'STARLINK'),
    ('Microsoft',               'expected', 'MICROSOFT'),
    ('Odoo',                    'expected', 'ODOO BE'),
    ('Proximus',                'expected', 'PROXIMUS'),
    ('VOO Business',            'expected', 'VOO|ORANGE BELGIUM'),
    ('Securitas',               'expected', 'SECURITAS'),
    ('Power Online',            'expected', 'POWER ONLINE'),
    ('Isabel',                  'expected', 'ISABEL'),
    ('Amazon Business',         'expected', 'AMAZON EU SARL'),
    ('Societe Wallonne des Eaux', 'expected', 'SWDE|SOCIETE WALLONNE'),
    ('Antargaz',                'expected', 'ANTARGAZ'),
    ('Baloise',                 'expected', 'BALOISE'),
    ('Comfisgest',              'expected', 'COMFISGEST'),

    # ── Jamais de facture : ticket de caisse, frais, prélèvements ──
    ('CBC Banque',              'none',     None),
    ('DeBe Services',           'none',     'TOTAL NB'),
    ('BricoPlanit',             'none',     'BRICO'),
    ('Bpost',                   'none',     'BPOST|N&D 23'),
    ('EG Retail',               'none',     None),
]

print("══ CONFIGURATION DES FOURNISSEURS ══")
for nom, policy, label in CONFIG:
    p = P.search([('name', 'ilike', nom), ('supplier_rank', '>', 0)], limit=1)
    if not p:
        p = P.search([('name', 'ilike', nom)], limit=1)
    if not p:
        print(f"  ? {nom:<28} introuvable")
        continue
    vals = {'x_invoice_policy': policy}
    if label:
        vals['x_bank_label'] = label
    p.write(vals)
    print(f"  ✓ {p.name[:28]:<28} {policy:<9} {label or ''}")

env.cr.commit()

# ── Contrôle ──
from collections import Counter
STL = env['account.bank.statement.line']
lines = STL.search([('is_reconciled', '=', False), ('state', '=', 'posted')])
print(f"\n{len(lines)} lignes non rapprochées :",
      dict(Counter(l.x_invoice_status for l in lines)))

prio = lines.filtered(lambda l: l.x_invoice_priority)
print(f"\n══ {len(prio)} FACTURE(S) À RÉCLAMER ══")
for l in prio.sorted('date', reverse=True):
    print(f"  {l.date} | {l.amount:>9.2f} € | "
          f"{(l.x_expected_partner_id.name or '?')[:24]:<24} | "
          f"{(l.payment_ref or '')[:46]}")

reste = lines.filtered(
    lambda l: l.x_invoice_status == 'missing' and not l.x_invoice_priority)
print(f"\n══ {len(reste)} LIGNE(S) EN 'MISSING' SANS FOURNISSEUR IDENTIFIÉ ══")
for l in reste.sorted('date', reverse=True):
    print(f"  {l.date} | {l.amount:>9.2f} € | {(l.payment_ref or '')[:62]}")
