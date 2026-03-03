/** @odoo-module **/
import { rpc } from "@web/core/network/rpc";

const QUICK_ACTIONS = [
    { label: "\ud83e\udd16 Robots nettoyeurs", prompt: "Quels robots nettoyeurs de piscine recommandez-vous?" },
    { label: "\ud83d\udca7 Traitement eau", prompt: "Comment bien traiter l'eau de ma piscine?" },
    { label: "\ud83d\udd25 Chauffage piscine", prompt: "Quelles solutions de chauffage piscine proposez-vous?" },
    { label: "\ud83d\udec1 Spas et jacuzzis", prompt: "Quels spas et jacuzzis avez-vous en catalogue?" },
    { label: "\u2744\ufe0f Hivernage", prompt: "Comment hiverner correctement ma piscine?" },
    { label: "\ud83c\udfca Piscines hors-sol", prompt: "Quelles piscines hors-sol sont disponibles?" },
];

class LolirinAiChat {
    constructor() {
        this.config = {};
        this.isOpen = false;
        this.messages = [];
        this.history = [];
        this.sessionId = this._getSid();
        this.isLoading = false;
        this.messageCount = 0;
        this.hasRated = false;
        this.container = null;
        this.init();
    }

    async init() {
        try {
            this.config = await rpc('/ai_chat/config', {});
            if (!this.config.enabled) return;
            this._build();
            this._bind();
            this._applyColors();
        } catch (e) {
            console.error('[AI Chat] Init failed:', e);
        }
    }

    _getSid() {
        let s = sessionStorage.getItem('lai_sid');
        if (!s) {
            s = 'lai_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('lai_sid', s);
        }
        return s;
    }

    _esc(t) {
        const d = document.createElement('div');
        d.textContent = t;
        return d.innerHTML;
    }

    _md(t) {
        if (!t) return '';
        return t
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" style="color:var(--lai-primary);text-decoration:underline">$1</a>')
            .replace(/\n/g, '<br/>');
    }

    _time() {
        const now = new Date();
        return now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
    }

    _applyColors() {
        const c = this.container;
        if (this.config.primary_color) c.style.setProperty('--lai-primary', this.config.primary_color);
        if (this.config.secondary_color) c.style.setProperty('--lai-secondary', this.config.secondary_color);
        if (this.config.position === 'left') c.classList.add('position-left');
    }

