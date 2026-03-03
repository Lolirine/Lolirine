/** @odoo-module **/
import { rpc } from "@web/core/network/rpc";

const QUICK_ACTIONS = [
    { label: "\ud83e\udd16 Robots nettoyeurs", prompt: "Quels robots nettoyeurs recommandez-vous?" },
    { label: "\ud83d\udca7 Traitement eau", prompt: "Comment traiter l eau de ma piscine?" },
    { label: "\ud83d\udd25 Chauffage", prompt: "Quelle solution de chauffage piscine?" },
    { label: "\ud83d\udec1 Spas", prompt: "Quels spas proposez-vous?" },
    { label: "\u2744\ufe0f Hivernage", prompt: "Comment hiverner ma piscine?" },
    { label: "\ud83c\udfca Piscines hors-sol", prompt: "Quelles piscines hors-sol avez-vous?" },
];

class LolirinAiChat {
    constructor() {
        this.config = {};
        this.isOpen = false;
        this.messages = [];
        this.history = [];
        this.sessionId = this._getSid();
        this.isLoading = false;
        this.container = null;
        this.init();
    }

    async init() {
        try {
            this.config = await rpc('/ai_chat/config', {});
            if (!this.config.enabled) return;
            this._build();
            this._bind();
        } catch (e) {
            console.error('AI Chat init failed', e);
        }
    }

