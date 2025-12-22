# Rapport d'Analyse - Migration Odoo 18 → 19
## Modules Lolirine SPRL

**Date d'analyse** : 21 décembre 2025  
**Analyste** : Claude (Anthropic)  
**Version source** : Odoo 18.0  
**Version cible** : Odoo 19.0  

---

## Résumé Exécutif

✅ **Bonne nouvelle !** Tes modules sont **très bien codés** et nécessitent **très peu de modifications** pour être compatibles Odoo 19.

| Catégorie | Statut |
|-----------|--------|
| Méthodes dépréciées | ✅ 1 seule correction appliquée |
| Syntaxe XML | ✅ Compatible |
| API ORM | ✅ Compatible |
| Dépendances | ✅ Modules standard Odoo |

---

## Modules Analysés (9)

| Module | Version 18 | Version 19 | Statut |
|--------|------------|------------|--------|
| `act365_integration` | 18.0.1.0.0 | 19.0.1.0.0 | ✅ Prêt |
| `km_expense` | 18.0.1.0.0 | 19.0.1.0.0 | ✅ Corrigé |
| `lolirine_contract` | 18.0.1.3.0 | 19.0.1.3.0 | ✅ Prêt |
| `lolirine_invoice` | 18.0.1.4.0 | 19.0.1.4.0 | ✅ Prêt |
| `lolirine_scan_tva` | 18.0.1.1.0 | 19.0.1.1.0 | ✅ Prêt |
| `lolirine_scan_tva_documents` | 18.0.1.0.0 | 19.0.1.0.0 | ✅ Prêt |
| `lolirine_storage_availability` | 18.0.1.0.0 | 19.0.1.0.0 | ✅ Prêt |
| `storage_indexation` | 18.0.1.0.0 | 19.0.1.0.0 | ✅ Prêt |
| `storage_plan_module` | 1.0.66 | 19.0.1.0.66 | ✅ Prêt |

---

## Corrections Appliquées

### 1. Code Python

#### km_expense/models/km_trajet.py (ligne 461)

**Problème** : Utilisation de `self._context` qui est déprécié en Odoo 19.

```python
# AVANT (Odoo 18)
if self.bareme_id and not self._context.get('skip_taux_update'):

# APRÈS (Odoo 19)
if self.bareme_id and not self.env.context.get('skip_taux_update'):
```

**Raison** : En Odoo 19, `record._cr`, `record._context`, et `record._uid` sont dépréciés. Il faut utiliser `self.env.cr`, `self.env.context`, et `self.env.uid` respectivement.

### 2. Versions des Manifests

Toutes les versions ont été mises à jour de `18.0.x.x.x` vers `19.0.x.x.x` dans les fichiers `__manifest__.py`.

### 3. Scripts de Migration

Des scripts `post-migrate.py` ont été créés dans chaque module :
```
module/migrations/19.0.1.0.0/post-migrate.py
```

---

## Vérifications Effectuées (Aucun Problème)

| Vérification | Résultat |
|--------------|----------|
| `name_get()` (déprécié) | ✅ Non utilisé |
| `read_group()` (utiliser `_read_group`) | ✅ Non utilisé |
| `@api.multi` / `@api.one` (supprimés) | ✅ Non utilisé |
| `fields_view_get()` (déprécié) | ✅ Non utilisé |
| `group_operator` (renommé `aggregator`) | ✅ Non utilisé |
| `odoo.osv` (déprécié) | ✅ Non utilisé |
| `inselect` (supprimé) | ✅ Non utilisé |
| `_flush_search()` (déprécié) | ✅ Non utilisé |
| Syntaxe XML `tree` vs `list` | ✅ Compatible (les deux fonctionnent) |

---

## Dépendances des Modules

Tous les modules dépendent de modules standard Odoo qui existent en version 19 :

- `base` ✅
- `account` ✅
- `sale` ✅
- `sale_subscription` ✅
- `mail` ✅
- `contacts` ✅
- `portal` ✅
- `website` ✅
- `website_sale` ✅
- `website_appointment` ✅
- `product` ✅
- `hr` ✅
- `hr_expense` ✅
- `fleet` ✅
- `calendar` ✅
- `base_vat` ✅
- `documents` ✅
- `web` ✅

---

## Instructions pour Odoo.sh

### Étape 1 : Préparer la branche

1. Crée une nouvelle branche pour la migration (ex: `migration-19`)
2. Remplace les modules par les versions corrigées (ce ZIP)

### Étape 2 : Commit et Push

```bash
git checkout -b migration-19
# Copier les modules corrigés
git add .
git commit -m "Migration Odoo 18 → 19 : Modules Lolirine"
git push origin migration-19
```

### Étape 3 : Sur Odoo.sh

1. Va dans ton projet Odoo.sh
2. Configure la branche `migration-19` comme branche de staging
3. Odoo.sh va automatiquement :
   - Exécuter le service d'upgrade sur ta base de données
   - Appliquer les scripts de migration de tes modules custom
   - Te fournir une base de données de test

### Étape 4 : Test

1. Teste toutes les fonctionnalités de chaque module
2. Vérifie les logs pour tout message d'erreur
3. Valide les données migrées

### Étape 5 : Production

Une fois les tests validés :
1. Fusionne la branche en production
2. Odoo.sh effectuera la migration finale

---

## Points d'Attention pour les Tests

### Module km_expense
- [ ] Tester la création de trajets avec différents barèmes
- [ ] Vérifier que le contexte `skip_taux_update` fonctionne toujours

### Module act365_integration
- [ ] Tester la synchronisation avec ACT365
- [ ] Vérifier l'attribution des codes PIN

### Module lolirine_scan_tva
- [ ] Tester l'OCR et l'extraction de TVA
- [ ] Vérifier la création de partenaires

### Module storage_indexation
- [ ] Tester l'indexation automatique des prix
- [ ] Vérifier les calculs basés sur l'indice santé belge

### Module storage_plan_module
- [ ] Tester le plan interactif des boxes
- [ ] Vérifier les réservations

### Module lolirine_contract
- [ ] Tester la génération de contrats PDF
- [ ] Vérifier les signatures électroniques

### Module lolirine_invoice
- [ ] Tester l'envoi de factures par email
- [ ] Vérifier l'intégration Peppol

---

## Changements API Odoo 19 (Pour Référence)

### Dépréciés dans Odoo 19

| Ancien | Nouveau |
|--------|---------|
| `self._cr` | `self.env.cr` |
| `self._context` | `self.env.context` |
| `self._uid` | `self.env.uid` |
| `name_get()` | Lire `display_name` |
| `read_group()` | `_read_group()` ou `formatted_read_group()` |
| `odoo.osv` | Nouveau système de domaines |

### Nouveautés Odoo 19

- `@api.private` pour méthodes non-RPC
- Nouveau `odoo.domain` et `odoo.Domain` API
- Support GROUPING SETS pour les vues pivot
- Dates dynamiques dans les domaines

---

## Conclusion

Tes modules Lolirine sont **prêts pour Odoo 19** après les corrections minimales appliquées. Le code est propre et suit les bonnes pratiques Odoo.

**Prochaine étape** : Télécharge le ZIP corrigé et effectue la migration via Odoo.sh.

---

*Rapport généré automatiquement par Claude - Anthropic*
