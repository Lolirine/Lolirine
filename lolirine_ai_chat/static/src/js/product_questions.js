/** Questions et réponses — vote « utile » et filtre (vanilla JS) */
(function () {
    "use strict";
    function init() {
        var bloc = document.getElementById("lpq");
        if (!bloc) { return; }
        bloc.addEventListener("click", function (ev) {
            var btn = ev.target.closest(".lpq-utile");
            if (!btn || btn.classList.contains("done")) { return; }
            var cle = "lpq_vote_" + btn.dataset.id;
            try { if (localStorage.getItem(cle)) { btn.classList.add("done"); return; } } catch (e) {}
            btn.classList.add("done");
            fetch("/shop/question/utile", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: { question_id: btn.dataset.id } }),
            }).then(function (r) { return r.json(); }).then(function (r) {
                if (r.result && r.result.ok) {
                    btn.innerHTML = '<i class="fa fa-thumbs-up me-1"></i>Merci (' + r.result.votes + ")";
                    try { localStorage.setItem(cle, "1"); } catch (e) {}
                }
            }).catch(function () { btn.classList.remove("done"); });
        });
        var filtre = bloc.querySelector(".lpq-filtre");
        if (filtre) {
            var norm = function (s) { return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); };
            filtre.addEventListener("input", function () {
                var mots = norm(filtre.value).split(/\s+/).filter(Boolean);
                var visibles = 0;
                bloc.querySelectorAll(".lpq-item").forEach(function (it) {
                    var t = norm(it.textContent);
                    var ok = mots.every(function (m) { return t.indexOf(m) !== -1; });
                    it.classList.toggle("d-none", !ok);
                    if (ok) { visibles++; }
                });
                bloc.querySelector(".lpq-vide").classList.toggle("d-none", visibles > 0);
            });
        }
    }
    if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); } else { init(); }
})();
