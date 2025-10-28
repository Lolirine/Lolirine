# Installation du module Box Contact Redirect via GitHub

## 📦 Fichier à télécharger

**box_contact_redirect.zip** (14 KB)

Ce fichier contient le module complet prêt pour Odoo 18.1.

---

## 🚀 Installation via GitHub

### Étape 1 : Télécharger et extraire le module

1. Téléchargez le fichier **box_contact_redirect.zip**
2. Extrayez l'archive sur votre ordinateur
3. Vous obtiendrez un dossier `box_contact_redirect/`

### Étape 2 : Cloner votre dépôt GitHub

```bash
# Cloner votre dépôt GitHub lié à Odoo.sh
git clone https://github.com/votre-compte/votre-repo-odoo.git
cd votre-repo-odoo
```

### Étape 3 : Copier le module

```bash
# Copier le dossier box_contact_redirect dans votre dépôt
cp -r /chemin/vers/box_contact_redirect .

# Vérifier que le module est bien présent
ls -la box_contact_redirect/
```

### Étape 4 : Commit et push vers GitHub

```bash
# Ajouter les fichiers
git add box_contact_redirect/

# Vérifier les fichiers ajoutés
git status

# Commit
git commit -m "Add box_contact_redirect module v18.1.1.0 for Odoo"

# Push vers GitHub
git push origin main
# OU si vous utilisez master :
git push origin master
```

### Étape 5 : Synchronisation avec Odoo.sh

Si votre Odoo.sh est lié à GitHub :
1. Le push déclenchera automatiquement un build sur Odoo.sh
2. Consultez le dashboard Odoo.sh pour suivre le build
3. Une fois terminé, le module sera disponible

---

## 📋 Structure du module (contenu du ZIP)

```
box_contact_redirect/
├── __init__.py                         # Init principal
├── __manifest__.py                     # Configuration du module (v18.1.1.0)
├── README.md                           # Documentation
├── QUICKSTART.md                       # Guide rapide
├── DEPLOYMENT.md                       # Guide de déploiement
├── config.py                           # Configuration
├── controllers/
│   ├── __init__.py
│   └── main.py                         # Gestion de la redirection
├── models/
│   ├── __init__.py
│   └── product_template.py             # Champs produit
├── views/
│   ├── product_template_views.xml      # Vue backend
│   └── website_sale_templates.xml      # Templates frontend
└── data/
    └── demo_data.xml                   # Données de démo (optionnel)
```

---

## ✅ Installation dans Odoo (après le push)

1. Connectez-vous à votre instance Odoo.sh
2. **Paramètres** > **Activer le mode développeur**
3. **Apps** > **Mettre à jour la liste des Apps**
4. Recherchez "**Box Contact Redirect**"
5. Cliquez sur **Installer**

---

## 🎯 Configuration d'un produit

Après installation :

1. **Ventes** > **Produits** > Ouvrir un produit (box)
2. Onglet **Ventes** > Section **Gestion Box**
3. Cocher :
   - ☑️ **Box disponible**
   - ☑️ **Rediriger vers contact**
4. **Publier** sur le site web
5. Vérifier sur le site : le bouton "Nous contacter" doit apparaître

---

## 🔧 Vérification après installation

### Vérifier que le module est bien dans le dépôt

```bash
git log --oneline | head -5
# Vous devriez voir votre commit "Add box_contact_redirect..."
```

### Vérifier sur Odoo.sh

1. Dashboard Odoo.sh > Logs du build
2. Vérifier qu'il n'y a pas d'erreurs
3. Le module doit être dans la liste des Apps

### Test fonctionnel

1. Configurer un produit comme indiqué ci-dessus
2. Visiter le site en mode non connecté
3. Le bouton "Nous contacter" doit être visible au lieu de "Ajouter au panier"

---

## 📝 Commandes Git utiles

```bash
# Voir les fichiers modifiés
git status

# Voir l'historique
git log --oneline

# Annuler le dernier commit (si nécessaire)
git reset --soft HEAD~1

# Forcer le push (si conflit)
git push origin main --force
```

---

## 🐛 Résolution de problèmes

### Le module n'apparaît pas dans Apps

**Solutions :**
- Vérifier que le push GitHub est bien effectué
- Vérifier les logs de build sur Odoo.sh
- Mettre à jour la liste des Apps dans Odoo
- Activer le mode développeur

### Erreur lors du build Odoo.sh

**Solutions :**
- Consulter les logs dans le dashboard Odoo.sh
- Vérifier que `website_sale` est installé
- Vérifier la syntaxe des fichiers XML

### Le bouton ne change pas sur le site

**Solutions :**
- Vérifier que les deux cases sont cochées sur le produit
- Vider le cache du navigateur (Ctrl+F5)
- Vérifier que le produit est publié sur le site web

---

## 📚 Documentation supplémentaire

- **README.md** : Documentation du module (dans le ZIP)
- **QUICKSTART.md** : Guide de démarrage rapide (dans le ZIP)
- **DEPLOYMENT.md** : Guide de déploiement détaillé (dans le ZIP)

---

## ✨ Version du module

**Version : 18.1.1.0**

Compatible avec :
- ✅ Odoo 18.1
- ✅ Odoo 17.x
- ✅ Community et Enterprise

Testé et validé pour Odoo 18.1 !

---

## 🎉 C'est terminé !

Votre module est maintenant déployé via GitHub et prêt à être utilisé sur Odoo.sh.

Bonne gestion de vos box ! 📦
