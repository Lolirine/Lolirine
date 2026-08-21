#!/usr/bin/env bash
#
# vendor_libs.sh — Rapatrie React / ReactDOM / Babel standalone dans le module
#
# À lancer depuis n'importe où : le script se repère tout seul s'il est
# placé dans <module>/tools/. Sinon, exportez MODULE_DIR avant l'appel :
#     MODULE_DIR=~/repos/lolirine/lolirine_pool_checklist ./vendor_libs.sh
#
set -euo pipefail

# ── Versions épinglées ────────────────────────────────────────────────
REACT_VERSION="18.3.1"
BABEL_VERSION="7.26.4"

# ── Localisation du module ────────────────────────────────────────────
if [ -n "${MODULE_DIR:-}" ]; then
    MOD="$MODULE_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    MOD="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

if [ ! -f "$MOD/__manifest__.py" ]; then
    echo "✗ __manifest__.py introuvable dans : $MOD"
    echo "  Relancez avec  MODULE_DIR=/chemin/vers/lolirine_pool_checklist $0"
    exit 1
fi

LIB="$MOD/static/lib"
mkdir -p "$LIB"
echo "→ Module : $MOD"
echo "→ Cible  : $LIB"
echo

# ── Téléchargement + contrôle ─────────────────────────────────────────
# $1 = URL, $2 = nom de fichier local, $3 = taille minimale attendue (octets)
fetch() {
    local url="$1" out="$2" minsize="$3"
    local dest="$LIB/$out"
    echo "  ↓ $out"
    if ! curl -fsSL --retry 3 --connect-timeout 20 "$url" -o "$dest.tmp"; then
        echo "    ✗ échec du téléchargement : $url"
        rm -f "$dest.tmp"
        return 1
    fi
    local size
    size=$(wc -c < "$dest.tmp" | tr -d ' ')
    if [ "$size" -lt "$minsize" ]; then
        echo "    ✗ fichier suspect ($size octets, attendu > $minsize) — page d'erreur du CDN ?"
        rm -f "$dest.tmp"
        return 1
    fi
    # Un fichier HTML récupéré par erreur commencerait par < ou un BOM
    if head -c 200 "$dest.tmp" | grep -qi '<!doctype\|<html'; then
        echo "    ✗ contenu HTML au lieu de JavaScript — URL invalide ?"
        rm -f "$dest.tmp"
        return 1
    fi
    mv "$dest.tmp" "$dest"
    echo "    ✓ $(printf "%'d" "$size") octets"
}

echo "Téléchargement des librairies…"
fetch "https://unpkg.com/react@${REACT_VERSION}/umd/react.production.min.js" \
      "react.production.min.js" 8000
fetch "https://unpkg.com/react-dom@${REACT_VERSION}/umd/react-dom.production.min.js" \
      "react-dom.production.min.js" 100000
fetch "https://unpkg.com/@babel/standalone@${BABEL_VERSION}/babel.min.js" \
      "babel.min.js" 1000000
echo

# ── Vérification fonctionnelle sommaire ───────────────────────────────
echo "Contrôles de contenu…"
grep -q "createElement" "$LIB/react.production.min.js" \
    && echo "  ✓ react : createElement présent" \
    || { echo "  ✗ react : contenu inattendu"; exit 1; }
grep -q "createRoot" "$LIB/react-dom.production.min.js" \
    && echo "  ✓ react-dom : createRoot présent" \
    || { echo "  ✗ react-dom : contenu inattendu"; exit 1; }
grep -q "transform" "$LIB/babel.min.js" \
    && echo "  ✓ babel : transform présent" \
    || { echo "  ✗ babel : contenu inattendu"; exit 1; }
echo

# ── Trace de version, utile dans six mois ─────────────────────────────
cat > "$LIB/VERSIONS.txt" <<EOF
Librairies rapatriées pour lolirine_pool_checklist
Rapatriées le : $(date '+%Y-%m-%d %H:%M')

react                 ${REACT_VERSION}   (UMD, production)
react-dom             ${REACT_VERSION}   (UMD, production)
@babel/standalone     ${BABEL_VERSION}

Pourquoi ces fichiers sont ici plutôt qu'appelés sur unpkg :
en juin 2026 le preset React de @babel/standalone est passé au JSX
runtime "automatic" par défaut. Le code transpilé contenait alors un
import ESM impossible à injecter comme script classique, et la page
/visite-chantier est devenue blanche sans qu'aucune ligne du module
n'ait changé. Les fichiers locaux suppriment cette dépendance et
permettent aussi de travailler sur chantier sans réseau fiable.

Pour mettre à jour : modifier les versions en tête de tools/vendor_libs.sh
et relancer le script. Tester /visite-chantier avant de pousser.
EOF
echo "  ✓ VERSIONS.txt écrit"
echo

# ── Récapitulatif ─────────────────────────────────────────────────────
echo "Contenu de static/lib :"
ls -lh "$LIB" | tail -n +2 | awk '{printf "  %-36s %s\n", $9, $5}'
echo
TOTAL=$(du -sh "$LIB" | cut -f1)
echo "Total : $TOTAL"
echo
echo "Étapes suivantes :"
echo "  1. Remplacer views/templates.xml par la version fournie"
echo "  2. git add static/lib tools/vendor_libs.sh views/templates.xml"
echo "  3. git commit -m 'Rapatriement React/Babel en local + fiche vierge imprimable'"
echo "  4. git push  →  Upgrade du module  →  purge des assets  →  Cmd+Shift+R"
