/*
 * pool_nav.js : navigation enrichie du Pool Store (site 6 uniquement).
 *
 *  1. Bandeau de navigation sous la barre de confiance (rayons, promotions,
 *     nouveautes, racheter, commandes, listes, bascule de prix HTVA/TVAC).
 *  2. Tiroir "Tous les rayons" + recherche limitee a un rayon.
 *  3. Listes : nombre de resultats, choix de quantite sur les tuiles,
 *     prix HTVA sur les tuiles en mode professionnel.
 *  4. Fiche produit : prix degressifs, "Frequemment achetes ensemble",
 *     tableau comparatif avec les produits alternatifs.
 *  5. Panier : demande de devis.
 *  6. Tunnel de commande : date de livraison rappelee, garanties, pays.
 *  7. Confirmation : la suite de la commande, le suivi, les complements.
 *
 * Script classique (pas de module) : tout est rendu ici a partir des routes
 * JSON /lolirine_nav/*. Chaque bloc est independant et reste masque si sa
 * route echoue. Les blocs places dans la page sont retires des que l'editeur
 * du site s'ouvre, pour ne jamais etre enregistres dans une vue.
 */
(function () {
    "use strict";

    if (window.__lolirinePoolNavStarted) {
        return;
    }
    window.__lolirinePoolNavStarted = true;

    var html = document.documentElement;
    var LANG = (html.lang || "fr").slice(0, 2).toLowerCase();
    var LOCALE = LANG === "nl" ? "nl-BE" : LANG === "en" ? "en-GB" : "fr-BE";
    var MODE_KEY = "lolirine_price_mode";

    function t(fr, nl, en) {
        return LANG === "nl" ? nl : LANG === "en" ? en : fr;
    }

    // Prefixe de langue de l'adresse courante (/nl, /en...), a conserver.
    var PREFIX = (function () {
        var m = window.location.pathname.match(/^\/(nl|en|fr)(_[A-Z]{2})?(?=\/|$)/);
        return m ? m[0] : "";
    })();

    function L(path) {
        return PREFIX + path;
    }

    function money(amount) {
        try {
            return new Intl.NumberFormat(LOCALE, { style: "currency", currency: "EUR" }).format(
                amount || 0
            );
        } catch (e) {
            return (amount || 0).toFixed(2) + " €";
        }
    }

    function el(tag, cls, text) {
        var node = document.createElement(tag);
        if (cls) {
            node.className = cls;
        }
        if (text !== undefined && text !== null) {
            node.textContent = text;
        }
        return node;
    }

    // Bloc place dans la page : jamais editable, retire a l'ouverture de l'editeur.
    function guard(node) {
        node.classList.add("lp-nav-injected", "o_not_editable");
        node.setAttribute("contenteditable", "false");
        return node;
    }

    function getJSON(url) {
        return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } }).then(function (r) {
            return r.json();
        });
    }

    function rpc(route, params) {
        return fetch(route, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: params || {} }),
        })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                if (data.error) {
                    throw new Error((data.error.data && data.error.data.message) || "RPC");
                }
                return data.result;
            });
    }

    function priceMode() {
        try {
            return window.localStorage.getItem(MODE_KEY) === "ht" ? "ht" : "ttc";
        } catch (e) {
            return "ttc";
        }
    }

    function setPriceMode(mode) {
        try {
            window.localStorage.setItem(MODE_KEY, mode);
        } catch (e) {
            /* stockage indisponible : le choix vaut pour la page */
        }
        html.setAttribute("data-lp-price", mode);
        document.dispatchEvent(new CustomEvent("lp-price-mode", { detail: mode }));
    }

    function setCartBadge(count) {
        document.querySelectorAll(".my_cart_quantity").forEach(function (badge) {
            badge.textContent = count;
            badge.classList.toggle("d-none", !count);
        });
    }

    function inEditor() {
        return document.body.classList.contains("editor_enable");
    }

    /* ================================================================
     * 1. Bandeau de navigation
     * ================================================================ */
    var drawer = null;
    var context = null;

    function buildStrip() {
        var main = document.querySelector("#wrapwrap > main");
        if (!main || document.querySelector(".lp-navstrip")) {
            return;
        }
        var strip = guard(el("nav", "lp-navstrip"));
        strip.setAttribute("aria-label", t("Navigation boutique", "Winkelnavigatie", "Shop navigation"));

        var all = el("button", "lp-navstrip-all");
        all.type = "button";
        all.appendChild(el("i", "fa fa-bars"));
        all.appendChild(el("span", null, t("Tous les rayons", "Alle afdelingen", "All departments")));
        all.addEventListener("click", openDrawer);
        strip.appendChild(all);

        var track = el("div", "lp-navstrip-track");
        [
            [t("Promotions", "Promoties", "Deals"), "/shop/promotions", "fa-tag"],
            [t("Nouveautés", "Nieuw", "New arrivals"), "/shop?order=create_date+desc", "fa-star-o"],
            [t("Acheter à nouveau", "Opnieuw kopen", "Buy again"), "/shop/acheter-a-nouveau", "fa-repeat"],
            [t("Mes commandes", "Mijn bestellingen", "My orders"), "/my/orders", "fa-cube"],
            [t("Mes listes", "Mijn lijsten", "My lists"), "/shop/wishlist", "fa-heart-o"],
            [t("Marques", "Merken", "Brands"), "/marques", "fa-certificate"],
            [t("Calculateur", "Calculator", "Calculator"), "/calculateur-piscine", "fa-calculator"],
        ].forEach(function (item) {
            var a = el("a", "lp-navstrip-link");
            a.href = L(item[1]);
            a.appendChild(el("i", "fa " + item[2]));
            a.appendChild(el("span", null, item[0]));
            track.appendChild(a);
        });
        strip.appendChild(track);

        var side = el("div", "lp-navstrip-side");
        var hello = el("a", "lp-navstrip-hello");
        hello.href = L("/web/login");
        hello.textContent = t("Se connecter", "Aanmelden", "Sign in");
        side.appendChild(hello);

        var toggle = el("div", "lp-pricemode");
        toggle.setAttribute("role", "group");
        toggle.setAttribute("aria-label", t("Affichage des prix", "Prijsweergave", "Price display"));
        [["ttc", t("TVAC", "Incl. btw", "Incl. VAT")], ["ht", t("HTVA", "Excl. btw", "Excl. VAT")]].forEach(
            function (opt) {
                var b = el("button", "lp-pricemode-btn", opt[1]);
                b.type = "button";
                b.dataset.mode = opt[0];
                b.addEventListener("click", function () {
                    setPriceMode(opt[0]);
                });
                toggle.appendChild(b);
            }
        );
        side.appendChild(toggle);
        strip.appendChild(side);

        var trust = main.querySelector(":scope > .lp-trustbar");
        if (trust && trust.nextSibling) {
            main.insertBefore(strip, trust.nextSibling);
        } else {
            main.insertBefore(strip, main.firstChild);
        }
    }

    function refreshHello() {
        var hello = document.querySelector(".lp-navstrip-hello");
        if (hello && context && context.user && context.user.logged) {
            hello.href = L("/my/home");
            hello.textContent = t("Bonjour, ", "Dag ", "Hello, ") + (context.user.name || "");
        }
    }

    /* ================================================================
     * 2. Tiroir des rayons + recherche par rayon
     * ================================================================ */
    function buildDrawer() {
        if (drawer) {
            return drawer;
        }
        drawer = el("div", "lp-catdrawer");
        drawer.setAttribute("aria-hidden", "true");
        var overlay = el("div", "lp-catdrawer-overlay");
        overlay.addEventListener("click", closeDrawer);
        var panel = el("aside", "lp-catdrawer-panel");
        panel.setAttribute("role", "dialog");
        panel.setAttribute("aria-modal", "true");
        panel.setAttribute("aria-label", t("Tous les rayons", "Alle afdelingen", "All departments"));
        var head = el("header", "lp-catdrawer-head");
        head.appendChild(el("span", null, t("Tous les rayons", "Alle afdelingen", "All departments")));
        var close = el("button", "lp-catdrawer-close");
        close.type = "button";
        close.setAttribute("aria-label", t("Fermer", "Sluiten", "Close"));
        close.appendChild(el("i", "fa fa-times"));
        close.addEventListener("click", closeDrawer);
        head.appendChild(close);
        panel.appendChild(head);
        panel.appendChild(el("div", "lp-catdrawer-body"));
        drawer.appendChild(overlay);
        drawer.appendChild(panel);
        document.body.appendChild(drawer);
        document.addEventListener("keydown", function (ev) {
            if (ev.key === "Escape") {
                closeDrawer();
            }
        });
        fillDrawer();
        return drawer;
    }

    function fillDrawer() {
        if (!drawer || !context) {
            return;
        }
        var body = drawer.querySelector(".lp-catdrawer-body");
        body.textContent = "";
        var home = el("a", "lp-catdrawer-top", t("Toute la boutique", "De hele winkel", "The whole shop"));
        home.href = L("/shop");
        body.appendChild(home);
        (context.categories || []).forEach(function (cat) {
            if (!cat.children || !cat.children.length) {
                var solo = el("a", "lp-catdrawer-top", cat.name);
                solo.href = L(cat.url);
                body.appendChild(solo);
                return;
            }
            var group = el("details", "lp-catdrawer-group");
            group.appendChild(el("summary", null, cat.name));
            var list = el("div", "lp-catdrawer-list");
            var every = el("a", "lp-catdrawer-item lp-catdrawer-every",
                t("Tout voir", "Alles bekijken", "See all"));
            every.href = L(cat.url);
            list.appendChild(every);
            cat.children.forEach(function (child) {
                var a = el("a", "lp-catdrawer-item", child.name);
                a.href = L(child.url);
                list.appendChild(a);
            });
            group.appendChild(list);
            body.appendChild(group);
        });
    }

    function openDrawer() {
        buildDrawer();
        drawer.classList.add("is-open");
        drawer.setAttribute("aria-hidden", "false");
    }

    function closeDrawer() {
        if (drawer) {
            drawer.classList.remove("is-open");
            drawer.setAttribute("aria-hidden", "true");
        }
    }

    function buildSearchScope() {
        if (!context || !context.categories || !context.categories.length) {
            return;
        }
        document.querySelectorAll("header form.o_searchbar_form").forEach(function (form) {
            if (form.querySelector(".lp-searchscope")) {
                return;
            }
            var select = guard(el("select", "lp-searchscope form-select form-select-sm"));
            select.setAttribute("aria-label", t("Rechercher dans", "Zoeken in", "Search in"));
            var any = el("option", null, t("Tous les rayons", "Alle afdelingen", "All departments"));
            any.value = "";
            select.appendChild(any);
            context.categories.forEach(function (cat) {
                var opt = el("option", null, cat.name);
                opt.value = cat.id;
                select.appendChild(opt);
            });
            form.insertBefore(select, form.firstChild);
            form.addEventListener("submit", function (ev) {
                var input = form.querySelector('input[name="search"]');
                var query = input ? input.value.trim() : "";
                if (!select.value || !query) {
                    return; // recherche generale : comportement d'origine
                }
                ev.preventDefault();
                window.location.href =
                    L("/shop/category/" + select.value) + "?search=" + encodeURIComponent(query);
            });
        });
    }

    /* ================================================================
     * 3. Listes de produits
     * ================================================================ */
    var tilePrices = {};

    function tiles() {
        return Array.prototype.slice.call(
            document.querySelectorAll("#products_grid .oe_product form.oe_product_cart")
        );
    }

    function tileId(form) {
        var input = form.querySelector('input[name="product_id"]');
        return input ? input.value : null;
    }

    function buildResultCount() {
        var grid = document.querySelector("#products_grid");
        if (!grid || grid.querySelector(".lp-resultcount") || !tiles().length) {
            return;
        }
        var params = new URLSearchParams(window.location.search);
        var cat = window.location.pathname.match(/\/shop\/category\/(?:[^\/?#]*-)?(\d+)/);
        if (cat) {
            params.set("category", cat[1]);
        }
        var page = window.location.pathname.match(/\/page\/(\d+)/);
        getJSON(L("/lolirine_nav/count") + "?" + params.toString())
            .then(function (data) {
                if (!data || typeof data.count !== "number" || inEditor()) {
                    return;
                }
                var line = guard(el("div", "lp-resultcount"));
                var strong = el("strong", null, new Intl.NumberFormat(LOCALE).format(data.count));
                line.appendChild(strong);
                line.appendChild(
                    document.createTextNode(
                        " " + (data.count > 1
                            ? t("produits", "producten", "products")
                            : t("produit", "product", "product"))
                    )
                );
                if (page && parseInt(page[1], 10) > 1) {
                    line.appendChild(
                        document.createTextNode(" · " + t("page ", "pagina ", "page ") + page[1])
                    );
                }
                grid.insertBefore(line, grid.firstChild);
            })
            .catch(function () {});
    }

    function loadTilePrices() {
        var ids = tiles().map(tileId).filter(Boolean);
        if (!ids.length) {
            return Promise.resolve();
        }
        return getJSON(L("/lolirine_nav/prices") + "?ids=" + ids.join(","))
            .then(function (data) {
                tilePrices = (data && data.prices) || {};
            })
            .catch(function () {});
    }

    function buildTileSteppers() {
        tiles().forEach(function (form) {
            var info = tilePrices[tileId(form)];
            var button = form.querySelector(".o_wsale_product_btn_primary");
            var row = form.querySelector(".o_wsale_product_action_row");
            if (!info || !info.simple || !(info.ttc > 0) || !button || !row
                    || form.querySelector(".lp-tileqty")) {
                return;
            }
            var box = guard(el("div", "lp-tileqty"));
            var minus = el("button", "lp-tileqty-btn", "−");
            var value = el("span", "lp-tileqty-val", "1");
            var plus = el("button", "lp-tileqty-btn", "+");
            minus.type = plus.type = "button";
            minus.setAttribute("aria-label", t("Diminuer la quantité", "Minder", "Decrease quantity"));
            plus.setAttribute("aria-label", t("Augmenter la quantité", "Meer", "Increase quantity"));
            var qty = 1;
            function set(n) {
                qty = Math.max(1, Math.min(999, n));
                value.textContent = qty;
            }
            minus.addEventListener("click", function (ev) {
                ev.preventDefault();
                set(qty - 1);
            });
            plus.addEventListener("click", function (ev) {
                ev.preventDefault();
                set(qty + 1);
            });
            box.appendChild(minus);
            box.appendChild(value);
            box.appendChild(plus);
            // Sur sa propre ligne, au-dessus du prix et des boutons de la tuile.
            var sub = form.querySelector(".o_wsale_product_sub");
            if (sub) {
                sub.parentNode.insertBefore(box, sub);
            } else {
                row.parentNode.insertBefore(box, row);
            }

            // Quantite 1 : ajout d'origine d'Odoo. Au-dela : ajout direct de la quantite.
            button.addEventListener(
                "click",
                function (ev) {
                    if (qty <= 1 || box.classList.contains("is-busy")) {
                        return;
                    }
                    ev.preventDefault();
                    ev.stopImmediatePropagation();
                    box.classList.add("is-busy");
                    rpc("/lolirine_motion/cart/add", { product_id: tileId(form), quantity: qty })
                        .then(function (res) {
                            if (res && !res.error) {
                                setCartBadge(res.count);
                                set(1);
                            }
                        })
                        .catch(function () {})
                        .then(function () {
                            box.classList.remove("is-busy");
                        });
                },
                true
            );
        });
    }

    function applyTilePriceMode() {
        var mode = priceMode();
        tiles().forEach(function (form) {
            var info = tilePrices[tileId(form)];
            var price = form.querySelector(".product_price");
            if (!info || !price || !(info.ht > 0)) {
                return;
            }
            var alt = price.querySelector(".lp-tileprice-ht");
            if (mode === "ht") {
                if (!alt) {
                    alt = guard(el("span", "lp-tileprice-ht"));
                    alt.appendChild(el("strong", null, money(info.ht)));
                    alt.appendChild(el("small", null, " " + t("HTVA", "excl. btw", "excl. VAT")));
                    price.appendChild(alt);
                }
                price.classList.add("lp-show-ht");
            } else {
                price.classList.remove("lp-show-ht");
            }
        });
    }

    /* ================================================================
     * 4. Fiche produit
     * ================================================================ */
    function productIds() {
        // Le premier formulaire de la fiche est la barre de recherche : on part
        // du champ cache du formulaire d'achat.
        var tmpl = document.querySelector('#product_detail input[name="product_template_id"]');
        if (!tmpl) {
            return null;
        }
        var form = tmpl.closest("form") || document.querySelector("#product_detail");
        var prod = form.querySelector('input[name="product_id"]');
        return { tmpl: tmpl.value, product: prod ? prod.value : "", form: form };
    }

    function card(item, withCheck, checked) {
        var box = el(withCheck ? "label" : "div", "lp-fbt-item");
        if (withCheck) {
            var check = el("input", "lp-fbt-check");
            check.type = "checkbox";
            check.checked = checked;
            check.value = item.product_id;
            box.appendChild(check);
        }
        var img = el("img");
        img.src = item.image;
        img.alt = "";
        img.loading = "lazy";
        box.appendChild(img);
        var link = el("a", "lp-fbt-name", item.name);
        link.href = L(item.url);
        box.appendChild(link);
        var price = el("span", "lp-fbt-price");
        price.dataset.ht = item.ht;
        price.dataset.ttc = item.ttc;
        box.appendChild(price);
        return box;
    }

    function paintPrices(root) {
        var mode = priceMode();
        root.querySelectorAll("[data-ht][data-ttc]").forEach(function (node) {
            var value = parseFloat(mode === "ht" ? node.dataset.ht : node.dataset.ttc);
            node.textContent = value > 0
                ? money(value) + (mode === "ht" ? " " + t("HTVA", "excl. btw", "excl. VAT") : "")
                : t("Sur devis", "Op offerte", "On quote");
        });
    }

    function buildTiers(data, ids) {
        var anchor = document.querySelector("#o_wsale_cta_wrapper");
        if (!data.tiers || !data.tiers.length || !anchor || !data.self) {
            return;
        }
        var box = guard(el("div", "lp-tiers"));
        box.appendChild(el("div", "lp-block-title",
            t("Prix dégressifs", "Staffelprijzen", "Quantity pricing")));
        var table = el("table", "lp-tiers-table");
        var head = el("tr");
        [t("Quantité", "Aantal", "Quantity"), t("Prix unitaire", "Stukprijs", "Unit price"),
            t("Remise", "Korting", "Saving")].forEach(function (label) {
            head.appendChild(el("th", null, label));
        });
        table.appendChild(head);
        [{ qty: 1, ht: data.self.ht, ttc: data.self.ttc, pct: 0 }].concat(data.tiers).forEach(
            function (tier) {
                var tr = el("tr", "lp-tiers-row");
                tr.appendChild(el("td", null, tier.qty + (tier.qty > 1 ? "+" : "")));
                var price = el("td");
                price.dataset.ht = tier.ht;
                price.dataset.ttc = tier.ttc;
                tr.appendChild(price);
                tr.appendChild(el("td", null, tier.pct ? "−" + tier.pct + " %" : "—"));
                tr.addEventListener("click", function () {
                    var input = ids.form.querySelector('input[name="add_qty"]');
                    if (input) {
                        input.value = tier.qty;
                        input.dispatchEvent(new Event("change", { bubbles: true }));
                    }
                });
                table.appendChild(tr);
            }
        );
        box.appendChild(table);
        anchor.parentNode.insertBefore(box, anchor);
        paintPrices(box);
    }

    function buildBundle(data) {
        if (!data.bundle || !data.bundle.length || !data.self || !(data.self.ttc > 0)) {
            return;
        }
        var section = guard(el("section", "lp-fbt container"));
        section.appendChild(el("h4", "lp-block-title",
            t("Fréquemment achetés ensemble", "Vaak samen gekocht", "Frequently bought together")));
        var row = el("div", "lp-fbt-row");
        var items = [data.self].concat(data.bundle);
        items.forEach(function (item, index) {
            if (index) {
                row.appendChild(el("span", "lp-fbt-plus", "+"));
            }
            row.appendChild(card(item, true, true));
        });
        var total = el("div", "lp-fbt-total");
        var label = el("div", "lp-fbt-total-label");
        var amount = el("div", "lp-fbt-total-amount");
        var add = el("button", "btn btn-primary lp-fbt-add");
        add.type = "button";
        var done = el("div", "lp-fbt-done");
        total.appendChild(label);
        total.appendChild(amount);
        total.appendChild(add);
        total.appendChild(done);
        row.appendChild(total);
        section.appendChild(row);

        function chosen() {
            return items.filter(function (item, index) {
                return row.querySelectorAll(".lp-fbt-check")[index].checked;
            });
        }
        function refresh() {
            var list = chosen();
            var mode = priceMode();
            var sum = list.reduce(function (acc, item) {
                return acc + (mode === "ht" ? item.ht : item.ttc);
            }, 0);
            label.textContent = t("Prix total", "Totaalprijs", "Total price")
                + (mode === "ht" ? " " + t("HTVA", "excl. btw", "excl. VAT") : "");
            amount.textContent = money(sum);
            add.disabled = !list.length;
            add.textContent = list.length > 1
                ? t("Ajouter les " + list.length + " au panier",
                    "Alle " + list.length + " toevoegen", "Add all " + list.length + " to cart")
                : t("Ajouter au panier", "In winkelwagen", "Add to cart");
            paintPrices(section);
        }
        row.addEventListener("change", refresh);
        document.addEventListener("lp-price-mode", refresh);
        add.addEventListener("click", function () {
            var list = chosen();
            if (!list.length || add.disabled) {
                return;
            }
            add.disabled = true;
            done.textContent = "";
            var last = null;
            list.reduce(function (chain, item) {
                return chain.then(function () {
                    return rpc("/lolirine_motion/cart/add", {
                        product_id: item.product_id, quantity: 1,
                    }).then(function (res) {
                        if (!res || res.error) {
                            throw new Error("cart");
                        }
                        last = res;
                    });
                });
            }, Promise.resolve())
                .then(function () {
                    done.textContent = t("Ajouté au panier", "Toegevoegd", "Added to cart");
                })
                .catch(function () {
                    done.textContent = t("Ajout impossible, réessayez.",
                        "Toevoegen mislukt, probeer opnieuw.", "Could not add, please retry.");
                })
                .then(function () {
                    if (last) {
                        setCartBadge(last.count);
                    }
                    add.disabled = false;
                });
        });

        var old = document.querySelector(".o_lp_accessories");
        var desc = document.querySelector("#product_full_description");
        var host = old || desc;
        if (old) {
            old.parentNode.insertBefore(section, old);
            html.classList.add("lp-has-fbt");
        } else if (host) {
            host.parentNode.insertBefore(section, host.nextSibling);
        } else {
            return;
        }
        refresh();
    }

    function buildCompare(data) {
        var cmp = data.compare;
        if (!cmp || !cmp.items || cmp.items.length < 2) {
            return;
        }
        var section = guard(el("section", "lp-compare container"));
        section.appendChild(el("h4", "lp-block-title",
            t("Comparer avec des produits similaires", "Vergelijk met vergelijkbare producten",
                "Compare with similar items")));
        var scroll = el("div", "lp-compare-scroll");
        var table = el("table", "lp-compare-table");
        var head = el("tr");
        head.appendChild(el("th"));
        cmp.items.forEach(function (item) {
            var th = el("th", item.current ? "is-current" : "");
            var a = el("a", "lp-compare-card");
            a.href = L(item.url);
            var img = el("img");
            img.src = item.image;
            img.alt = "";
            img.loading = "lazy";
            a.appendChild(img);
            a.appendChild(el("span", null, item.name));
            th.appendChild(a);
            if (item.current) {
                th.appendChild(el("em", "lp-compare-tag",
                    t("Cet article", "Dit artikel", "This item")));
            }
            head.appendChild(th);
        });
        table.appendChild(head);
        var priceRow = el("tr");
        priceRow.appendChild(el("td", "lp-compare-label", t("Prix", "Prijs", "Price")));
        cmp.items.forEach(function (item) {
            var td = el("td", "lp-compare-price" + (item.current ? " is-current" : ""));
            td.dataset.ht = item.ht;
            td.dataset.ttc = item.ttc;
            priceRow.appendChild(td);
        });
        table.appendChild(priceRow);
        (cmp.rows || []).forEach(function (row) {
            var tr = el("tr");
            tr.appendChild(el("td", "lp-compare-label", row.label));
            row.cells.forEach(function (cell, index) {
                tr.appendChild(el("td", cmp.items[index].current ? "is-current" : "", cell || "—"));
            });
            table.appendChild(tr);
        });
        scroll.appendChild(table);
        section.appendChild(scroll);

        var anchor = document.querySelector("#o_product_page_reviews")
            || document.querySelector("#oe_structure_website_sale_product_2");
        var detail = document.querySelector("#product_detail");
        if (anchor) {
            anchor.parentNode.insertBefore(section, anchor);
        } else if (detail) {
            detail.appendChild(section);
        } else {
            return;
        }
        paintPrices(section);
        document.addEventListener("lp-price-mode", function () {
            paintPrices(section);
        });
    }

    function buildProduct() {
        var ids = productIds();
        if (!ids || !document.querySelector("#product_detail")) {
            return;
        }
        getJSON(L("/lolirine_nav/product/" + ids.tmpl) + "?product_id=" + encodeURIComponent(ids.product))
            .then(function (data) {
                if (!data || data.error || inEditor()) {
                    return;
                }
                buildTiers(data, ids);
                buildBundle(data);
                buildCompare(data);
                document.addEventListener("lp-price-mode", function () {
                    var tiers = document.querySelector(".lp-tiers");
                    if (tiers) {
                        paintPrices(tiers);
                    }
                });
            })
            .catch(function () {});
    }

    /* ================================================================
     * 5. Panier : demande de devis
     * ================================================================ */
    function buildQuote() {
        if (!document.querySelector("#shop_cart")) {
            return;
        }
        var checkout = document.querySelector('a[name="website_sale_main_button"]');
        if (!checkout || document.querySelector(".lp-quote-open")) {
            return;
        }
        var open = guard(el("button", "btn btn-outline-primary w-100 mt-2 lp-quote-open"));
        open.type = "button";
        open.appendChild(el("i", "fa fa-file-text-o me-1"));
        open.appendChild(document.createTextNode(
            t("Demander un devis pour ce panier", "Offerte aanvragen voor deze winkelwagen",
                "Request a quote for this cart")));
        checkout.parentNode.insertBefore(open, checkout.nextSibling);

        var modal = el("div", "lp-quote");
        modal.setAttribute("aria-hidden", "true");
        var overlay = el("div", "lp-quote-overlay");
        var dialog = el("form", "lp-quote-dialog");
        dialog.setAttribute("role", "dialog");
        dialog.setAttribute("aria-modal", "true");
        dialog.appendChild(el("h4", null, t("Demande de devis", "Offerteaanvraag", "Quote request")));
        dialog.appendChild(el("p", "lp-quote-intro",
            t("Nous vous envoyons un devis pour le contenu de ce panier, port compris, sous un jour ouvrable.",
                "Wij sturen u binnen één werkdag een offerte voor deze winkelwagen, inclusief verzending.",
                "We send you a quote for this cart, shipping included, within one working day.")));
        var fields = {};
        [
            ["name", t("Nom et prénom", "Naam", "Full name"), "text", true],
            ["email", "E-mail", "email", true],
            ["phone", t("Téléphone", "Telefoon", "Phone"), "tel", false],
            ["company", t("Société", "Bedrijf", "Company"), "text", false],
            ["vat", t("Numéro de TVA", "Btw-nummer", "VAT number"), "text", false],
        ].forEach(function (def) {
            var wrap = el("label", "lp-quote-field");
            wrap.appendChild(el("span", null, def[1] + (def[3] ? " *" : "")));
            var input = el("input", "form-control");
            input.type = def[2];
            input.name = def[0];
            input.required = def[3];
            wrap.appendChild(input);
            dialog.appendChild(wrap);
            fields[def[0]] = input;
        });
        var noteWrap = el("label", "lp-quote-field");
        noteWrap.appendChild(el("span", null, t("Message", "Bericht", "Message")));
        var note = el("textarea", "form-control");
        note.rows = 3;
        noteWrap.appendChild(note);
        dialog.appendChild(noteWrap);
        var status = el("div", "lp-quote-status");
        dialog.appendChild(status);
        var actions = el("div", "lp-quote-actions");
        var cancel = el("button", "btn btn-light", t("Annuler", "Annuleren", "Cancel"));
        cancel.type = "button";
        var send = el("button", "btn btn-primary", t("Envoyer la demande", "Aanvraag versturen", "Send request"));
        send.type = "submit";
        actions.appendChild(cancel);
        actions.appendChild(send);
        dialog.appendChild(actions);
        modal.appendChild(overlay);
        modal.appendChild(dialog);
        document.body.appendChild(modal);

        function show(on) {
            modal.classList.toggle("is-open", on);
            modal.setAttribute("aria-hidden", on ? "false" : "true");
        }
        open.addEventListener("click", function () {
            show(true);
        });
        overlay.addEventListener("click", function () {
            show(false);
        });
        cancel.addEventListener("click", function () {
            show(false);
        });
        dialog.addEventListener("submit", function (ev) {
            ev.preventDefault();
            send.disabled = true;
            status.textContent = "";
            rpc("/lolirine_nav/quote", {
                name: fields.name.value, email: fields.email.value, phone: fields.phone.value,
                company: fields.company.value, vat: fields.vat.value, note: note.value,
            })
                .then(function (res) {
                    if (res && res.ok) {
                        status.className = "lp-quote-status is-ok";
                        status.textContent = t("Demande envoyée. Référence : ", "Aanvraag verzonden. Referentie: ",
                            "Request sent. Reference: ") + (res.ref || "");
                        send.style.display = "none";
                        cancel.textContent = t("Fermer", "Sluiten", "Close");
                        return;
                    }
                    throw new Error("quote");
                })
                .catch(function () {
                    status.className = "lp-quote-status is-error";
                    status.textContent = t("L'envoi a échoué. Vérifiez vos coordonnées ou écrivez-nous sur WhatsApp.",
                        "Verzenden mislukt. Controleer uw gegevens of schrijf ons via WhatsApp.",
                        "Sending failed. Check your details or message us on WhatsApp.");
                    send.disabled = false;
                });
        });
    }

    /* ================================================================
     * 6. Tunnel de commande : date de livraison, garanties, pays
     * ================================================================ */
    function isCheckoutStep() {
        return /\/shop\/(address|checkout|payment|extra_info)(\/|$)/.test(window.location.pathname);
    }

    function reassurance() {
        var list = el("ul", "lp-checkout-trust");
        [
            ["fa-lock", t("Paiement sécurisé (Bancontact, carte)", "Veilig betalen (Bancontact, kaart)",
                "Secure payment (Bancontact, card)")],
            ["fa-undo", t("Retour possible sous 14 jours", "Retourneren binnen 14 dagen",
                "Returns within 14 days")],
            ["fa-life-ring", t("SAV en Belgique", "Dienst na verkoop in België",
                "After-sales service in Belgium")],
        ].forEach(function (item) {
            var li = el("li");
            li.appendChild(el("i", "fa " + item[0]));
            li.appendChild(el("span", null, item[1]));
            list.appendChild(li);
        });
        var help = el("li");
        help.appendChild(el("i", "fa fa-whatsapp"));
        var a = el("a", null, t("Une question ? Écrivez-nous sur WhatsApp",
            "Een vraag? Schrijf ons via WhatsApp", "A question? Message us on WhatsApp"));
        a.href = "https://wa.me/32497444146";
        a.target = "_blank";
        a.rel = "noopener";
        help.appendChild(a);
        list.appendChild(help);
        return list;
    }

    function promiseLine(delivery) {
        var line = el("div", "lp-checkout-promise");
        line.appendChild(el("i", "fa fa-truck"));
        var text = el("span");
        text.appendChild(document.createTextNode(
            t("Livraison estimée ", "Geschatte levering ", "Estimated delivery ")));
        text.appendChild(el("strong", null, delivery.text));
        line.appendChild(text);
        return line;
    }

    function buildCheckout() {
        if (!isCheckoutStep()) {
            return;
        }
        html.classList.add("lp-checkout-step");

        // Pays : Belgique proposee d'office si rien n'est encore choisi.
        var country = document.querySelector('select[name="country_id"]');
        if (country && !country.value) {
            var be = Array.prototype.filter.call(country.options, function (opt) {
                return /^Belgi/i.test(opt.textContent.trim());
            })[0];
            if (be) {
                country.value = be.value;
                country.dispatchEvent(new Event("change", { bubbles: true }));
            }
        }

        var card = document.querySelector(".o_total_card .card-body");
        var cta = card && card.querySelector(".o_cta_navigation_container");
        var column = document.querySelector(".o_website_sale_checkout_container .oe_cart");
        var box = null;
        if (card && !card.querySelector(".lp-checkout-box")) {
            box = guard(el("div", "lp-checkout-box"));
            box.appendChild(reassurance());
            if (cta) {
                card.insertBefore(box, cta);
            } else {
                card.appendChild(box);
            }
        }
        getJSON(L("/lolirine_nav/checkout"))
            .then(function (data) {
                var delivery = data && data.delivery;
                if (!delivery || !delivery.text || inEditor()) {
                    return;
                }
                if (box) {
                    box.insertBefore(promiseLine(delivery), box.firstChild);
                }
                // Sur mobile le recapitulatif est replie : la date est rappelee en tete d'etape.
                if (column && !column.querySelector(".lp-checkout-promise")) {
                    var mobile = guard(promiseLine(delivery));
                    mobile.classList.add("lp-checkout-promise-mobile");
                    column.insertBefore(mobile, column.firstChild);
                }
            })
            .catch(function () {});
    }

    /* ================================================================
     * 7. Confirmation de commande : la suite, le suivi, les complements
     * ================================================================ */
    function buildConfirmation() {
        var anchor = document.querySelector("#order_name");
        if (!/\/shop\/confirmation(\/|$)/.test(window.location.pathname) || !anchor
                || document.querySelector(".lp-confirm")) {
            return;
        }
        getJSON(L("/lolirine_nav/confirmation"))
            .then(function (data) {
                if (!data || !data.order || inEditor()) {
                    return;
                }
                var section = guard(el("section", "lp-confirm"));
                section.appendChild(el("h4", "lp-block-title",
                    t("Et maintenant ?", "En nu?", "What happens next?")));
                var steps = el("ol", "lp-confirm-steps");
                var delivery = data.delivery && data.delivery.text;
                [
                    [t("Confirmation par e-mail", "Bevestiging per e-mail", "Confirmation by e-mail"),
                        data.order.email
                            ? t("Envoyée à ", "Verzonden naar ", "Sent to ") + data.order.email
                            : t("Vous la recevez dans quelques minutes.", "U ontvangt ze binnen enkele minuten.",
                                "You will receive it within minutes.")],
                    [t("Préparation de la commande", "Voorbereiding van de bestelling", "Order preparation"),
                        t("Nous la transmettons à notre entrepôt partenaire.",
                            "Wij geven ze door aan ons partnermagazijn.",
                            "We pass it on to our partner warehouse.")],
                    [t("Expédition", "Verzending", "Shipping"),
                        t("Vous recevez un e-mail avec le suivi du colis.",
                            "U ontvangt een e-mail met de track-and-trace.",
                            "You receive an e-mail with the parcel tracking.")],
                    [t("Livraison", "Levering", "Delivery"),
                        delivery
                            ? t("Estimée ", "Geschat ", "Estimated ") + delivery
                            : t("À l'adresse indiquée.", "Op het opgegeven adres.", "To the address given.")],
                ].forEach(function (step, index) {
                    var li = el("li", "lp-confirm-step" + (index === 0 ? " is-done" : ""));
                    li.appendChild(el("span", "lp-confirm-dot", index === 0 ? "✓" : String(index + 1)));
                    var body = el("div");
                    body.appendChild(el("strong", null, step[0]));
                    body.appendChild(el("span", null, step[1]));
                    li.appendChild(body);
                    steps.appendChild(li);
                });
                section.appendChild(steps);

                var actions = el("div", "lp-confirm-actions");
                if (data.order.portal_url) {
                    var follow = el("a", "btn btn-primary",
                        t("Suivre ma commande", "Mijn bestelling volgen", "Track my order"));
                    follow.href = data.order.portal_url;
                    actions.appendChild(follow);
                }
                var shop = el("a", "btn btn-outline-primary",
                    t("Continuer mes achats", "Verder winkelen", "Continue shopping"));
                shop.href = L("/shop");
                actions.appendChild(shop);
                section.appendChild(actions);

                if (data.complements && data.complements.length) {
                    section.appendChild(el("h5", "lp-block-title lp-confirm-more",
                        t("Pour compléter votre commande", "Om uw bestelling aan te vullen",
                            "To complete your order")));
                    var row = el("div", "lp-fbt-row");
                    data.complements.forEach(function (item) {
                        row.appendChild(card(item, false, false));
                    });
                    section.appendChild(row);
                }
                anchor.parentNode.insertBefore(section, anchor.nextSibling);
                paintPrices(section);
                document.addEventListener("lp-price-mode", function () {
                    paintPrices(section);
                });
            })
            .catch(function () {});
    }

    /* ================================================================
     * Demarrage
     * ================================================================ */
    function removeInjected() {
        document.querySelectorAll(".lp-nav-injected").forEach(function (node) {
            node.remove();
        });
        html.classList.remove("lp-has-fbt", "lp-checkout-step");
    }

    // Chaque bloc est isole : une erreur dans l'un n'arrete ni les autres ni le site.
    function safe(fn) {
        return function () {
            try {
                return fn.apply(null, arguments);
            } catch (e) {
                if (window.console) {
                    window.console.warn("[lolirine_nav]", e);
                }
                return undefined;
            }
        };
    }

    function start() {
        if (html.getAttribute("data-website-id") !== "6" || inEditor()) {
            return;
        }
        html.setAttribute("data-lp-price", priceMode());
        safe(buildStrip)();
        safe(buildResultCount)();
        safe(buildProduct)();
        safe(buildQuote)();
        safe(buildCheckout)();
        safe(buildConfirmation)();
        loadTilePrices()
            .then(function () {
                if (inEditor()) {
                    return;
                }
                safe(buildTileSteppers)();
                safe(applyTilePriceMode)();
            })
            .catch(function () {});
        document.addEventListener("lp-price-mode", safe(applyTilePriceMode));
        getJSON(L("/lolirine_nav/context"))
            .then(function (data) {
                context = data || {};
                if (inEditor()) {
                    return;
                }
                safe(refreshHello)();
                safe(buildSearchScope)();
                safe(fillDrawer)();
            })
            .catch(function () {});

        // L'editeur du site s'ouvre : on retire tout ce qui a ete place dans la page.
        new MutationObserver(function () {
            if (inEditor()) {
                removeInjected();
            }
        }).observe(document.body, { attributes: true, attributeFilter: ["class"] });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", safe(start));
    } else {
        safe(start)();
    }
})();
