/*
 * motion_boot.js — script CLASSIQUE (pas de @odoo-module).
 * Exécuté à l'évaluation du bundle, le plus tôt possible.
 *
 * Rôle :
 *  - Marque <html> comme "prêt à animer" => le SCSS peut pré-masquer les
 *    éléments à révéler SANS risque de les laisser cachés si le JS est absent
 *    (la classe n'est jamais ajoutée si ce script ne tourne pas).
 *  - Pose un failsafe : si pour une raison quelconque les interactions ne
 *    révèlent jamais le contenu (erreur JS, lib manquante), tout réapparaît
 *    après un délai. Aucun contenu ne peut rester invisible.
 */
(function () {
    "use strict";
    var root = document.documentElement;
    root.classList.add("o_motion_ready");
    window.setTimeout(function () {
        root.classList.add("o_motion_failsafe");
    }, 4000);
})();