    _getSid() {
        let s = sessionStorage.getItem('lai_sid');
        if (!s) { s = 'lai_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9); sessionStorage.setItem('lai_sid', s); }
        return s;
    }

    _esc(t) { let d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

    _md(t) {
        if (!t) return '';
        return t.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>').replace(/\n/g, '<br/>');
    }

    _build() {
        this.container = document.createElement('div');
        this.container.id = 'lolirine-ai-chat-container';
        this.container.innerHTML = '<div class="lai-chat-window" style="display:none"><div class="lai-header"><div class="lai-header-info"><div class="lai-header-avatar">\ud83c\udfca</div><div><div class="lai-header-title">Lolirine Pool Store</div><div class="lai-header-status"><span class="lai-status-dot"></span>Assistant IA</div></div></div><div class="lai-header-actions"><button class="lai-header-btn lai-btn-clear" title="Nouveau">\u21bb</button><button class="lai-header-btn lai-btn-close">\u2715</button></div></div><div class="lai-messages"></div><div class="lai-input-area"><div class="lai-input-wrapper"><textarea class="lai-input" rows="1" placeholder="Posez votre question..."></textarea><button class="lai-send-btn" disabled>\u27a4</button></div><div class="lai-footer">Lolirine Pool Store \u00a9 2026</div></div></div><button class="lai-toggle-btn"><span class="lai-toggle-icon">\ud83d\udcac</span><span class="lai-badge">1</span></button>';

        let root = document.getElementById('lolirine-ai-chat-root');
        if (root) root.appendChild(this.container);
        else document.body.appendChild(this.container);

        this.chatWin = this.container.querySelector('.lai-chat-window');
        this.msgArea = this.container.querySelector('.lai-messages');
        this.inp = this.container.querySelector('.lai-input');
        this.sendBtn = this.container.querySelector('.lai-send-btn');
        this.togBtn = this.container.querySelector('.lai-toggle-btn');
        this.badge = this.container.querySelector('.lai-badge');
        this._showWelcome();
    }

    _bind() {
        this.togBtn.addEventListener('click', () => this._toggle());
        this.container.querySelector('.lai-btn-close').addEventListener('click', () => this._toggle());
        this.container.querySelector('.lai-btn-clear').addEventListener('click', () => this._clear());
        this.inp.addEventListener('input', () => {
            this.sendBtn.disabled = !this.inp.value.trim() || this.isLoading;
            this.inp.style.height = 'auto';
            this.inp.style.height = Math.min(this.inp.scrollHeight, 100) + 'px';
        });
        this.inp.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._send(); } });
        this.sendBtn.addEventListener('click', () => this._send());
    }

    _toggle() {
        this.isOpen = !this.isOpen;
        this.chatWin.style.display = this.isOpen ? 'flex' : 'none';
        this.togBtn.classList.toggle('is-open', this.isOpen);
        this.togBtn.querySelector('.lai-toggle-icon').textContent = this.isOpen ? '\u2715' : '\ud83d\udcac';
        if (this.isOpen) { this.badge.style.display = 'none'; this.inp.focus(); }
    }

    _clear() {
        this.messages = []; this.history = [];
        this.sessionId = 'lai_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem('lai_sid', this.sessionId);
        this.msgArea.innerHTML = '';
        this._showWelcome();
    }

    _scroll() { requestAnimationFrame(() => { this.msgArea.scrollTop = this.msgArea.scrollHeight; }); }

    _showWelcome() {
        let wm = this.config.welcome_message || 'Bonjour! Comment puis-je vous aider?';
        let h = '<div class="lai-welcome-msg">' + this._md(wm) + '</div>';
        h += '<div class="lai-quick-actions">';
        for (let a of QUICK_ACTIONS) h += '<button class="lai-quick-btn" data-p="' + this._esc(a.prompt) + '">' + a.label + '</button>';
        h += '</div>';
        this.msgArea.innerHTML = h;
        this.msgArea.querySelectorAll('.lai-quick-btn').forEach(b => {
            b.addEventListener('click', () => { this.inp.value = b.dataset.p; this._send(); });
        });
    }

    _addBubble(role, text, err) {
        let r = document.createElement('div'); r.className = 'lai-msg-row ' + role;
        let b = document.createElement('div'); b.className = 'lai-msg-bubble ' + role + (err ? ' error' : '');
        b.innerHTML = this._md(text); r.appendChild(b); this.msgArea.appendChild(r); this._scroll();
    }

    _addSources(sources) {
        if (!sources || !sources.length) return;
        let c = document.createElement('div'); c.className = 'lai-sources';
        c.innerHTML = '<div class="lai-sources-title">\ud83d\udd0d Sources web</div>';
        for (let s of sources.slice(0, 3)) {
            let a = document.createElement('a'); a.className = 'lai-source-link'; a.href = s.url; a.target = '_blank'; a.rel = 'noopener';
            a.innerHTML = '<div class="lai-source-title">' + this._esc(s.title || s.url) + '</div><div class="lai-source-url">' + this._esc(s.url) + '</div>';
            c.appendChild(a);
        }
        this.msgArea.appendChild(c); this._scroll();
    }

    _showLoad() {
        let d = document.createElement('div'); d.className = 'lai-loading'; d.id = 'lai-loader';
        d.innerHTML = '<div class="lai-loading-bubble"><div class="lai-loading-dots"><div class="lai-loading-dot"></div><div class="lai-loading-dot"></div><div class="lai-loading-dot"></div></div><span class="lai-loading-text">Recherche...</span></div>';
        this.msgArea.appendChild(d); this._scroll();
    }

    _hideLoad() { let l = document.getElementById('lai-loader'); if (l) l.remove(); }

    async _send() {
        let text = this.inp.value.trim();
        if (!text || this.isLoading) return;
        if (this.messages.length === 0) this.msgArea.innerHTML = '';
        this._addBubble('user', text);
        this.messages.push({ role: 'user', content: text });
        this.history.push({ role: 'user', content: text });
        this.inp.value = ''; this.inp.style.height = 'auto'; this.sendBtn.disabled = true;
        this.isLoading = true; this._showLoad();

        try {
            let res = await rpc('/ai_chat/send', { session_id: this.sessionId, message: text, conversation_history: this.history });
            this._hideLoad();
            if (res.error) { this._addBubble('assistant', res.error, true); }
            else {
                if (res.session_id) { this.sessionId = res.session_id; sessionStorage.setItem('lai_sid', this.sessionId); }
                await this._type(res.response);
                this.messages.push({ role: 'assistant', content: res.response });
                this.history.push({ role: 'assistant', content: res.response });
                if (res.web_sources && res.web_sources.length) this._addSources(res.web_sources);
            }
        } catch (e) {
            this._hideLoad();
            this._addBubble('assistant', 'Erreur. Reessayez ou contactez Lolirine Pool Store.', true);
        } finally { this.isLoading = false; this.sendBtn.disabled = !this.inp.value.trim(); }
    }

    async _type(text) {
        let r = document.createElement('div'); r.className = 'lai-msg-row assistant';
        let b = document.createElement('div'); b.className = 'lai-msg-bubble assistant';
        r.appendChild(b); this.msgArea.appendChild(r);
        let words = text.split(' '), acc = '';
        for (let i = 0; i < words.length; i++) {
            acc += (i === 0 ? '' : ' ') + words[i];
            b.innerHTML = this._md(acc); this._scroll();
            await new Promise(r => setTimeout(r, 12));
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.o_main_navbar') && !document.querySelector('#wrapwrap')) return;
    new LolirinAiChat();
});

let _laiInit = false;
new MutationObserver(() => {
    if (!_laiInit && document.getElementById('lolirine-ai-chat-root')) { _laiInit = true; new LolirinAiChat(); }
}).observe(document.body, { childList: true, subtree: true });
