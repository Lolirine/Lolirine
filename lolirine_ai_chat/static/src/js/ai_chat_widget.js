/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

// ============================================================
// LOLIRINE AI CHAT WIDGET
// ============================================================

const QUICK_ACTIONS = [
    { label: "🤖 Robots nettoyeurs", prompt: "Quels robots nettoyeurs de piscine recommandez-vous ?" },
    { label: "💧 Traitement eau", prompt: "Comment bien traiter l'eau de ma piscine ?" },
    { label: "🔥 Chauffage", prompt: "Quelle solution de chauffage pour ma piscine ?" },
    { label: "🛁 Spas & Jacuzzis", prompt: "Quels spas proposez-vous ?" },
    { label: "❄️ Hivernage", prompt: "Comment hiverner ma piscine correctement ?" },
    { label: "🏊 Piscines hors-sol", prompt: "Quelles piscines hors-sol avez-vous ?" },
];

class LolirinAiChat {
    constructor() {
        this.config = {};
        this.isOpen = false;
        this.messages = [];
        this.conversationHistory = [];
        this.sessionId = this._getSessionId();
        this.isLoading = false;
        this.container = null;
        this.init();
    }

    // =========================================================================
    // INITIALIZATION
    // =========================================================================

    async init() {
        try {
            this.config = await rpc('/ai_chat/config', {});
            if (!this.config.enabled) return;

            this._applyColors();
            this._buildWidget();
            this._bindEvents();
        } catch (e) {
            console.error('Lolirine AI Chat: Init failed', e);
        }
    }

    _getSessionId() {
        let sid = sessionStorage.getItem('lai_session_id');
        if (!sid) {
            sid = 'lai_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('lai_session_id', sid);
        }
        return sid;
    }

    _applyColors() {
        const root = document.documentElement;
        if (this.config.primary_color) {
            root.style.setProperty('--lai-primary', this.config.primary_color);
        }
        if (this.config.secondary_color) {
            root.style.setProperty('--lai-secondary', this.config.secondary_color);
        }
    }

    // =========================================================================
    // BUILD DOM
    // =========================================================================

    _buildWidget() {
        const position = this.config.position || 'bottom-right';

        this.container = document.createElement('div');
        this.container.id = 'lolirine-ai-chat-container';
        this.container.className = `position-${position}`;

        this.container.innerHTML = `
            <!-- Chat Window -->
            <div class="lai-chat-window" style="display:none;">
                <!-- Header -->
                <div class="lai-header">
                    <div class="lai-header-wave"></div>
                    <div class="lai-header-content">
                        <div class="lai-header-info">
                            <div class="lai-header-avatar">🏊</div>
                            <div>
                                <div class="lai-header-title">Lolirine Pool Store</div>
                                <div class="lai-header-status">
                                    <span class="lai-status-dot"></span>
                                    Assistant IA • En ligne
                                </div>
                            </div>
                        </div>
                        <div class="lai-header-actions">
                            <button class="lai-header-btn lai-btn-clear" title="Nouvelle conversation">↻</button>
                            <button class="lai-header-btn lai-btn-close" title="Fermer">✕</button>
                        </div>
                    </div>
                </div>

                <!-- Messages -->
                <div class="lai-messages"></div>

                <!-- Input -->
                <div class="lai-input-area">
                    <div class="lai-input-wrapper">
                        <textarea class="lai-input" rows="1"
                                  placeholder="Posez votre question..."></textarea>
                        <button class="lai-send-btn" disabled>➤</button>
                    </div>
                    <div class="lai-footer">
                        Propulsé par l'IA • Lolirine Pool Store © 2026
                    </div>
                </div>
            </div>

            <!-- Toggle Button -->
            <button class="lai-toggle-btn">
                <span class="lai-toggle-icon">💬</span>
                <span class="lai-badge">1</span>
            </button>
        `;

        const root = document.getElementById('lolirine-ai-chat-root');
        if (root) {
            root.appendChild(this.container);
        } else {
            document.body.appendChild(this.container);
        }

        // Cache DOM refs
        this.chatWindow = this.container.querySelector('.lai-chat-window');
        this.messagesArea = this.container.querySelector('.lai-messages');
        this.inputEl = this.container.querySelector('.lai-input');
        this.sendBtn = this.container.querySelector('.lai-send-btn');
        this.toggleBtn = this.container.querySelector('.lai-toggle-btn');
        this.badge = this.container.querySelector('.lai-badge');

        // Show welcome
        this._renderWelcome();
    }

    // =========================================================================
    // EVENTS
    // =========================================================================

