# lolirine_seo_tracking — SEO & Trafic du Pool Store

Menu : **Site Web > SEO & Trafic**

| Écran | Contenu |
|---|---|
| Tableau de bord | KPI, sources, moteurs, IA, pages d'entrée, mots-clés Google, opportunités, 404, audit, appareils |
| Visites par source | Graphique / pivot des entrées sur le site par type de source et par source |
| Pages vues | Pages les plus consultées |
| Commandes par source | Commandes confirmées attribuées à la source de la visite |
| Mots-clés Google | Données Search Console (requête × page × jour × pays × appareil) |
| Opportunités SEO | Requêtes 28 j classées : CTR faible, position 4-10, page 2 |
| Audit SEO | Méta manquantes/trop longues/doublons, contenu court, images, URL, catégories vides, traductions |
| Pages 404 | URL cassées vues par visiteurs et robots, bouton « Créer la 301 » |
| Réglages | Search Console, destinataire du rapport, IndexNow, boutons d'action |

## Mesure
* Balise JS sans cookie (`seo_beacon.interaction.js`) → `POST /lolirine_seo/hit` (204).
* Pas d'IP, pas d'identifiant ; la source d'entrée est gardée en `sessionStorage`.
* Robots ignorés, 60 hits/min/IP max, sites filtrés par `lolirine_seo.website_ids` (défaut 6).
* 404 journalisées via `ir.http._handle_error` (curseur dédié, ne casse jamais la page).

## Tâches planifiées
* 05:17 — import Search Console (4 derniers jours recalculés ; 90 jours au 1er import)
* 04:43 — IndexNow des fiches/pages modifiées depuis 26 h
* lundi 06:23 — audit SEO + rapport hebdomadaire par e-mail

## Installation
Apps > mettre à jour la liste > installer « Lolirine — SEO & Trafic ».
Le hook remplit le robots.txt du site **seulement s'il est vide**.

## Données structurées (19.0.1.1.0)
Sur les sites suivis, le bloc `Organization` générique de website_sale (nom et logo de la
société) est remplacé par un graphe `OnlineStore` + `WebSite` : nom et logo du site, réseaux
sociaux du site, téléphone, adresse de contact, horaires, société exploitante (Lolirine SRL).
Valeurs réglables par paramètres système `lolirine_seo.org_street`, `org_zip`, `org_city`,
`org_country`, `org_phone`, `org_legal_name`, `org_vat`, `org_hours_week`,
`org_hours_saturday` (vide = non publié).
