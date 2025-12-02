# Guide d'implémentation des données

## Comment ajouter vos boxes au plan interactif

### 1. Comprendre le système de grille

Le plan utilise une grille CSS pour positionner les boxes. Chaque box a deux coordonnées :
- `grid_row` : La ligne (de haut en bas)
- `grid_col` : La colonne (de gauche à droite)

Par exemple, d'après vos captures d'écran :

**Rez-de-chaussée :**
```
Colonne:    1      2      3      4      5
Ligne 1:  1G08   1G09   1D20   1D24   1D23
Ligne 2:  1G07   1G10   1D21   1D25   (SDS)
Ligne 3:  1G06   1G11   1D18   1D26
...
```

**Premier étage :**
```
Colonne:    1      2      3      4      5
Ligne 1:  CNC2   2G43   2G44   2D61   2D62
Ligne 2:         2G42   2G44   2D60   2D63
Ligne 3:         2G41   2G45   2D59   2D64
...
```

### 2. Créer des boxes via l'interface

1. Aller dans `Garde-Meubles > Boxes > Tous les boxes`
2. Cliquer sur "Créer"
3. Remplir les informations :

**Exemple pour le box 1D30 (de votre capture) :**
- Numéro de box : `1D30`
- Étage : `Rez-de-chaussée`
- Largeur : `240` cm
- Profondeur : `200` cm
- Hauteur : `250` cm
- Prix mensuel : `91` €
- Statut : `Disponible`
- Ligne grille : `1` (ou selon sa position)
- Colonne grille : `5` (ou selon sa position)

### 3. Créer des boxes en masse via XML

Créer un fichier XML dans `data/` :

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="0">
        <!-- Rez-de-chaussée - Ligne 1 -->
        <record id="box_1g08" model="storage.box">
            <field name="name">1G08</field>
            <field name="floor_id" ref="floor_ground"/>
            <field name="width">240</field>
            <field name="depth">200</field>
            <field name="height">250</field>
            <field name="price_monthly">91</field>
            <field name="status">occupe</field>
            <field name="grid_row">1</field>
            <field name="grid_col">1</field>
        </record>

        <record id="box_1g09" model="storage.box">
            <field name="name">1G09</field>
            <field name="floor_id" ref="floor_ground"/>
            <field name="width">240</field>
            <field name="depth">200</field>
            <field name="height">250</field>
            <field name="price_monthly">91</field>
            <field name="status">occupe</field>
            <field name="grid_row">1</field>
            <field name="grid_col">2</field>
        </record>

        <record id="box_1d20" model="storage.box">
            <field name="name">1D20</field>
            <field name="floor_id" ref="floor_ground"/>
            <field name="width">250</field>
            <field name="depth">200</field>
            <field name="height">250</field>
            <field name="price_monthly">85</field>
            <field name="status">disponible</field>
            <field name="grid_row">1</field>
            <field name="grid_col">3</field>
        </record>

        <!-- ... continuez pour tous vos boxes -->
    </data>
</odoo>
```

### 4. Créer des boxes via l'API Python

```python
# Script Python pour créer des boxes en masse
boxes_data = [
    {'name': '1G08', 'floor': 'RDC', 'width': 240, 'depth': 200, 'height': 250, 
     'price': 91, 'status': 'occupe', 'row': 1, 'col': 1},
    {'name': '1G09', 'floor': 'RDC', 'width': 240, 'depth': 200, 'height': 250, 
     'price': 91, 'status': 'occupe', 'row': 1, 'col': 2},
    # ... etc
]

# Dans Odoo shell ou script
for data in boxes_data:
    floor = env['storage.floor'].search([('code', '=', data['floor'])], limit=1)
    env['storage.box'].create({
        'name': data['name'],
        'floor_id': floor.id,
        'width': data['width'],
        'depth': data['depth'],
        'height': data['height'],
        'price_monthly': data['price'],
        'status': data['status'],
        'grid_row': data['row'],
        'grid_col': data['col'],
    })
```

### 5. Importer depuis CSV/Excel

1. Préparer un fichier CSV avec ces colonnes :
```csv
name,floor_code,width,depth,height,price_monthly,status,grid_row,grid_col
1G08,RDC,240,200,250,91,occupe,1,1
1G09,RDC,240,200,250,91,occupe,1,2
1D20,RDC,250,200,250,85,disponible,1,3
...
```

2. Utiliser un script Python pour importer :

```python
import csv

