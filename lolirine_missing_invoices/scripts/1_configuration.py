# ═══════════════════════════════════════════════════════════════════
# À lancer dans odoo shell APRÈS mise à jour du module
#   (le champ x_no_invoice_expected doit exister)
# ═══════════════════════════════════════════════════════════════════
RM = env['account.reconcile.model']

# ── Modèles dont les transactions n'ont jamais de facture ──
#  8 Virements internes            25 Virements internes (regex)
#  9 Escompte                      26/36 TVA compte courant
# 10 Frais bancaires               28 Cautions clients reçues
# 11/12 Payouts Stripe             37 Assurance solde restant dû
# 14 Honesty loyer appartement     38-44 Crédits CBC (jeu complet)
# 45 Avances C/C administrateurs
SANS_FACTURE = [8, 9, 10, 11, 12, 14, 25, 26, 28, 36, 37,
                38, 39, 40, 41, 42, 43, 44, 45]

# NON marqués volontairement : 15 (Claude.ai), 17 (Canva), 46 (Mastercard),
# 47 (Cofeo) — fournisseurs étrangers hors Peppol, donc précisément les
# factures que le rapport doit continuer à réclamer.

RM.browse(SANS_FACTURE).write({'x_no_invoice_expected': True})
print(f"✓ {len(SANS_FACTURE)} modèles marqués « aucune facture attendue »")

# ── Anciens modèles crédit (incomplets, doublonnés par 38-44) → archivage ──
anciens = RM.browse([18, 20, 22, 23, 24])
anciens.write({'active': False})
print(f"✓ {len(anciens)} anciens modèles CBC archivés")

# ── Motifs libres complémentaires ──
env['ir.config_parameter'].sudo().set_param(
    'lolirine_missing_invoices.no_invoice_labels',
    "Imputation frais Gestion dossier de crédit\n"
    "PAIEMENT CRÉDIT D'INVESTISSEMENT\n"
    "COTISATION CARTE\n"
    "INTÉRÊTS DÉBITEURS\n"
    "REMBOURSEMENT CAUTION"
)
print("✓ motifs libres enregistrés")

env.cr.commit()

# ── Contrôle immédiat de la nouvelle répartition ──
from collections import Counter
STL = env['account.bank.statement.line']
lines = STL.search([('is_reconciled', '=', False), ('state', '=', 'posted')])
print(f"\n{len(lines)} lignes non rapprochées :")
for statut, n in Counter(l.x_invoice_status for l in lines).most_common():
    print(f"   {statut:<12} {n:>4}")

print("\n── Ce qui reste en 'missing' ──")
for l in lines.filtered(lambda x: x.x_invoice_status == 'missing').sorted('date'):
    print(f"  {l.date} | {l.amount:>10.2f} € | {(l.payment_ref or '')[:70]}")
