# Fichiers optionnels

## account_reconcile_model_views.xml

Ajoute la case a cocher « Aucune facture attendue » sur le formulaire des
modeles de rapprochement.

**Non active par defaut** : ce fichier herite de vues standard Odoo
(`account.account_reconcile_model_form`, `account.account_reconcile_model_tree`).
Si l'un de ces xmlid n'existe pas dans ta version, l'installation du module
echoue avec `ValueError: External ID not found`.

Le champ `x_no_invoice_expected` existe de toute facon : il se coche par script
(`scripts/1_configuration.py`) ou via la vue developpeur.

Pour l'activer malgre tout :

1. verifier que les xmlid existent :

       env.ref('account.account_reconcile_model_form')
       env.ref('account.account_reconcile_model_tree')

2. supprimer du fichier le `<record>` correspondant a un xmlid absent ;
3. copier le fichier dans `views/` ;
4. ajouter `'views/account_reconcile_model_views.xml'` dans le `data` du
   manifest, AVANT `views/statement_line_views.xml`.

## Compteur sur le tableau de bord

L'ancienne version du module injectait un compteur sur la carte du journal
banque via `models/account_journal.py` et `views/journal_dashboard_views.xml`.
Ces fichiers ne sont pas repris ici : ils heritent de la vue kanban standard,
donc meme risque. Ils sont recuperables dans l'historique git du depot si tu
veux les remettre une fois l'installation de base validee.
