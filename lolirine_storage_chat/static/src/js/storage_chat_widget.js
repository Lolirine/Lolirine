/**
 * Lolirine AI Chat Widget - Vanilla JS
 */
(function() {
    "use strict";

    var QUICK_ACTIONS = [
        { label: "\ud83d\udce6 Tailles de box", prompt: "Quelles tailles de box de stockage proposez-vous?" },
        { label: "\ud83d\udcb0 Tarifs", prompt: "Quels sont vos tarifs pour le garde-meuble?" },
        { label: "\ud83d\udd10 Securite", prompt: "Comment est assuree la securite du garde-meuble?" },
        { label: "\ud83d\udcc5 Conditions", prompt: "Quelles sont les conditions de location?" },
        { label: "\ud83d\ude9a Demenagement", prompt: "Proposez-vous un service de demenagement?" },
        { label: "\u2753 Conseils stockage", prompt: "Quels conseils pour bien stocker mes affaires?" },
    ];

    function jsonRpc(url, params) {
        return fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0", method: "call",
                id: Date.now(), params: params || {}
            }),
        })
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.error) throw new Error(d.error.data ? d.error.data.message : "RPC Error");
            return d.result;
        });
    }

    function Chat() {
        this.cfg = {};
        this.isOpen = false;
        this.msgs = [];
        this.hist = [];
        this.sid = this._getSid();
        this.loading = false;
        this.count = 0;
        this.rated = false;
        this.el = null;
    }

    Chat.prototype._getSid = function() {
        var s = sessionStorage.getItem("lsc_sid");
        if (!s) { s = "lsc_" + Date.now() + "_" + Math.random().toString(36).substr(2,9); sessionStorage.setItem("lsc_sid", s); }
        return s;
    };

    Chat.prototype._esc = function(t) { var d = document.createElement("div"); d.textContent = t; return d.innerHTML; };

    Chat.prototype._md = function(t) {
        if (!t) return "";
        return t
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/`([^`]+)`/g, "<code>$1</code>")
            .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
                '<a href="$2" target="_blank" rel="noopener" style="color:var(--lai-primary);text-decoration:underline">$1</a>')
            .replace(/\n/g, "<br/>");
    };

    Chat.prototype._time = function() {
        var n = new Date();
        return ("0"+n.getHours()).slice(-2) + ":" + ("0"+n.getMinutes()).slice(-2);
    };

    Chat.prototype.init = function() {
        var self = this;
        jsonRpc("/storage_chat/config")
        .then(function(c) {
            self.cfg = c;
            if (!c.enabled) return;
            self._build();
            self._bind();
            if (c.primary_color) self.el.style.setProperty("--lai-primary", c.primary_color);
            if (c.secondary_color) self.el.style.setProperty("--lai-secondary", c.secondary_color);
            if (c.position === "left") self.el.classList.add("position-left");
            self.tog.classList.add("bounce");
            setTimeout(function() { self.tog.classList.remove("bounce"); }, 800);
            self._scheduleTeaser();
        })
        .catch(function(e) { console.warn("[Storage Chat] Init skipped:", e.message); });
    };

    Chat.prototype._build = function() {
        this.el = document.createElement("div");
        this.el.id = "lolirine-storage-chat-container";
        this.el.innerHTML =
            '<div class="lai-chat-window" style="display:none">' +
            '<div class="lai-header">' +
            '<div class="lai-header-info">' +
            '<div class="lai-header-avatar">\ud83c\udfe0</div>' +
            '<div><div class="lai-header-title">Lolirine Garde-Meuble</div>' +
            '<div class="lai-header-status"><span class="lai-status-dot"></span>Assistant Stockage</div>' +
            '</div></div>' +
            '<div class="lai-header-actions">' +
            '<button class="lai-header-btn lai-btn-clear" title="Nouveau">\u21bb</button>' +
            '<button class="lai-header-btn lai-btn-close">\u2715</button>' +
            '</div></div>' +
            '<div class="lai-messages"></div>' +
            '<div class="lai-input-area">' +
            '<div class="lai-input-wrapper">' +
            '<textarea class="lai-input" rows="1" placeholder="Posez votre question..."></textarea>' +
            '<button class="lai-send-btn" disabled>\u27a4</button>' +
            '</div>' +
            '<div class="lai-msg-count"></div>' +
            '<div class="lai-footer">Lolirine Garde-Meuble \u00a9 2026</div>' +
            '</div></div>' +
            '<button class="lai-toggle-btn">' +
            '<span class="lai-toggle-icon">\ud83d\udcac</span>' +
            '<span class="lai-badge">1</span></button>';

        var root = document.getElementById("lolirine-storage-chat-root");
        if (root) root.appendChild(this.el);
        else document.body.appendChild(this.el);

        this.win = this.el.querySelector(".lai-chat-window");
        this.area = this.el.querySelector(".lai-messages");
        this.inp = this.el.querySelector(".lai-input");
        this.btn = this.el.querySelector(".lai-send-btn");
        this.tog = this.el.querySelector(".lai-toggle-btn");
        this.bdg = this.el.querySelector(".lai-badge");
        this.cntEl = this.el.querySelector(".lai-msg-count");
        this._welcome();
    };

    Chat.prototype._bind = function() {
        var self = this;
        this.tog.addEventListener("click", function() { self._toggle(); });
        this.el.querySelector(".lai-btn-close").addEventListener("click", function() { self._toggle(); });
        this.el.querySelector(".lai-btn-clear").addEventListener("click", function() { self._clear(); });
        this.inp.addEventListener("input", function() {
            self.btn.disabled = !self.inp.value.trim() || self.loading;
            self.inp.style.height = "auto";
            self.inp.style.height = Math.min(self.inp.scrollHeight, 100) + "px";
        });
        this.inp.addEventListener("keydown", function(e) {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); self._send(); }
        });
        this.btn.addEventListener("click", function() { self._send(); });
    };

    Chat.prototype._toggle = function() {
        this._hideTeaser();
        this.isOpen = !this.isOpen;
        this.win.style.display = this.isOpen ? "flex" : "none";
        this.tog.classList.toggle("is-open", this.isOpen);
        this.tog.querySelector(".lai-toggle-icon").textContent = this.isOpen ? "\u2715" : "\ud83d\udcac";
        if (this.isOpen) { this.bdg.style.display = "none"; var i = this.inp; setTimeout(function(){i.focus();},100); this._scroll(); }
    };

    Chat.prototype._clear = function() {
        this.msgs = []; this.hist = []; this.count = 0; this.rated = false;
        jsonRpc("/storage_chat/close", {session_id: this.sid}).catch(function(){});
        this.sid = "lsc_" + Date.now() + "_" + Math.random().toString(36).substr(2,9);
        sessionStorage.setItem("lsc_sid", this.sid);
        this.area.innerHTML = "";
        this.cntEl.textContent = "";
        this._welcome();
    };

    Chat.prototype._scroll = function() {
        var a = this.area; requestAnimationFrame(function() { a.scrollTop = a.scrollHeight; });
    };

    Chat.prototype._welcome = function() {
        var wm = this.cfg.welcome_message || "Bonjour! Comment puis-je vous aider?";
        var h = '<div class="lai-welcome-msg">' + this._md(wm) + "</div>";
        h += '<div class="lai-quick-actions">';
        for (var i = 0; i < QUICK_ACTIONS.length; i++) {
            h += '<button class="lai-quick-btn" data-p="' + this._esc(QUICK_ACTIONS[i].prompt) + '">' + QUICK_ACTIONS[i].label + "</button>";
        }
        h += "</div>";
        this.area.innerHTML = h;
        var self = this;
        this.area.querySelectorAll(".lai-quick-btn").forEach(function(b) {
            b.addEventListener("click", function() { self.inp.value = b.dataset.p; self._send(); });
        });
    };

    Chat.prototype._bubble = function(role, text, err) {
        var r = document.createElement("div"); r.className = "lai-msg-row " + role;
        var b = document.createElement("div"); b.className = "lai-msg-bubble " + role + (err ? " error" : "");
        b.innerHTML = this._md(text); r.appendChild(b);
        var t = document.createElement("div"); t.className = "lai-msg-time"; t.textContent = this._time(); r.appendChild(t);
        this.area.appendChild(r); this._scroll();
    };

    Chat.prototype._sources = function(src) {
        if (!src || !src.length) return;
        var c = document.createElement("div"); c.className = "lai-sources";
        c.innerHTML = '<div class="lai-sources-title">\ud83d\udd0d Sources</div>';
        var seen = {};
        for (var i = 0; i < Math.min(src.length, 4); i++) {
            if (seen[src[i].url]) continue; seen[src[i].url] = true;
            var a = document.createElement("a"); a.className = "lai-source-link";
            a.href = src[i].url; a.target = "_blank"; a.rel = "noopener";
            a.innerHTML = '<div class="lai-source-title">' + this._esc(src[i].title || src[i].url) + '</div>' +
                '<div class="lai-source-url">' + this._esc(src[i].url) + "</div>";
            c.appendChild(a);
        }
        this.area.appendChild(c); this._scroll();
    };

    Chat.prototype._rating = function() {
        if (this.rated) return;
        var self = this;
        var r = document.createElement("div"); r.className = "lai-rating";
        r.innerHTML = '<span class="lai-rating-label">Votre avis?</span><div class="lai-rating-stars"></div>';
        var stars = r.querySelector(".lai-rating-stars");
        for (var i = 1; i <= 5; i++) {
            (function(v) {
                var s = document.createElement("span"); s.className = "lai-rating-star";
                s.textContent = "\u2b50"; s.dataset.val = v;
                s.addEventListener("click", function() {
                    self.rated = true;
                    jsonRpc("/storage_chat/rate", {session_id: self.sid, rating: v}).catch(function(){});
                    r.innerHTML = '<span class="lai-rating-thanks">\u2705 Merci!</span>';
                });
                s.addEventListener("mouseenter", function() {
                    stars.querySelectorAll(".lai-rating-star").forEach(function(x) {
                        x.classList.toggle("active", parseInt(x.dataset.val) <= v);
                    });
                });
                stars.appendChild(s);
            })(i);
        }
        stars.addEventListener("mouseleave", function() {
            stars.querySelectorAll(".lai-rating-star").forEach(function(x) { x.classList.remove("active"); });
        });
        this.area.appendChild(r); this._scroll();
    };

    Chat.prototype._loader = function(show) {
        if (show) {
            var d = document.createElement("div"); d.className = "lai-loading"; d.id = "lai-loader";
            d.innerHTML = '<div class="lai-loading-bubble"><div class="lai-loading-dots">' +
                '<div class="lai-loading-dot"></div><div class="lai-loading-dot"></div><div class="lai-loading-dot"></div>' +
                '</div><span class="lai-loading-text">Recherche...</span></div>';
            this.area.appendChild(d); this._scroll();
        } else {
            var l = document.getElementById("lai-loader"); if (l) l.remove();
        }
    };

    Chat.prototype._send = function() {
        var text = this.inp.value.trim();
        if (!text || this.loading) return;
        var max = this.cfg.max_messages || 50;
        if (this.count >= max) {
            this._bubble("assistant", "Limite atteinte. Cliquez \u21bb pour recommencer.", true);
            return;
        }
        if (this.msgs.length === 0) this.area.innerHTML = "";
        this._bubble("user", text);
        this.msgs.push({role:"user",content:text});
        this.hist.push({role:"user",content:text});
        this.count++;
        this.cntEl.textContent = this.count + "/" + max;
        this.inp.value = ""; this.inp.style.height = "auto"; this.btn.disabled = true;
        this.loading = true;
        this._loader(true);

        var self = this;
        jsonRpc("/storage_chat/send", {
            session_id: this.sid, message: text, conversation_history: this.hist
        })
        .then(function(res) {
            self._loader(false);
            if (res.error) { self._bubble("assistant", res.error, true); return; }
            if (res.session_id) { self.sid = res.session_id; sessionStorage.setItem("lsc_sid", self.sid); }
            return self._type(res.response).then(function() {
                self.msgs.push({role:"assistant",content:res.response});
                self.hist.push({role:"assistant",content:res.response});
                if (res.web_sources && res.web_sources.length) self._sources(res.web_sources);
                if (self.count > 0 && self.count % 5 === 0 && !self.rated) self._rating();
            });
        })
        .catch(function(e) {
            self._loader(false);
            self._bubble("assistant", "Erreur. Reessayez.", true);
        })
        .finally(function() { self.loading = false; self.btn.disabled = !self.inp.value.trim(); });
    };

    Chat.prototype._type = function(text) {
        var self = this;
        return new Promise(function(resolve) {
            var r = document.createElement("div"); r.className = "lai-msg-row assistant";
            var b = document.createElement("div"); b.className = "lai-msg-bubble assistant";
            r.appendChild(b);
            var t = document.createElement("div"); t.className = "lai-msg-time"; t.textContent = self._time();
            r.appendChild(t);
            self.area.appendChild(r);
            var words = text.split(" "), idx = 0, acc = "";
            function step() {
                if (idx >= words.length) { resolve(); return; }
                acc += (idx === 0 ? "" : " ") + words[idx];
                b.innerHTML = self._md(acc);
                self._scroll();
                idx++;
                setTimeout(step, idx < 30 ? 18 : (idx < 80 ? 8 : 3));
            }
            step();
        });
    };

    Chat.prototype._scheduleTeaser = function() {
        var self = this;
        if (sessionStorage.getItem("lsc_teaser_shown")) return;
        if (self.isOpen) return;
        setTimeout(function() {
            if (self.isOpen) return;
            self._showTeaser();
        }, 5000);
    };

    Chat.prototype._showTeaser = function() {
        var self = this;
        if (this.teaserEl || this.isOpen) return;
        sessionStorage.setItem("lsc_teaser_shown", "1");
        this.tog.classList.add("pulse");
        var teaser = document.createElement("div");
        teaser.className = "lai-teaser";
        teaser.innerHTML =
            '<button class="lai-teaser-close">\u2715</button>' +
            '\ud83d\udc4b Bonjour ! Besoin d\u2019un espace de stockage ? ' +
            'Je peux vous renseigner sur nos box et tarifs.';
        this.teaserEl = teaser;
        var root = this.el.parentElement || document.body;
        root.appendChild(teaser);
        requestAnimationFrame(function() {
            requestAnimationFrame(function() { teaser.classList.add("show"); });
        });
        teaser.addEventListener("click", function(e) {
            if (e.target.classList.contains("lai-teaser-close")) { self._hideTeaser(); return; }
            self._hideTeaser();
            if (!self.isOpen) self._toggle();
        });
        this.teaserTimer = setTimeout(function() { self._hideTeaser(); }, 12000);
    };

    Chat.prototype._hideTeaser = function() {
        if (this.teaserTimer) { clearTimeout(this.teaserTimer); this.teaserTimer = null; }
        this.tog.classList.remove("pulse");
        if (this.teaserEl) {
            this.teaserEl.classList.remove("show");
            var el = this.teaserEl;
            setTimeout(function() { if (el.parentElement) el.parentElement.removeChild(el); }, 400);
            this.teaserEl = null;
        }
    };

    // Init - skip backend
    function go() {
        if (document.querySelector(".o_main_navbar") && !document.querySelector("#wrapwrap")) return;
        var c = new Chat(); c.init();
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go);
    else go();
})();
