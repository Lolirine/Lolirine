/** @odoo-module **/

/*
 * motion_helpers.js
 * Point d'accès unique au moteur Motion + tokens partagés.
 * Centraliser ici garantit une "signature" d'animation cohérente sur tout le site.
 */

// La lib UMD expose window.Motion (animate, inView, stagger, hover, press, scroll...).
export function getMotion() {
    return typeof window !== "undefined" ? window.Motion || null : null;
}

// Accessibilité : on n'anime pas si l'utilisateur a demandé moins de mouvement.
export function prefersReducedMotion() {
    try {
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch {
        return false;
    }
}

// True si on peut réellement animer (lib présente ET mouvement autorisé).
export function canAnimate() {
    return !!getMotion() && !prefersReducedMotion();
}

/*
 * Tokens de mouvement — la "charte" d'animation.
 * On ajuste ICI pour changer le ressenti de tout le site d'un coup.
 */
export const MOTION = {
    // Courbes (cubic-bezier). expoOut = entrée nette puis ralentissement doux.
    easeExpoOut: [0.16, 1, 0.3, 1],
    easeSoft: [0.4, 0, 0.2, 1],
    easeBack: [0.34, 1.56, 0.64, 1], // léger rebond pour le "press"
    // Durées (secondes)
    dur: 0.6,
    durFast: 0.32,
    durSlow: 0.9,
    // Cascade par défaut entre items
    stagger: 0.08,
    // Translation par défaut d'un reveal (px)
    distance: 24,
};

// Petit util : lit un data-attribut numérique avec valeur par défaut.
export function dataNum(el, key, fallback) {
    const v = parseFloat(el.dataset[key]);
    return Number.isFinite(v) ? v : fallback;
}
