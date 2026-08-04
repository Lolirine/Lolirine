# ═══════════════════════════════════════════════════════════════════
# Rapprochement automatique des lignes à candidate unique
# 1er passage : CONFIRME = False  → simulation, aucune écriture
# 2e  passage : CONFIRME = True   → exécution, commit ligne par ligne
# ═══════════════════════════════════════════════════════════════════
from odoo.tools import float_compare

CONFIRME = False

STL = env['account.bank.statement.line']
lines = STL.search([('is_reconciled', '=', False), ('state', '=', 'posted')],
                   order='date')

todo, ambigu = [], []
for l in lines:
    if l.x_invoice_status != 'found':
        continue
    cands = l.x_invoice_candidate_ids
    if len(cands) == 1 and float_compare(abs(cands.amount_residual),
                                         abs(l.amount), precision_digits=2) == 0:
        todo.append((l, cands))
    else:
        ambigu.append((l, cands))

print(f"══ {len(todo)} ligne(s) rapprochables sans ambiguïté ══")
for l, inv in todo:
    print(f"  {l.date} | {l.amount:>9.2f} € | {(l.partner_id.name or '-')[:22]:<22} "
          f"→ {inv.name} ({inv.partner_id.name})")
    print(f"        {(l.payment_ref or '')[:78]}")

print(f"\n══ {len(ambigu)} ligne(s) à trancher manuellement ══")
for l, cands in ambigu:
    print(f"  {l.date} | {l.amount:>9.2f} € | {len(cands)} candidate(s) : "
          f"{', '.join(cands.mapped('name')[:5])}")
    print(f"        {(l.payment_ref or '')[:78]}")

if not CONFIRME:
    print("\n▶ Simulation uniquement. Repasser avec CONFIRME = True pour exécuter.")
else:
    print("\n══ EXÉCUTION ══")
    ok = ko = 0
    for l, inv in todo:
        try:
            if l._x_link_invoice(inv):
                env.cr.commit()
                ok += 1
                print(f"  ✓ {l.date} {l.amount:>9.2f} € → {inv.name}")
            else:
                ko += 1
                print(f"  – {l.date} {l.amount:>9.2f} € : structure inattendue, ignorée")
        except Exception as e:
            env.cr.rollback()
            ko += 1
            print(f"  ✗ {l.date} {l.amount:>9.2f} € → {inv.name} : {e}")
    print(f"\n{ok} rapprochement(s) effectué(s), {ko} en échec.")
