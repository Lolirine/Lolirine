# Guide de déploiement et debug - Box Contact Redirect

## Déploiement sur Odoo.sh

### Méthode 1 : Via Git (Recommandée)

1. **Cloner votre dépôt Odoo.sh**
   ```bash
   git clone https://votre-projet@odoo.sh/votre-projet.git
   cd votre-projet
   ```

2. **Ajouter le module**
   ```bash
   # Créer le dossier du module
   mkdir -p box_contact_redirect
   
   # Copier les fichiers (ajustez le chemin source)
   cp -r /chemin/source/box_contact_redirect/* box_contact_redirect/
   ```

3. **Vérifier la structure**
   ```bash
   tree box_contact_redirect
   ```
   
   Vous devriez voir :
   ```
   box_contact_redirect/
   ├── __init__.py
   ├── __manifest__.py
   ├── controllers/
   ├── models/
   ├── views/
   ├── data/
   └── README.md
   ```

4. **Commit et push**
   ```bash
   git add box_contact_redirect/
   git commit -m "Add box_contact_redirect module"
   git push origin master
   ```

5. **Attendre le déploiement**
   - Odoo.sh va automatiquement rebuilder votre instance
   - Suivez les logs dans le dashboard Odoo.sh
   - Une fois terminé, connectez-vous à votre instance

6. **Installer le module**
   - Activez le mode développeur : Settings > Activate the developer mode
   - Apps > Update Apps List
   - Recherchez "Box Contact Redirect"
   - Installez le module

### Méthode 2 : Upload manuel (Développement local)

Pour tester localement avant de pousser :

1. **Copier dans addons**
   ```bash
   cp -r box_contact_redirect /chemin/vers/odoo/addons/
   ```

2. **Redémarrer Odoo**
   ```bash
   ./odoo-bin -u box_contact_redirect -d votre_database
   ```

## Vérification post-installation

### 1. Vérifier que le module est installé

```python
# Dans Odoo shell
self.env['ir.module.module'].search([('name', '=', 'box_contact_redirect')])
```

### 2. Vérifier les champs sur product.template

```python
# Dans Odoo shell
product = self.env['product.template'].search([], limit=1)
print(hasattr(product, 'box_require_contact'))
print(hasattr(product, 'box_is_available'))
```

### 3. Tester sur un produit

1. Créez ou modifiez un produit
2. Cochez "Box disponible" et "Rediriger vers contact"
3. Publiez le produit sur le site web
4. Visitez la page produit en mode non connecté
5. Vérifiez que le bouton "Nous contacter" apparaît

## Debug et résolution de problèmes

### Problème : Le module n'apparaît pas dans la liste

**Solution :**
1. Vérifiez que `__manifest__.py` est correct
2. Activez le mode développeur
3. Apps > Update Apps List
4. Recherchez à nouveau

### Problème : Erreur lors de l'installation

**Vérifiez :**
1. Les dépendances sont installées (`website_sale`, `sale_subscription`)
2. Les fichiers XML sont bien formés
3. Les imports Python sont corrects

**Commandes de debug :**
```bash
# Voir les logs Odoo
tail -f /var/log/odoo/odoo.log

# Tester la syntaxe XML
xmllint --noout views/website_sale_templates.xml
```

### Problème : Le bouton ne change pas sur le site

**Vérifiez :**
1. Le produit a bien les deux cases cochées
2. Le cache du site est vidé (Ctrl+F5)
3. Le mode debug assets est activé
4. Les templates sont bien hérités

**Test en mode développeur :**
```python
# Vérifier le template
template = self.env.ref('box_contact_redirect.product_add_to_cart_inherit_box')
print(template.exists())
```

### Problème : La redirection ne fonctionne pas

**Vérifiez :**
1. Le controller est bien chargé
2. La route `/contactus` est accessible
3. Le formulaire de contact standard existe

**Test de la route :**
```bash
curl -I https://votre-site.odoo.com/contactus?box_name=Test
```

## Personnalisation avancée

### Modifier le message de contact par défaut

Éditez `controllers/main.py` :

```python
default_message = f"""Bonjour,

Je suis intéressé(e) par le box : {box_name}

Informations complémentaires :
- Durée souhaitée : 
- Date de début : 
- Questions particulières : 

Merci de me recontacter.
"""
```

### Ajouter un badge "Disponible" sur les vignettes

Créez un nouveau template dans `views/website_sale_templates.xml` :

```xml
<template id="product_badge_available" inherit_id="website_sale.products_item">
    <xpath expr="//div[hasclass('ribbon')]" position="after">
        <span t-if="product.box_is_available and product.box_require_contact" 
              class="badge badge-success" 
              style="position: absolute; top: 10px; right: 10px;">
            Disponible
        </span>
    </xpath>
</template>
```

### Envoyer un email automatique lors du contact

Ajoutez dans `controllers/main.py` :

```python
from odoo.tools.mail import email_split

@http.route(['/box/contact/submit'], type='http', auth="public", methods=['POST'], website=True, csrf=True)
def submit_box_contact(self, **post):
    box_id = post.get('box_id')
    if box_id:
        product = request.env['product.template'].sudo().browse(int(box_id))
        # Envoyer un email à l'équipe commerciale
        mail_values = {
            'subject': f'Demande de contact pour le box : {product.name}',
            'body_html': f'<p>Nouvelle demande de contact...</p>',
            'email_to': 'commercial@votreentreprise.com',
        }
        request.env['mail.mail'].sudo().create(mail_values).send()
    
    return request.redirect('/contactus-thank-you')
```

## Maintenance

### Mettre à jour le module

```bash
# Après modifications
git add box_contact_redirect/
git commit -m "Update box_contact_redirect module"
git push origin master

# Dans Odoo
Apps > box_contact_redirect > Upgrade
```

### Logs utiles

```python
# Ajouter des logs dans le code
import logging
_logger = logging.getLogger(__name__)

_logger.info("Box contact redirect: product %s", product.name)
```

## Support

Pour tout problème, vérifiez :
1. Les logs Odoo.sh dans le dashboard
2. La console du navigateur (F12)
3. Le mode debug Odoo activé

## Checklist de déploiement

- [ ] Module copié dans le dépôt Git
- [ ] Push vers Odoo.sh effectué
- [ ] Build réussi
- [ ] Module installé
- [ ] Tests effectués sur un produit
- [ ] Vérification sur le site web public
- [ ] Cache vidé
- [ ] Formulaire de contact fonctionnel
