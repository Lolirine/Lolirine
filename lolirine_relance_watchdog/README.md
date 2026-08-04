# Lolirine - Surveillance des relances

Module Odoo 19 pour Lolirine SRL (garde-meubles).

## Objectif

Ce module **ne relance jamais un client**. Il marque les factures dont le suivi
est incoherent, pour eviter qu'une creance reste des mois sans action puis
declenche brutalement une mise en demeure assortie de frais.

## Signaux detectes

| Motif affiche | Signification |
|---|---|
| `aucune relance depuis l'echeance (N j de retard)` | La facture est echue mais aucun courrier de rappel n'est parti depuis |
| `suivi client en manuel` | Le client a ete sorti du circuit automatique et n'a jamais ete repris |
| `abonnement encore actif` | Le client loue toujours alors qu'une facture reste impayee |
| `facture de frais impayee` | Une facture de frais de relance est elle-meme impayee (risque de frais sur frais) |

## Installation

1. Copier le dossier `lolirine_relance_watchdog` dans le repertoire des addons
2. Pousser sur GitHub, attendre le rebuild Odoo.sh
3. Applications > Mettre a jour la liste > installer "Lolirine - Surveillance des relances"

## Amorcage

Le cron tourne chaque jour a 07h00. Pour un premier calcul immediat :

```python
env['account.move']._cron_lolirine_relance_watchdog()
env.cr.commit()
res = env['account.move'].search([('lolirine_relance_alert', '=', True)])
for m in res:
    print(m.name, m.partner_id.name, m.amount_residual, '|', m.lolirine_relance_msg)
```

## Reglage

Parametre systeme `lolirine_relance.alert_days` (defaut : 10 jours de retard).
Le monter a 15 si le premier passage produit trop de lignes.

## Ou regarder

- Banniere orange en haut de la fiche facture
- Colonne "Motif d'alerte" dans la liste des factures
- Filtre "Relances oubliees" dans la recherche
- Menu Comptabilite > Clients > Relances oubliees
- Action groupee "Verifier la coherence des relances" depuis la liste
