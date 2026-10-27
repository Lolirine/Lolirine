/** @odoo-module **/
/*
 * Boutique : en changeant de catégorie, on repart sans filtres.
 * Odoo garde dans les liens de catégorie les filtres de la page en cours
 * (attribute_values, prix min/max). Après un clic sur la pastille « Gris » des
 * minipiscines Laghetto, le lien « Spas Treesse » emportait ce filtre et la
 * catégorie paraissait vide. Les liens vers une AUTRE catégorie sont nettoyés ;
 * la pagination de la catégorie en cours garde ses filtres.
 */
const PARAMS = ["attribute_values", "attrib", "min_price", "max_price"];
const catId = (path) => {
    const m = path.match(/\/shop\/category\/(?:[^/?#]*-)?(\d+)/);
    return m ? m[1] : null;
};

function nettoyer() {
    const courante = catId(window.location.pathname);
    document.querySelectorAll('a[href*="/shop/category/"]').forEach((a) => {
        let url;
        try {
            url = new URL(a.getAttribute("href"), window.location.origin);
        } catch {
            return;
        }
        if (url.origin !== window.location.origin || catId(url.pathname) === courante) {
            return;
        }
        if (!PARAMS.some((p) => url.searchParams.has(p))) {
            return;
        }
        PARAMS.forEach((p) => url.searchParams.delete(p));
        a.setAttribute("href", url.pathname + url.search + url.hash);
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", nettoyer);
} else {
    nettoyer();
}
