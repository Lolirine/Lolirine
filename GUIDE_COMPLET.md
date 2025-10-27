# Module Box Contact Redirect - Installation et Guide Complet

## 📦 Contenu du module

Votre module Odoo personnalisé **Box Contact Redirect** est prêt ! Il contient :

### Fichiers principaux :
- **__manifest__.py** : Configuration du module
- **__init__.py** : Initialisation du module
- **config.py** : Paramètres de configuration

### Dossiers :
- **controllers/** : Gestion de la redirection vers le formulaire de contact
- **models/** : Extension du modèle produit avec les nouveaux champs
- **views/** : Templates pour le backend et le frontend
- **data/** : Données de démonstration (optionnelles)

### Documentation :
- **README.md** : Documentation complète du module
- **QUICKSTART.md** : Guide de démarrage rapide (À LIRE EN PREMIER !)
- **DEPLOYMENT.md** : Guide de déploiement et debug

---

## 🚀 Installation rapide (5 minutes)

### Étape 1 : Récupérer le module
- Téléchargez **box_contact_redirect.zip**
- OU utilisez le dossier **box_contact_redirect/**

### Étape 2 : Déployer sur Odoo.sh

```bash
# Cloner votre projet
git clone https://[votre-projet]@odoo.sh/[votre-projet].git
cd [votre-projet]

# Ajouter le module
unzip /chemin/vers/box_contact_redirect.zip
# OU
cp -r /chemin/vers/box_contact_redirect .

# Pousser vers Odoo.sh
git add box_contact_redirect/
git commit -m "Add box contact redirect module"
git push origin master
```

### Étape 3 : Installer dans Odoo
1. Paramètres > Activer le mode développeur
2. Apps > Mettre à jour la liste des Apps
3. Rechercher "Box Contact Redirect"
4. Installer

### Étape 4 : Configurer un box
1. Ventes > Produits
2. Ouvrir un produit (box)
3. Onglet Ventes > Section "Gestion Box"
4. Cocher : ☑ Box disponible + ☑ Rediriger vers contact
5. Sauvegarder

### Étape 5 : Tester
- Visitez votre site en mode non connecté
- Allez sur le produit configuré
- Le bouton "Nous contacter pour ce box" doit apparaître

---

## ✨ Fonctionnalités

### Ce que fait le module :

1. **Ajout de 2 nouveaux champs** sur chaque produit :
   - "Box disponible" : indique qu'un box est libre
   - "Rediriger vers contact" : active le bouton de contact

2. **Remplacement intelligent du bouton** :
   - Si les 2 cases sont cochées → Bouton "Nous contacter"
   - Sinon → Bouton "Ajouter au panier" normal

3. **Redirection avec contexte** :
   - Clic sur "Nous contacter" → Formulaire de contact
   - Message pré-rempli avec le nom du box
   - L'ID du box est transmis pour suivi

4. **Fonctionne partout** :
   - Page détail du produit
   - Grille de produits / catalogue
   - Vue liste

---

## 🎯 Cas d'usage typique

### Scénario : Gestion d'un box de 5m²

**Situation initiale** : Box libre, vous voulez que les clients vous contactent

**Configuration dans Odoo** :
```
Produit : Box 5m² - Étage 1
Type : Service (abonnement)
Prix : 50€/mois
☑ Récurrent (mensuel)
☑ Box disponible
☑ Rediriger vers contact
☑ Publié sur le site web
```

**Résultat sur le site** :
- Le client voit le box avec ses caractéristiques
- Au lieu de "Ajouter au panier", il voit "Nous contacter pour ce box"
- Clic → Formulaire de contact pré-rempli
- Vous recevez la demande et pouvez traiter la location

**Quand le box est loué** :
```
☐ Décocher "Box disponible"
```
→ Le box n'apparaît plus comme disponible ou peut être masqué

---

## 🔧 Personnalisation

### Changer le texte du bouton

**Fichier** : `views/website_sale_templates.xml`

**Ligne à modifier** :
```xml
<i class="fa fa-envelope"/> Nous contacter pour ce box
```

**Exemples de personnalisation** :
```xml
<i class="fa fa-phone"/> Réserver ce box
<i class="fa fa-calendar"/> Demander la disponibilité
<i class="fa fa-comments"/> Discuter avec un conseiller
```

### Changer le message pré-rempli

**Fichier** : `controllers/main.py`

**Ligne à modifier** :
```python
default_message = f"Bonjour,\n\nJe suis intéressé(e) par le box : {box_name}\n\nMerci de me recontacter.\n"
```

**Exemple de personnalisation** :
```python
default_message = f"""Bonjour,

Je souhaite obtenir plus d'informations sur le box : {box_name}

Informations sur mon besoin :
- Durée de location souhaitée : 
- Date de début souhaitée : 
- Questions spécifiques : 

Cordialement,
"""
```

---

## 📋 Structure technique du module

```
box_contact_redirect/
│
├── __init__.py                      # Init principal
├── __manifest__.py                  # Configuration du module
├── config.py                        # Paramètres
│
├── controllers/
│   ├── __init__.py
│   └── main.py                      # Controller pour la redirection
│
├── models/
│   ├── __init__.py
│   └── product_template.py          # Extension du modèle Produit
│
├── views/
│   ├── product_template_views.xml   # Vue backend (formulaire)
│   └── website_sale_templates.xml   # Vue frontend (site web)
│
├── data/
│   └── demo_data.xml                # Données de démo (optionnel)
│
└── Documentation/
    ├── README.md                    # Doc complète
    ├── QUICKSTART.md                # Guide rapide
    └── DEPLOYMENT.md                # Guide déploiement
```

---

## ⚙️ Configuration avancée

### Ajouter une notification email automatique

Vous pouvez modifier `controllers/main.py` pour envoyer un email automatique à votre équipe :

```python
@http.route(['/contactus'], type='http', auth="public", website=True, sitemap=False)
def contact_form_box(self, box_name=None, box_id=None, **kwargs):
    # ... code existant ...
    
    # Envoyer une notification
    if box_id:
        mail_values = {
            'subject': f'🔔 Nouvelle demande pour le box {box_name}',
            'body_html': f'<p>Un client est intéressé par le box {box_name}</p>',
            'email_to': 'location@votreentreprise.com',
        }
        request.env['mail.mail'].sudo().create(mail_values).send()
    
    return request.render("website.contactus", values)
```

### Intégrer avec un CRM

Le module peut être étendu pour créer automatiquement une opportunité dans le CRM Odoo :

```python
# Créer une opportunité CRM
lead_values = {
    'name': f'Demande box : {box_name}',
    'type': 'opportunity',
    'partner_id': partner.id if partner else False,
}
request.env['crm.lead'].sudo().create(lead_values)
```

---

## 🐛 Résolution de problèmes

### Le module n'apparaît pas dans Apps
- Vérifiez que les fichiers sont bien dans le dossier addons
- Mode développeur activé ?
- "Mettre à jour la liste des Apps" effectué ?

### Le bouton ne change pas
- Les deux cases sont bien cochées ?
- Cache du navigateur vidé (Ctrl + F5) ?
- Le produit est publié sur le site ?

### Erreur lors de l'installation
- Vérifiez que `website_sale` et `sale_subscription` sont installés
- Consultez les logs Odoo.sh
- Vérifiez la syntaxe des fichiers XML

### La redirection ne fonctionne pas
- Testez l'URL directement : `https://votre-site.com/contactus?box_name=Test`
- Vérifiez que le formulaire de contact standard existe

---

## 📊 Workflow recommandé

### Pour un nouveau box disponible :
1. Créer le produit dans Odoo
2. ☑ Type = Service (pour abonnement)
3. ☑ Récurrent = Oui (mensuel/annuel)
4. ☑ Box disponible
5. ☑ Rediriger vers contact
6. ☑ Publier sur le site web

### Quand vous recevez une demande :
1. Contactez le client (email/téléphone)
2. Si location confirmée :
   - Créez un abonnement/commande dans Odoo
   - ☐ Décochez "Box disponible" sur le produit
3. Si pas intéressé : suivez votre processus normal

### Quand un box se libère :
1. Terminez l'abonnement du client sortant
2. ☑ Recochez "Box disponible"
3. Le box réapparaît automatiquement avec le bouton contact

---

## 🎓 Bonnes pratiques

### Nommage des produits
Utilisez des noms clairs et descriptifs :
- ✅ "Box 5m² - Rez-de-chaussée - Accès facile"
- ✅ "Box 10m² - 1er étage - Sécurisé"
- ❌ "Box 1" ou "Produit A"

### Catégorisation
Créez des catégories pour faciliter la navigation :
- "Box petits volumes (5m²)"
- "Box moyens volumes (10m²)"
- "Box grands volumes (20m²+)"

### Images
Ajoutez des photos de qualité :
- Photo du box vide
- Photo des dimensions
- Photo de l'accès

### Description
Soyez précis sur :
- Dimensions exactes
- Étage / Emplacement
- Conditions d'accès
- Services inclus

---

## 📞 Support et ressources

### Documentation incluse :
- **QUICKSTART.md** : Démarrage rapide (lire en premier)
- **README.md** : Documentation technique complète
- **DEPLOYMENT.md** : Déploiement et debug

### Pour aller plus loin :
- Documentation Odoo officielle : https://www.odoo.com/documentation
- Forum Odoo : https://www.odoo.com/forum
- Documentation développeurs : https://www.odoo.com/documentation/developer/

### Logs et debug :
- Logs Odoo.sh : Dashboard > Logs
- Mode développeur : Paramètres > Activer
- Console navigateur : F12 (pour debug frontend)

---

## ✅ Checklist de déploiement

### Avant de commencer :
- [ ] Sauvegarde de votre base de données Odoo
- [ ] Accès Git à votre projet Odoo.sh
- [ ] Mode développeur activé

### Installation :
- [ ] Module copié dans le dépôt Git
- [ ] Push effectué vers Odoo.sh
- [ ] Build réussi (vérifier dans dashboard)
- [ ] Module installé dans Apps
- [ ] Pas d'erreurs dans les logs

### Configuration :
- [ ] Au moins un produit configuré en test
- [ ] Cases "Box disponible" et "Rediriger vers contact" cochées
- [ ] Produit publié sur le site web

### Tests :
- [ ] Bouton "Nous contacter" visible sur la page produit
- [ ] Bouton "Nous contacter" visible dans le catalogue
- [ ] Clic redirige vers le formulaire de contact
- [ ] Message pré-rempli avec le nom du box
- [ ] Formulaire de contact fonctionnel
- [ ] Réception de la demande de contact

### Mise en production :
- [ ] Tests réussis sur environnement de staging
- [ ] Configuration de tous les box disponibles
- [ ] Formation de l'équipe effectuée
- [ ] Process de gestion des demandes défini

---

## 🎉 Félicitations !

Votre module est maintenant opérationnel. Vous pouvez :
1. Configurer tous vos box disponibles
2. Commencer à recevoir des demandes de contact
3. Gérer efficacement vos locations

N'hésitez pas à personnaliser le module selon vos besoins spécifiques !

---

**Version du module** : 1.0  
**Compatible avec** : Odoo 14.0 et supérieur  
**Dépendances** : website_sale, sale_subscription  
**Licence** : LGPL-3