    _bindEvents() {
        // Toggle
        this.toggleBtn.addEventListener('click', () => this._toggle());

        // Close / Clear
        this.container.querySelector('.lai-btn-close').addEventListener('click', () => this._toggle());
        this.container.querySelector('.lai-btn-clear').addEventListener('click', () => this._clearChat());

        // Input
        this.inputEl.addEventListener('input', () => {
            this.sendBtn.disabled = !this.inputEl.value.trim() || this.isLoading;
            this.inputEl.style.height = 'auto';
            this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 100) + 'px';
        });
        this.inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this._sendMessage();
            }
        });

        // Send
        this.sendBtn.addEventListener('click', () => this._sendMessage());
    }

    // =========================================================================
    // UI ACTIONS
    // =========================================================================

    _toggle() {
        this.isOpen = !this.isOpen;
        this.chatWindow.style.display = this.isOpen ? 'flex' : 'none';
        this.toggleBtn.classList.toggle('is-open', this.isOpen);
        this.toggleBtn.querySelector('.lai-toggle-icon').textContent = this.isOpen ? '✕' : '💬';

        if (this.isOpen) {
            this.badge.style.display = 'none';
            this.inputEl.focus();
        }
    }

    _clearChat() {
        // Close current session
        if (this.sessionId) {
            rpc('/ai_chat/close', { session_id: this.sessionId }).catch(() => {});
        }

        this.messages = [];
        this.conversationHistory = [];
        this.sessionId = 'lai_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem('lai_session_id', this.sessionId);

        this.messagesArea.innerHTML = '';
        this._renderWelcome();
    }

    _scrollToBottom() {
        requestAnimationFrame(() => {
            this.messagesArea.scrollTop = this.messagesArea.scrollHeight;
        });
    }

    // =========================================================================
    // RENDERING
    // =========================================================================

    _parseMarkdown(text) {
        if (!text) return '';
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br/>');
    }

    _renderWelcome() {
        const welcomeMsg = this.config.welcome_message ||
            "Bonjour ! 🏊 Je suis l'assistant IA de Lolirine Pool Store. Comment puis-je vous aider ?";

        let html = `<div class="lai-welcome-group">`;
        html += `<div class="lai-welcome-msg">${this._parseMarkdown(welcomeMsg)}</div>`;
        html += `<div class="lai-welcome-msg">Que ce soit pour choisir un robot de piscine, traiter votre eau, ou trouver le spa parfait — je suis là pour vous guider !</div>`;
        html += `</div>`;

        // Quick actions
        html += `<div class="lai-quick-actions">`;
        for (const action of QUICK_ACTIONS) {
            html += `<button class="lai-quick-btn" data-prompt="${this._escapeHtml(action.prompt)}">${action.label}</button>`;
        }
        html += `</div>`;

        this.messagesArea.innerHTML = html;

        // Bind quick action clicks
        this.messagesArea.querySelectorAll('.lai-quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.inputEl.value = btn.dataset.prompt;
                this._sendMessage();
            });
        });
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _addMessageBubble(role, content, isError = false) {
        const row = document.createElement('div');
        row.className = `lai-msg-row ${role}`;

        const bubble = document.createElement('div');
        bubble.className = `lai-msg-bubble ${role}${isError ? ' error' : ''}`;
        bubble.innerHTML = this._parseMarkdown(content);

        row.appendChild(bubble);
        this.messagesArea.appendChild(row);
        this._scrollToBottom();
    }

    _addSources(sources) {
        if (!sources || sources.length === 0) return;

        const container = document.createElement('div');
        container.className = 'lai-sources';
        container.innerHTML = `<div class="lai-sources-title">🔍 Sources web</div>`;

        for (const source of sources.slice(0, 3)) {
            const link = document.createElement('a');
            link.className = 'lai-source-link';
            link.href = source.url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.innerHTML = `
                <div class="lai-source-title">${this._escapeHtml(source.title || source.url)}</div>
                <div class="lai-source-url">${this._escapeHtml(source.url)}</div>
            `;
            container.appendChild(link);
        }

        this.messagesArea.appendChild(container);
        this._scrollToBottom();
    }

    _showLoading() {
        const loader = document.createElement('div');
        loader.className = 'lai-loading';
        loader.id = 'lai-loader';
        loader.innerHTML = `
            <div class="lai-loading-bubble">
                <div class="lai-loading-dots">
                    <div class="lai-loading-dot"></div>
                    <div class="lai-loading-dot"></div>
                    <div class="lai-loading-dot"></div>
                </div>
                <span class="lai-loading-text">Recherche en cours...</span>
            </div>
        `;
        this.messagesArea.appendChild(loader);
        this._scrollToBottom();
    }

    _hideLoading() {
        const loader = document.getElementById('lai-loader');
        if (loader) loader.remove();
    }

    _showRating() {
        const ratingDiv = document.createElement('div');
        ratingDiv.className = 'lai-rating';
        ratingDiv.innerHTML = `
            <span class="lai-rating-label">Cette réponse vous a aidé ?</span>
            ${[1, 2, 3, 4, 5].map(n =>
                `<button class="lai-rating-star" data-rating="${n}">⭐</button>`
            ).join('')}
        `;

        ratingDiv.querySelectorAll('.lai-rating-star').forEach(star => {
            star.addEventListener('click', () => {
                const rating = star.dataset.rating;
                ratingDiv.querySelectorAll('.lai-rating-star').forEach((s, i) => {
                    s.classList.toggle('active', i < parseInt(rating));
                });
                rpc('/ai_chat/rate', {
                    session_id: this.sessionId,
                    rating: rating,
                }).catch(() => {});
                setTimeout(() => {
                    ratingDiv.innerHTML = '<span class="lai-rating-label">Merci pour votre retour ! 🙏</span>';
                }, 500);
            });
        });

        this.messagesArea.appendChild(ratingDiv);
        this._scrollToBottom();
    }

    // =========================================================================
    // SEND MESSAGE
    // =========================================================================

    async _sendMessage() {
        const text = this.inputEl.value.trim();
        if (!text || this.isLoading) return;

        // Clear welcome on first message
        if (this.messages.length === 0) {
            this.messagesArea.innerHTML = '';
        }

        // Add user message
        this._addMessageBubble('user', text);
        this.messages.push({ role: 'user', content: text });
        this.conversationHistory.push({ role: 'user', content: text });

        // Reset input
        this.inputEl.value = '';
        this.inputEl.style.height = 'auto';
        this.sendBtn.disabled = true;
        this.isLoading = true;
        this._showLoading();

        try {
            const result = await rpc('/ai_chat/send', {
                session_id: this.sessionId,
                message: text,
                conversation_history: this.conversationHistory,
            });

            this._hideLoading();

            if (result.error) {
                this._addMessageBubble('assistant', result.error, true);
            } else {
                // Update session ID if new
                if (result.session_id) {
                    this.sessionId = result.session_id;
                    sessionStorage.setItem('lai_session_id', this.sessionId);
                }

                // Typing animation
                await this._typeMessage(result.response);

                // Add to history
                this.messages.push({ role: 'assistant', content: result.response });
                this.conversationHistory.push({ role: 'assistant', content: result.response });

                // Show sources
                if (result.web_sources && result.web_sources.length > 0) {
                    this._addSources(result.web_sources);
                }

                // Show rating every 5 messages
                if (this.messages.filter(m => m.role === 'assistant').length % 5 === 0) {
                    this._showRating();
                }
            }
        } catch (e) {
            this._hideLoading();
            this._addMessageBubble(
                'assistant',
                "Désolé, une erreur s'est produite. Veuillez réessayer ou contacter directement Lolirine Pool Store. 🙏",
                true
            );
            console.error('Lolirine AI Chat Error:', e);
        } finally {
            this.isLoading = false;
            this.sendBtn.disabled = !this.inputEl.value.trim();
        }
    }

    async _typeMessage(text) {
        const row = document.createElement('div');
        row.className = 'lai-msg-row assistant';
        const bubble = document.createElement('div');
        bubble.className = 'lai-msg-bubble assistant';
        row.appendChild(bubble);
        this.messagesArea.appendChild(row);

        const words = text.split(' ');
        let accumulated = '';

        for (let i = 0; i < words.length; i++) {
            accumulated += (i === 0 ? '' : ' ') + words[i];
            bubble.innerHTML = this._parseMarkdown(accumulated);
            this._scrollToBottom();
            await new Promise(r => setTimeout(r, 12));
        }
    }
}

// ============================================================
// AUTO-INIT on page load
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    // Don't init in Odoo backend
    if (document.querySelector('.o_main_navbar') && !document.querySelector('#wrapwrap')) {
        return;
    }
    new LolirinAiChat();
});

// Also handle Odoo SPA navigation
if (window.addEventListener) {
    let initialized = false;
    const observer = new MutationObserver(() => {
        if (!initialized && document.getElementById('lolirine-ai-chat-root')) {
            initialized = true;
            new LolirinAiChat();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}
