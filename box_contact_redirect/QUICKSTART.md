# Guide de démarrage rapide - Box Contact Redirect

## Installation en 5 étapes

### 1. Récupérer le module
Vous avez reçu le fichier `box_contact_redirect.zip` ou le dossier `box_contact_redirect/`

### 2. Déployer sur Odoo.sh

**Option A : Via Git (Recommandé)**
```bash
# Cloner votre projet Odoo.sh
git clone https://[votre-projet]@odoo.sh/[votre-projet].git
cd [votre-projet]

# Extraire le module
unzip box_contact_redirect.zip
# OU copier le dossier directement

# Commit et push
git add box_contact_redirect/
git commit -m "Add box contact redirect module"
git push origin master
```

**Option B : Upload manuel sur une instance de développement**
- Connectez-vous à votre serveur
- Placez le dossier dans `/chemin/odoo/addons/`
- Redémarrez Odoo

### 3. Installer le module dans Odoo

1. Connectez-vous à votre instance Odoo
2. Allez dans **Paramètres** (Settings)
3. Activez le **mode développeur** :
   - Cliquez sur "Activer le mode développeur"
4. Allez dans **Apps** (Applications)
5. Cliquez sur **Mettre à jour la liste des Apps**
6. Recherchez "**Box Contact Redirect**"
7. Cliquez sur **Installer**

### 4. Configurer vos produits (Box)

1. Allez dans **Ventes > Produits > Produits**
2. Sélectionnez un produit (box) ou créez-en un nouveau
3. Dans l'onglet **Ventes**, trouvez la section **"Gestion Box"**
4. **Cochez** :
   - ☑ **Box disponible** : le box est actuellement libre
   - ☑ **Rediriger vers contact** : remplace le bouton d'achat

5. **Sauvegardez** le produit

### 5. Vérifier sur le site web

1. Allez sur votre **site web** (en mode visiteur, déconnecté)
2. Naviguez vers la **boutique** ou le **catalogue de box**
3. Trouvez le produit que vous venez de configurer
4. Vous devriez voir un bouton **"Nous contacter pour ce box"** au lieu de "Ajouter au panier"
5. Cliquez dessus pour vérifier la redirection vers le formulaire de contact

## Configuration type pour un box

```
Nom du produit : Box 5m² - Rez-de-chaussée
Type : Service (pour les abonnements)
Prix : 50.00 € / mois
Récurrent : Oui (facturation mensuelle)

Dans l'onglet "Ventes" :
✓ Box disponible
✓ Rediriger vers contact
✓ Publié sur le site web
```

## Que se passe-t-il quand un client clique sur "Nous contacter" ?

1. Le client est redirigé vers `/contactus`
2. Le formulaire de contact s'affiche
3. Le message est pré-rempli avec :
   ```
   Bonjour,
   
   Je suis intéressé(e) par le box : [Nom du box]
   
   Merci de me recontacter.
   ```
4. Le client peut compléter ses coordonnées et envoyer

## Astuce : Gérer plusieurs box

Pour gérer efficacement plusieurs box :

1. **Créez un attribut ou une catégorie** pour différencier vos box
   - Exemple : "Box 5m²", "Box 10m²", "Box 20m²"

2. **Utilisez des variantes** si vous avez plusieurs box identiques
   - Exemple : Box 5m² - Étage 1, Box 5m² - Étage 2

3. **Cochez systématiquement** "Rediriger vers contact" pour tous les box libres

4. **Décochez** quand le box est loué pour qu'il n'apparaisse plus comme disponible

## Workflow recommandé

### Quand un box devient disponible :
1. Ouvrez le produit dans Odoo
2. ☑ Cochez "Box disponible"
3. ☑ Cochez "Rediriger vers contact"
4. ☑ Publiez sur le site web si ce n'est pas déjà fait

### Quand un box est loué :
1. Ouvrez le produit dans Odoo
2. ☐ Décochez "Box disponible"
3. ☐ (Optionnel) Décochez "Publié sur le site web" pour le masquer

### Gestion des demandes :
1. Vous recevez les demandes via le formulaire de contact
2. Traitez la demande (appel, email, etc.)
3. Si le client confirme, créez une commande/abonnement
4. Marquez le box comme non disponible

## Personnalisation rapide

### Changer le texte du bouton

Éditez `views/website_sale_templates.xml`, ligne ~8 :
```xml
<i class="fa fa-envelope"/> Nous contacter pour ce box
```

Remplacez par votre texte, par exemple :
```xml
<i class="fa fa-phone"/> Appelez-nous pour réserver
```

### Changer le message pré-rempli

Éditez `controllers/main.py`, ligne ~25 :
```python
default_message = f"Votre message personnalisé ici\n\nBox : {box_name}"
```

## FAQ

**Q : Puis-je avoir à la fois "Ajouter au panier" pour certains produits et "Contact" pour d'autres ?**  
R : Oui ! Seuls les produits avec les deux cases cochées auront le bouton de contact. Les autres garderont le bouton d'achat normal.

**Q : Comment désactiver temporairement le module ?**  
R : Apps > Box Contact Redirect > Désinstaller. Mais il est préférable de simplement décocher les cases sur les produits concernés.

**Q : Puis-je utiliser ce module pour d'autres types de produits ?**  
R : Oui ! Le module fonctionne pour n'importe quel produit. Il suffit de cocher les deux cases.

**Q : Le formulaire de contact peut-il être personnalisé ?**  
R : Oui, vous pouvez créer votre propre formulaire de contact en héritant du template Odoo standard.

## Besoin d'aide ?

1. Consultez le `README.md` pour plus de détails
2. Consultez le `DEPLOYMENT.md` pour le debug
3. Vérifiez les logs Odoo.sh
4. Activez le mode développeur pour plus d'options

## Prochaines étapes

Une fois le module installé et testé :
- [ ] Configurez tous vos box disponibles
- [ ] Testez le processus complet (clic → contact → réception)
- [ ] Personnalisez le message de contact selon vos besoins
- [ ] (Optionnel) Ajoutez des automatisations email
- [ ] Formez votre équipe à l'utilisation

Bonne gestion de vos box ! 📦
