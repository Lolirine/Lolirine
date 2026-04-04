# lolirine_storage_notify
## Module de notifications temps réel – Garde-Meuble Lolirine

### Vue d'ensemble

Ce module implémente **3 couches de notification simultanées** pour alerter l'administrateur
dès qu'un client interagit sur le portail garde-meuble.

---

## Les 3 canaux

| Canal | Quand | Condition |
|---|---|---|
| **Toast backend (bus.bus)** | Instantané | L'onglet Odoo doit être ouvert |
| **Activité mail (pastille 🟠)** | Instantané | Toujours, visible dans le menu Activités |
| **Web Push (OS level)** | Instantané | Navigateur enregistré, même minimisé |

---

## Événements surveillés

| Événement | Déclencheur |
|---|---|
| Inscription portail | `res.users` create avec group_portal |
| Demande de RDV | `calendar.event` create depuis le portail |
| Formulaire de contact | `crm.lead` create depuis le site web |
| Message portail | `mail.message` create par un utilisateur portail |

---

## Installation

### 1. Dépendance Python (Odoo.sh)

Ajoutez dans votre `requirements.txt` à la **racine du dépôt** :

```
pywebpush>=2.0.0
```

Puis commitez et laissez Odoo.sh rebuilder.

### 2. Installer le module

```bash
# Via Odoo shell
env['ir.module.module'].search([('name','=','lolirine_storage_notify')]).button_immediate_install()
```

### 3. Générer les clés VAPID (Web Push)

1. Aller dans **Paramètres → Notifications Lolirine**
2. Cliquer sur **🔑 Générer les clés VAPID**
3. Saisir votre email de contact (ex: `admin@lolirine.be`)
4. Cliquer **Générer** puis **Sauvegarder**

### 4. Activer le Web Push dans le navigateur

Au prochain chargement du backend Odoo, une demande de permission apparaîtra.
**Accepter** pour activer les notifications OS-level.

Vérifier les abonnements dans :
**Paramètres → Abonnements Push**

### 5. Tester

Via l'action serveur **"Tester les notifications"** dans la liste des actions,
ou via le shell :

```python
env['lolirine.notify.mixin']._lolirine_notify(
    event_type='default',
    title='Test',
    message='Ça fonctionne !',
    partner=env.user.partner_id,
    url='/odoo/settings',
    activity_summary='Test',
)
```

---

## Architecture des fichiers

```
lolirine_storage_notify/
├── __manifest__.py
├── requirements.txt                    ← pywebpush
├── models/
│   ├── notify_mixin.py                 ← Cœur : 3 canaux
│   ├── push_subscription.py            ← Stockage abonnements push
│   ├── res_users.py                    ← Hook inscription portail
│   ├── calendar_event.py               ← Hook demande RDV
│   ├── crm_lead.py                     ← Hook formulaire contact
│   ├── mail_message.py                 ← Hook messages portail
│   └── res_config_settings.py          ← Paramètres
├── controllers/
│   └── notify_controller.py            ← API push + SW serving
├── wizard/
│   ├── vapid_setup_wizard.py           ← Génération clés VAPID
│   └── vapid_setup_views.xml
├── static/src/js/
│   ├── notify_service.js               ← Service OWL (bus + push)
│   └── service_worker.js               ← SW (servi via /sw-lolirine.js)
├── data/
│   ├── mail_activity_type.xml
│   └── ir_config_parameter.xml
├── views/
│   ├── push_subscription_views.xml
│   └── res_config_settings_views.xml
└── security/
    └── ir.model.access.csv
```

---

## Notes importantes

- Le Service Worker est servi via `/sw-lolirine.js` (controller Python)
  pour satisfaire la contrainte de scope racine des navigateurs.
- Les abonnements révoqués (HTTP 404/410) sont désactivés automatiquement.
- Le canal **bus.bus** ne fonctionne que si l'onglet backend est ouvert.
- Le canal **activité** est toujours fiable et visible dès la prochaine ouverture.
- Le canal **Web Push** fonctionne même navigateur fermé (sauf si le PC est éteint).