    _build() {
        this.container = document.createElement('div');
        this.container.id = 'lolirine-ai-chat-container';
        this.container.innerHTML = `
<div class="lai-chat-window" style="display:none">
    <div class="lai-header">
        <div class="lai-header-info">
            <div class="lai-header-avatar">\ud83c\udfca</div>
            <div>
                <div class="lai-header-title">Lolirine Pool Store</div>
                <div class="lai-header-status"><span class="lai-status-dot"></span>Assistant IA en ligne</div>
            </div>
        </div>
        <div class="lai-header-actions">
            <button class="lai-header-btn lai-btn-clear" title="Nouvelle conversation">\u21bb</button>
            <button class="lai-header-btn lai-btn-close" title="Fermer">\u2715</button>
        </div>
    </div>
    <div class="lai-messages"></div>
    <div class="lai-input-area">
        <div class="lai-input-wrapper">
            <textarea class="lai-input" rows="1" placeholder="Posez votre question sur les piscines, spas..."></textarea>
            <button class="lai-send-btn" disabled>\u27a4</button>
        </div>
        <div class="lai-msg-count"></div>
        <div class="lai-footer">Lolirine Pool Store \u00a9 2026 \u2022 Powered by AI</div>
    </div>
</div>
<button class="lai-toggle-btn">
    <span class="lai-toggle-icon">\ud83d\udcac</span>
    <span class="lai-badge">1</span>
</button>`;

        const root = document.getElementById('lolirine-ai-chat-root');
        if (root) root.appendChild(this.container);
        else document.body.appendChild(this.container);

        this.chatWin = this.container.querySelector('.lai-chat-window');
        this.msgArea = this.container.querySelector('.lai-messages');
        this.inp = this.container.querySelector('.lai-input');
        this.sendBtn = this.container.querySelector('.lai-send-btn');
        this.togBtn = this.container.querySelector('.lai-toggle-btn');
        this.badge = this.container.querySelector('.lai-badge');
        this.msgCountEl = this.container.querySelector('.lai-msg-count');
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
        this.inp.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this._send();
            }
        });
        this.sendBtn.addEventListener('click', () => this._send());
    }

    _toggle() {
        this.isOpen = !this.isOpen;
        this.chatWin.style.display = this.isOpen ? 'flex' : 'none';
        this.togBtn.classList.toggle('is-open', this.isOpen);
        this.togBtn.querySelector('.lai-toggle-icon').textContent = this.isOpen ? '\u2715' : '\ud83d\udcac';
        if (this.isOpen) {
            this.badge.style.display = 'none';
            setTimeout(() => this.inp.focus(), 100);
            this._scroll();
        }
    }

    _clear() {
        this.messages = [];
        this.history = [];
        this.messageCount = 0;
        this.hasRated = false;
        // Close old session
        rpc('/ai_chat/close', { session_id: this.sessionId }).catch(() => {});
        this.sessionId = 'lai_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem('lai_sid', this.sessionId);
        this.msgArea.innerHTML = '';
        this._updateMsgCount();
        this._showWelcome();
    }

    _scroll() {
        requestAnimationFrame(() => {
            this.msgArea.scrollTop = this.msgArea.scrollHeight;
        });
    }

    _updateMsgCount() {
        const max = this.config.max_messages || 50;
        if (this.messageCount > 0) {
            this.msgCountEl.textContent = this.messageCount + '/' + max + ' messages';
        } else {
            this.msgCountEl.textContent = '';
        }
    }

    _showWelcome() {
        const wm = this.config.welcome_message || 'Bonjour! Comment puis-je vous aider?';
        let h = '<div class="lai-welcome-msg">' + this._md(wm) + '</div>';
        h += '<div class="lai-quick-actions">';
        for (const a of QUICK_ACTIONS) {
            h += '<button class="lai-quick-btn" data-p="' + this._esc(a.prompt) + '">' + a.label + '</button>';
        }
        h += '</div>';
        this.msgArea.innerHTML = h;
        this.msgArea.querySelectorAll('.lai-quick-btn').forEach(b => {
            b.addEventListener('click', () => {
                this.inp.value = b.dataset.p;
                this._send();
            });
        });
    }

    _addBubble(role, text, err) {
        const r = document.createElement('div');
        r.className = 'lai-msg-row ' + role;
        const b = document.createElement('div');
        b.className = 'lai-msg-bubble ' + role + (err ? ' error' : '');
        b.innerHTML = this._md(text);
        r.appendChild(b);
        const t = document.createElement('div');
        t.className = 'lai-msg-time';
        t.textContent = this._time();
        r.appendChild(t);
        this.msgArea.appendChild(r);
        this._scroll();
    }

    _addSources(sources) {
        if (!sources || !sources.length) return;
        const c = document.createElement('div');
        c.className = 'lai-sources';
        c.innerHTML = '<div class="lai-sources-title">\ud83d\udd0d Sources web</div>';
        const seen = new Set();
        for (const s of sources.slice(0, 4)) {
            if (seen.has(s.url)) continue;
            seen.add(s.url);
            const a = document.createElement('a');
            a.className = 'lai-source-link';
            a.href = s.url;
            a.target = '_blank';
            a.rel = 'noopener';
            a.innerHTML = '<div class="lai-source-title">' + this._esc(s.title || s.url) + '</div><div class="lai-source-url">' + this._esc(s.url) + '</div>';
            c.appendChild(a);
        }
        this.msgArea.appendChild(c);
        this._scroll();
    }

    _showRating() {
        if (this.hasRated) return;
        const r = document.createElement('div');
        r.className = 'lai-rating';
        r.innerHTML = '<span class="lai-rating-label">Votre avis?</span><div class="lai-rating-stars"></div>';
        const stars = r.querySelector('.lai-rating-stars');
        for (let i = 1; i <= 5; i++) {
            const s = document.createElement('span');
            s.className = 'lai-rating-star';
            s.textContent = '\u2b50';
            s.dataset.val = i;
            s.addEventListener('click', async () => {
                this.hasRated = true;
                try {
                    await rpc('/ai_chat/rate', { session_id: this.sessionId, rating: i });
                } catch (e) {}
                r.innerHTML = '<span class="lai-rating-thanks">\u2705 Merci pour votre evaluation!</span>';
            });
            s.addEventListener('mouseenter', () => {
                stars.querySelectorAll('.lai-rating-star').forEach(st => {
                    st.classList.toggle('active', parseInt(st.dataset.val) <= i);
                });
            });
            stars.appendChild(s);
        }
        stars.addEventListener('mouseleave', () => {
            stars.querySelectorAll('.lai-rating-star').forEach(st => st.classList.remove('active'));
        });
        this.msgArea.appendChild(r);
        this._scroll();
    }

    _showLoad() {
        const d = document.createElement('div');
        d.className = 'lai-loading';
        d.id = 'lai-loader';
        d.innerHTML = '<div class="lai-loading-bubble"><div class="lai-loading-dots"><div class="lai-loading-dot"></div><div class="lai-loading-dot"></div><div class="lai-loading-dot"></div></div><span class="lai-loading-text">Recherche en cours...</span></div>';
        this.msgArea.appendChild(d);
        this._scroll();
    }

    _hideLoad() {
        const l = document.getElementById('lai-loader');
        if (l) l.remove();
    }

    async _send() {
        const text = this.inp.value.trim();
        if (!text || this.isLoading) return;
        const max = this.config.max_messages || 50;
        if (this.messageCount >= max) {
            this._addBubble('assistant', 'Limite de messages atteinte. Cliquez sur \u21bb pour une nouvelle conversation.', true);
            return;
        }
        if (this.messages.length === 0) this.msgArea.innerHTML = '';
        this._addBubble('user', text);
        this.messages.push({ role: 'user', content: text });
        this.history.push({ role: 'user', content: text });
        this.messageCount++;
        this._updateMsgCount();
        this.inp.value = '';
        this.inp.style.height = 'auto';
        this.sendBtn.disabled = true;
        this.isLoading = true;
        this._showLoad();

        try {
            const res = await rpc('/ai_chat/send', {
                session_id: this.sessionId,
                message: text,
                conversation_history: this.history,
            });
            this._hideLoad();
            if (res.error) {
                this._addBubble('assistant', res.error, true);
            } else {
                if (res.session_id) {
                    this.sessionId = res.session_id;
                    sessionStorage.setItem('lai_sid', this.sessionId);
                }
                await this._typeText(res.response);
                this.messages.push({ role: 'assistant', content: res.response });
                this.history.push({ role: 'assistant', content: res.response });
                if (res.web_sources && res.web_sources.length) {
                    this._addSources(res.web_sources);
                }
                // Show rating every 5 messages
                if (this.messageCount > 0 && this.messageCount % 5 === 0 && !this.hasRated) {
                    this._showRating();
                }
            }
        } catch (e) {
            this._hideLoad();
            this._addBubble('assistant', 'Erreur de communication. Verifiez votre connexion et reessayez.', true);
            console.error('[AI Chat] Send error:', e);
        } finally {
            this.isLoading = false;
            this.sendBtn.disabled = !this.inp.value.trim();
        }
    }

    async _typeText(text) {
        const r = document.createElement('div');
        r.className = 'lai-msg-row assistant';
        const b = document.createElement('div');
        b.className = 'lai-msg-bubble assistant';
        r.appendChild(b);
        const t = document.createElement('div');
        t.className = 'lai-msg-time';
        t.textContent = this._time();
        r.appendChild(t);
        this.msgArea.appendChild(r);

        const words = text.split(' ');
        let acc = '';
        for (let i = 0; i < words.length; i++) {
            acc += (i === 0 ? '' : ' ') + words[i];
            b.innerHTML = this._md(acc);
            this._scroll();
            if (i < 30) {
                await new Promise(r => setTimeout(r, 18));
            } else if (i < 80) {
                await new Promise(r => setTimeout(r, 8));
            } else {
                await new Promise(r => setTimeout(r, 3));
            }
        }
    }
}

// Initialize when DOM is ready
let _laiInitDone = false;
function tryInit() {
    if (_laiInitDone) return;
    // Skip if in backend
    if (document.querySelector('.o_main_navbar') && !document.querySelector('#wrapwrap')) return;
    _laiInitDone = true;
    new LolirinAiChat();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tryInit);
} else {
    tryInit();
}

// Also observe for SPA navigation
new MutationObserver(() => {
    if (!_laiInitDone && document.getElementById('lolirine-ai-chat-root')) {
        tryInit();
    }
}).observe(document.body, { childList: true, subtree: true });
