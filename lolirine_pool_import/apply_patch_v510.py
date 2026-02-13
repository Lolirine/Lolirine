#!/usr/bin/env python3
"""
Script d'application du patch v5.1.0 - Détection automatique des accessoires OCR
Usage: python3 apply_patch_v510.py pool_catalog_extraction.py
"""

import sys
import re
import shutil
from datetime import datetime

def apply_patch(filepath):
    """Applique toutes les modifications v5.1.0 au fichier."""
    
    # Créer une sauvegarde
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(filepath, backup_path)
    print(f"✅ Sauvegarde créée: {backup_path}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modifications = 0
    
    # =============================================
    # MODIFICATION 1: Nouveaux champs accessory_refs et accessory_names
    # =============================================
    if 'accessory_refs = fields.Text' not in content:
        # Trouver country_of_origin et ajouter après
        pattern = r"(country_of_origin = fields\.Char\([^)]+\))"
        replacement = r'''\1
    
    # =============================================
    # ACCESSOIRES DÉTECTÉS PAR OCR (v5.1.0)
    # =============================================
    accessory_refs = fields.Text(
        string='Références accessoires',
        help="JSON: références des accessoires détectés sur la page catalogue"
    )
    accessory_names = fields.Text(
        string='Noms accessoires',
        help="Noms des accessoires pour recherche si référence introuvable"
    )'''
        
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            content = new_content
            modifications += 1
            print("✅ Modification 1: Champs accessory_refs et accessory_names ajoutés")
        else:
            print("⚠️ Modification 1: Pattern non trouvé (country_of_origin)")
    else:
        print("ℹ️ Modification 1: Déjà appliquée")
    
    # =============================================
    # MODIFICATION 2: Extension du prompt JSON avec related_accessories
    # =============================================
    if '"related_accessories":' not in content:
        # Trouver detected_images et ajouter après
        pattern = r'("detected_images": \[\s*\{[^}]+\}\s*\],)'
        replacement = r'''\1
    "related_accessories": [
        {
            "reference": "référence de l'accessoire (ex: ACC-001, 12345)",
            "name": "nom complet de l'accessoire si visible",
            "type": "type d'accessoire (couverture, marche, appuie-tête, filtre, chariot, câble, brosse, housse, kit, télécommande, transformateur, vanne, support, etc.)"
        }
    ],'''
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        if new_content != content:
            content = new_content
            modifications += 1
            print("✅ Modification 2: related_accessories ajouté au prompt JSON")
        else:
            print("⚠️ Modification 2: Pattern non trouvé (detected_images)")
    else:
        print("ℹ️ Modification 2: Déjà appliquée")
    
    # =============================================
    # MODIFICATION 3: Instructions accessoires dans le prompt
    # =============================================
    if 'DÉTECTION DES ACCESSOIRES ASSOCIÉS' not in content:
        pattern = r"(Réponds UNIQUEMENT avec le JSON)"
        replacement = r'''DÉTECTION DES ACCESSOIRES ASSOCIÉS - IMPORTANT:
Cherche sur la page les mentions d'accessoires compatibles, options, articles associés, pièces détachées.
Types courants par catégorie:
- SPAS: couvertures thermiques, marches, appuie-têtes, kits d'entretien, coussins
- POMPES À CHALEUR: housses de protection, supports, kits hydrauliques, by-pass
- ROBOTS: chariots de transport, câbles de remplacement, brosses, filtres, sacs
- FILTRES: vannes multivoies, crépines, joints, manomètres
- PROJECTEURS: transformateurs, télécommandes, niches
Extrais les références ET les noms des accessoires mentionnés.
Si aucun accessoire n'est visible/mentionné, retourne "related_accessories": []

EXEMPLE pour les accessoires détectés:
Si tu vois sur la page d'un spa des mentions d'accessoires compatibles:
"related_accessories": [
    {"reference": "COV-J355", "name": "Couverture thermique J-355", "type": "couverture"},
    {"reference": "STP-2", "name": "Marche d'accès 2 niveaux", "type": "marche"},
    {"reference": null, "name": "Appuie-tête premium", "type": "appuie-tête"}
]

\1'''
        
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            content = new_content
            modifications += 1
            print("✅ Modification 3: Instructions accessoires ajoutées au prompt")
        else:
            print("⚠️ Modification 3: Pattern non trouvé")
    else:
        print("ℹ️ Modification 3: Déjà appliquée")
    
    # =============================================
    # MODIFICATION 4: Traitement accessoires dans _process_extraction_result
    # =============================================
    if "vals['accessory_refs']" not in content:
        # Chercher où ajouter le traitement des accessoires
        pattern = r"(vals = \{\s*'extraction_id': self\.id,[\s\S]*?'selling_price': self\._parse_price\(prod\.get\('selling_price'\)\),\s*\})"
        
        # Ajouter après le bloc vals initial
        replacement = r'''\1
            
            # Récupérer et stocker les accessoires détectés (v5.1.0)
            related_accessories = data.get('related_accessories', [])
            if related_accessories:
                vals['accessory_refs'] = json.dumps(related_accessories, ensure_ascii=False)
                accessory_names = [acc.get('name', '') for acc in related_accessories if acc.get('name')]
                if accessory_names:
                    vals['accessory_names'] = ', '.join(accessory_names)
                _logger.info(f"📦 {len(related_accessories)} accessoire(s) détecté(s)")'''
        
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            content = new_content
            modifications += 1
            print("✅ Modification 4: Traitement accessoires dans _process_extraction_result")
        else:
            print("⚠️ Modification 4: Pattern non trouvé - ajout manuel requis")
    else:
        print("ℹ️ Modification 4: Déjà appliquée")
    
    # =============================================
    # MODIFICATION 5: Méthode _link_accessories
    # =============================================
    if 'def _link_accessories' not in content:
        # Trouver _add_product_image et ajouter après
        link_accessories_method = '''
    def _link_accessories(self, product):
        """
        Recherche et lie les accessoires détectés au produit Odoo.
        Utilise le champ accessory_product_ids (Produits accessoires).
        
        Args:
            product: product.template créé ou mis à jour
        """
        self.ensure_one()
        
        if not self.accessory_refs:
            return
        
        try:
            accessories_data = json.loads(self.accessory_refs)
        except (json.JSONDecodeError, TypeError):
            _logger.warning(f"Impossible de parser accessory_refs")
            return
        
        if not accessories_data:
            return
        
        _logger.info(f"🔍 Recherche de {len(accessories_data)} accessoire(s) pour '{product.name}'")
        
        ProductTemplate = self.env['product.template']
        linked_ids = []
        not_found = []
        
        for acc in accessories_data:
            ref = (acc.get('reference') or '').strip()
            name = (acc.get('name') or '').strip()
            acc_type = (acc.get('type') or '').strip().lower()
            
            accessory_product = False
            
            # 1. Recherche par RÉFÉRENCE
            if ref:
                accessory_product = ProductTemplate.search([
                    '|', '|', '|',
                    ('default_code', '=', ref),
                    ('default_code', '=', f'POOL-{ref}'),
                    ('x_pool_supplier_ref', '=', ref),
                    ('default_code', 'ilike', ref),
                ], limit=1)
                if accessory_product:
                    _logger.info(f"  ✓ Trouvé par ref '{ref}': {accessory_product.name}")
            
            # 2. Recherche par NOM
            if not accessory_product and name:
                accessory_product = ProductTemplate.search([
                    ('name', '=ilike', name),
                    ('sale_ok', '=', True),
                ], limit=1)
                
                if not accessory_product:
                    keywords = [w for w in name.split() if len(w) > 3]
                    if len(keywords) >= 2:
                        domain = [('sale_ok', '=', True)]
                        for kw in keywords[:3]:
                            domain.append(('name', 'ilike', kw))
                        accessory_product = ProductTemplate.search(domain, limit=1)
                
                if accessory_product:
                    _logger.info(f"  ✓ Trouvé par nom '{name}': {accessory_product.name}")
            
            # 3. Recherche par TYPE
            if not accessory_product and acc_type:
                type_keywords = {
                    'couverture': ['couverture', 'cover', 'bâche'],
                    'marche': ['marche', 'step', 'escalier'],
                    'appuie-tête': ['appuie-tête', 'appui-tête', 'headrest'],
                    'filtre': ['filtre', 'cartouche', 'filter'],
                    'chariot': ['chariot', 'caddy', 'transport'],
                    'câble': ['câble', 'cable', 'cordon'],
                    'brosse': ['brosse', 'brush'],
                    'housse': ['housse', 'protection'],
                    'kit': ['kit', 'ensemble', 'set'],
                    'télécommande': ['télécommande', 'remote'],
                    'transformateur': ['transformateur', 'transfo'],
                    'vanne': ['vanne', 'valve'],
                    'support': ['support', 'socle', 'pied'],
                }
                
                search_words = type_keywords.get(acc_type, [acc_type])
                for keyword in search_words:
                    accessory_product = ProductTemplate.search([
                        ('name', 'ilike', keyword),
                        ('sale_ok', '=', True),
                    ], limit=1)
                    if accessory_product:
                        _logger.info(f"  ✓ Trouvé par type '{acc_type}': {accessory_product.name}")
                        break
            
            if accessory_product:
                if accessory_product.id not in linked_ids and accessory_product.id != product.id:
                    linked_ids.append(accessory_product.id)
            else:
                not_found.append({'ref': ref, 'name': name, 'type': acc_type})
        
        # Lier les accessoires
        if linked_ids:
            existing_ids = product.accessory_product_ids.ids if product.accessory_product_ids else []
            all_ids = list(set(existing_ids + linked_ids))
            
            try:
                product.write({'accessory_product_ids': [(6, 0, all_ids)]})
                _logger.info(f"🔗 {len(linked_ids)} accessoire(s) lié(s) à '{product.name}'")
            except Exception as e:
                _logger.warning(f"Erreur liaison accessoires: {e}")
        
        if not_found:
            _logger.info(f"⚠️ {len(not_found)} accessoire(s) non trouvé(s)")
'''
        
        # Chercher la fin de _add_product_image
        pattern = r"(if images_added > 0:\s*_logger\.info\(f\"✅ \{images_added\} image\(s\) ajoutée\(s\) au produit \{product\.name\}\"\))"
        replacement = r'\1' + link_accessories_method
        
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            content = new_content
            modifications += 1
            print("✅ Modification 5: Méthode _link_accessories ajoutée")
        else:
            print("⚠️ Modification 5: Pattern non trouvé - ajout manuel requis")
    else:
        print("ℹ️ Modification 5: Déjà appliquée")
    
    # =============================================
    # MODIFICATION 6a: Appel _link_accessories dans action_import_to_odoo
    # =============================================
    if 'self._link_accessories(product)' not in content:
        pattern = r"(self\._add_product_image\(product\)\s*\n)"
        replacement = r'''\1
            # Lier les accessoires détectés par l'OCR (v5.1.0)
            self._link_accessories(product)
'''
        
        new_content = re.sub(pattern, replacement, content, count=1)
        if new_content != content:
            content = new_content
            modifications += 1
            print("✅ Modification 6a: Appel _link_accessories dans action_import_to_odoo")
        else:
            print("⚠️ Modification 6a: Pattern non trouvé")
    else:
        print("ℹ️ Modification 6a: Déjà appliquée")
    
    # =============================================
    # MODIFICATION 6b: Appel dans _import_as_single_product_with_variants
    # =============================================
    if 'products_to_import[0]._link_accessories' not in content:
        pattern = r"(products_to_import\[0\]\._add_product_image\(template\))"
        replacement = r'''\1
            
            # Lier les accessoires (depuis le premier produit extrait) (v5.1.0)
            if products_to_import:
                products_to_import[0]._link_accessories(template)'''
        
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            content = new_content
            modifications += 1
            print("✅ Modification 6b: Appel _link_accessories dans variantes")
        else:
            print("⚠️ Modification 6b: Pattern non trouvé")
    else:
        print("ℹ️ Modification 6b: Déjà appliquée")
    
    # Écrire le fichier modifié
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n{'='*50}")
    print(f"✅ Patch v5.1.0 appliqué avec {modifications} modification(s)")
    print(f"📁 Fichier modifié: {filepath}")
    print(f"📁 Sauvegarde: {backup_path}")
    print(f"\n⚠️ N'oubliez pas de redémarrer Odoo après le déploiement!")
    
    return modifications

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 apply_patch_v510.py pool_catalog_extraction.py")
        sys.exit(1)
    
    filepath = sys.argv[1]
    try:
        apply_patch(filepath)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)