# Lire le CSV
with open('boxes.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        floor = env['storage.floor'].search([('code', '=', row['floor_code'])], limit=1)
        if floor:
            env['storage.box'].create({
                'name': row['name'],
                'floor_id': floor.id,
                'width': float(row['width']),
                'depth': float(row['depth']),
                'height': float(row['height']),
                'price_monthly': float(row['price_monthly']),
                'status': row['status'],
                'grid_row': int(row['grid_row']),
                'grid_col': int(row['grid_col']),
            })
```

### 6. Ajuster la grille si nécessaire

Si vous avez beaucoup de boxes, vous devrez peut-être ajuster la grille dans le CSS :

```css
/* Dans static/src/css/storage_plan.css */

.floor-plan[data-floor-code="RDC"] {
    grid-template-columns: repeat(6, 1fr); /* Augmenter de 5 à 6 colonnes */
    grid-template-rows: repeat(15, 80px);  /* Ajuster le nombre de lignes */
}
```

### 7. Zones spéciales (WC, TECH, etc.)

Pour les zones qui ne sont pas des boxes louables :

```xml
<record id="zone_wc" model="storage.box">
    <field name="name">WC</field>
    <field name="floor_id" ref="floor_ground"/>
    <field name="width">150</field>
    <field name="depth">150</field>
    <field name="height">250</field>
    <field name="price_monthly">0</field>
    <field name="status">technique</field>
    <field name="grid_row">10</field>
    <field name="grid_col">4</field>
    <field name="active">False</field> <!-- Pas affiché publiquement -->
</record>
```

### 8. Conseils pour un plan optimal

1. **Regroupez par zones logiques** : Gardez les numéros de boxes proches physiquement dans la grille
2. **Utilisez des statuts cohérents** : Assurez-vous que les statuts correspondent à la réalité
3. **Testez la grille** : Vérifiez l'affichage sur différentes tailles d'écran
4. **Ajoutez des descriptions** : Utilisez le champ `description` pour des infos spécifiques

### 9. Migration depuis votre système actuel

Si vous avez déjà un système :

1. Exportez vos données actuelles
2. Mappez les champs vers le modèle Odoo
3. Créez un script d'import
4. Testez sur une instance de développement
5. Validez les données importées
6. Importez en production

### 10. Exemple complet pour reproduire vos captures

Basé sur vos images, voici comment structurer :

```python
# Rez-de-chaussée - Organisation visible
boxes_rdc = {
    # Ligne 1
    (1, 1): {'name': '1G08', 'width': 240, 'depth': 200, 'price': 91, 'status': 'occupe'},
    (1, 2): {'name': '1G09', 'width': 240, 'depth': 200, 'price': 91, 'status': 'occupe'},
    (1, 3): {'name': '1D20', 'width': 250, 'depth': 200, 'price': 85, 'status': 'disponible'},
    (1, 4): {'name': '1D24', 'width': 240, 'depth': 200, 'price': 91, 'status': 'occupe'},
    (1, 5): {'name': '1D23', 'width': 300, 'depth': 200, 'price': 110, 'status': 'occupe'},
    # ... continuez
}

# Premier étage
boxes_r1 = {
    (1, 3): {'name': '2D61', 'width': 250, 'depth': 200, 'price': 88, 'status': 'occupe'},
    (1, 4): {'name': '2D62', 'width': 250, 'depth': 220, 'price': 90, 'status': 'occupe'},
    # ... continuez
}

# Import
floor_rdc = env['storage.floor'].search([('code', '=', 'RDC')], limit=1)
for (row, col), data in boxes_rdc.items():
    env['storage.box'].create({
        'name': data['name'],
        'floor_id': floor_rdc.id,
        'width': data['width'],
        'depth': data['depth'],
        'height': 250,  # Par défaut
        'price_monthly': data['price'],
        'status': data['status'],
        'grid_row': row,
        'grid_col': col,
    })
```

## Support

Pour toute question sur l'implémentation :
- Email : contact@lolirine.be
- Documentation complète dans le README.md
