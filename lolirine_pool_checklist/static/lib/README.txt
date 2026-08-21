Ce dossier doit contenir les trois librairies servies localement :

    react.production.min.js        (~11 Ko)
    react-dom.production.min.js    (~130 Ko)
    babel.min.js                   (~2,9 Mo)

Elles ne sont PAS incluses dans ce zip (poids). Pour les récupérer,
depuis la racine du module :

    ./tools/vendor_libs.sh

Le script télécharge les versions épinglées, contrôle taille et contenu,
et écrit un VERSIONS.txt expliquant pourquoi elles sont ici.

Tant que ces fichiers sont absents, /visite-chantier affichera un
encadré rouge « Babel ne s'est pas chargé » — pas une page blanche.
