# Script à exécuter dans le shell Odoo.sh pour assigner les produits existants

# ============================================================================
# COMMANDE À EXÉCUTER DANS LE SHELL ODOO.SH
# ============================================================================

# 1. Connecte-toi au shell Odoo.sh de ton projet
# 2. Lance le shell Python : odoo-bin shell -d <nom_base>
# 3. Copie-colle les commandes ci-dessous

# --- DÉBUT DU SCRIPT ---

# Trouver le site Pool Store
Website = env['website']
pool_website = Website.search([
    '|',
    ('name', 'ilike', 'Pool Store'),
    ('name', 'ilike', 'Lolirine Pool'),
], limit=1)

if pool_website:
    print(f"✅ Site Pool Store trouvé: ID={pool_website.id}, nom={pool_website.name}")
    
    # Trouver tous les produits piscine sans website_id assigné
    ProductTemplate = env['product.template']
    
    # Option 1: Tous les produits marqués is_pool_product
    pool_products = ProductTemplate.search([
        ('is_pool_product', '=', True),
        '|',
        ('website_id', '=', False),
        ('website_id', '!=', pool_website.id),
    ])
    
    if pool_products:
        print(f"📦 {len(pool_products)} produits piscine trouvés sans assignation correcte")
        pool_products.write({'website_id': pool_website.id})
        env.cr.commit()
        print(f"✅ {len(pool_products)} produits assignés au Pool Store!")
    else:
        print("ℹ️ Tous les produits piscine sont déjà correctement assignés")
        
    # Option 2: Produits avec default_code commençant par POOL-
    pool_products_by_ref = ProductTemplate.search([
        ('default_code', 'ilike', 'POOL-%'),
        '|',
        ('website_id', '=', False),
        ('website_id', '!=', pool_website.id),
    ])
    
    if pool_products_by_ref:
        print(f"📦 {len(pool_products_by_ref)} produits POOL-* trouvés")
        pool_products_by_ref.write({
            'website_id': pool_website.id,
            'is_pool_product': True,
        })
        env.cr.commit()
        print(f"✅ {len(pool_products_by_ref)} produits POOL-* assignés!")
        
else:
    print("❌ Site Pool Store non trouvé!")
    print("Sites disponibles:")
    for w in Website.search([]):
        print(f"  - ID={w.id}: {w.name} ({w.domain or 'pas de domaine'})")

# --- FIN DU SCRIPT ---

# ============================================================================
# VÉRIFICATION
# ============================================================================

# Pour vérifier que tout est bien assigné :
pool_website = env['website'].search([('name', 'ilike', 'Pool')], limit=1)
if pool_website:
    count = env['product.template'].search_count([
        ('website_id', '=', pool_website.id)
    ])
    print(f"📊 {count} produits sont assignés au site Pool Store")
