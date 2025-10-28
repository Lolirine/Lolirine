# Box Contact Redirect - Module Odoo 18.1

Module personnalisé pour la gestion de garde-meubles permettant de remplacer le bouton "Ajouter au panier" par un bouton "Nous contacter" pour les box disponibles.

## Version

**18.1.1.0** - Compatible avec Odoo 18.1 et 17.x

## Fonctionnalités

- 🎯 Ajoute deux champs sur les produits : "Box disponible" et "Rediriger vers contact"
- 🔄 Remplace automatiquement le bouton d'achat par un bouton de contact
- 📧 Redirige vers le formulaire de contact avec pré-remplissage des informations
- 🎨 S'intègre parfaitement dans le design Odoo 18.1
- ⚡ Fonctionne sur la page produit ET dans le catalogue

## Dépendances

- `website_sale` (module e-commerce standard Odoo)

## Installation

### Sur Odoo.sh

```bash
# Cloner votre projet
git clone https://votre-projet@odoo.sh/votre-projet.git
cd votre-projet

# Copier le module
cp -r box_contact_redirect .

# Push vers Odoo.sh
git add box_contact_redirect/
git commit -m "Add box_contact_redirect module"
git push origin master
```

### Dans Odoo

1. Activez le mode développeur
2. Apps > Mettre à jour la liste des Apps
3. Recherchez "Box Contact Redirect"
4. Installez

## Utilisation

### Configuration d'un produit

1. Ouvrez un produit dans **Ventes > Produits**
2. Allez dans l'onglet **Ventes**
3. Section **Gestion Box** :
   - ☑️ Cochez **Box disponible**
   - ☑️ Cochez **Rediriger vers contact**
4. Publiez le produit sur le site web

### Résultat

- Sur la page produit : Bouton "Nous contacter pour ce box"
- Dans le catalogue : Bouton "Nous contacter"
- Clic → Redirection vers le formulaire de contact

### Quand un box est loué

Décochez simplement **Box disponible** pour que le produit revienne au mode normal.

## Structure du module

```
box_contact_redirect/
├── __init__.py
├── __manifest__.py
├── README.md
├── controllers/
│   ├── __init__.py
│   └── main.py              # Controller de redirection
├── models/
│   ├── __init__.py
│   └── product_template.py   # Extension du modèle produit
└── views/
    ├── product_template_views.xml      # Vue backend
    └── website_sale_templates.xml      # Templates frontend
```

## Compatibilité

- ✅ Odoo 18.1 (version actuelle)
- ✅ Odoo 17.x
- ✅ Community et Enterprise
- ✅ Syntaxe moderne des vues
- ✅ Bootstrap 5

## Support

Pour toute question ou problème :
1. Vérifiez que `website_sale` est installé
2. Consultez les logs Odoo.sh
3. Vérifiez que le mode développeur est activé

## Licence

LGPL-3

## Auteur

Custom Development

---

**Version 18.1.1.0** - Testé et fonctionnel sur Odoo 18.1
