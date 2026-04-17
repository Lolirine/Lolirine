#!/bin/bash
# Deploy script for lolirine_pool_import_extended
# Run this from /home/odoo/src/user/

echo "🚀 Déploiement lolirine_pool_import_extended"
echo "============================================="

# 1. Vérification prérequis
echo "1️⃣ Vérification prérequis Python..."
python3 -c "import fitz; print('✅ PyMuPDF OK')" 2>/dev/null || echo "❌ PyMuPDF manquant"
python3 -c "import cv2; print('✅ OpenCV OK')" 2>/dev/null || echo "❌ OpenCV manquant" 
python3 -c "import PIL; print('✅ Pillow OK')" 2>/dev/null || echo "❌ Pillow manquant"
python3 -c "import numpy; print('✅ NumPy OK')" 2>/dev/null || echo "❌ NumPy manquant"

# 2. Vérification module parent
echo -e "\n2️⃣ Vérification module parent..."
if [ -d "lolirine_pool_import" ]; then
    echo "✅ lolirine_pool_import trouvé"
else
    echo "❌ ERREUR: Module parent lolirine_pool_import non trouvé"
    echo "   Assurez-vous qu'il est installé dans /home/odoo/src/user/"
    exit 1
fi

# 3. Activation dépendance
echo -e "\n3️⃣ Activation dépendance dans __manifest__.py..."
if grep -q "# 'lolirine_pool_import'" lolirine_pool_import_extended/__manifest__.py; then
    sed -i "s/# 'lolirine_pool_import',/'lolirine_pool_import',/" lolirine_pool_import_extended/__manifest__.py
    echo "✅ Dépendance activée"
else
    echo "✅ Dépendance déjà active"
fi

# 4. Vérification permissions
echo -e "\n4️⃣ Vérification permissions..."
chmod -R 755 lolirine_pool_import_extended/
echo "✅ Permissions définies"

# 5. Restart Odoo
echo -e "\n5️⃣ Instructions finales:"
echo "   • Redémarrer Odoo (odoo-restart ou depuis le dashboard)"
echo "   • Apps → Rechercher 'Image Extraction' → Installer"
echo "   • Ventes → Pool Store → Imports PDF → Test extraction"

echo -e "\n🎉 Déploiement prêt !"
echo "   📖 Voir README.md pour le guide d'utilisation complet"
