// Outreach System JavaScript
class OutreachManager {
    constructor() {
        this.currentAthleteId = null;
        this.currentOutreach = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupModal();
    }

    setupEventListeners() {
        // Listen for outreach generation buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.generate-outreach-btn')) {
                const athleteId = e.target.dataset.athleteId;
                this.generateOutreach(athleteId);
            }
            
            if (e.target.matches('.copy-outreach-btn')) {
                const text = e.target.dataset.text;
                this.copyToClipboard(text);
            }
            
            if (e.target.matches('.send-email-btn')) {
                this.sendEmail();
            }
        });
    }

    setupModal() {
        // Create outreach modal if it doesn't exist
        if (!document.getElementById('outreach-modal')) {
            const modal = document.createElement('div');
            modal.id = 'outreach-modal';
            modal.className = 'outreach-modal';
            modal.innerHTML = `
                <div class="outreach-modal-content">
                    <div class="outreach-modal-header">
                        <h3>Mensaje de Outreach Generado</h3>
                        <button class="outreach-modal-close">&times;</button>
                    </div>
                    <div class="outreach-modal-body">
                        <div class="outreach-tabs">
                            <button class="outreach-tab active" data-tab="email">Email</button>
                            <button class="outreach-tab" data-tab="whatsapp">WhatsApp</button>
                            <button class="outreach-tab" data-tab="telegram">Telegram</button>
                        </div>
                        
                        <div class="outreach-content">
                            <div class="outreach-panel active" data-panel="email">
                                <div class="email-section">
                                    <h4>Asunto</h4>
                                    <div class="email-subject"></div>
                                    <button class="copy-outreach-btn" data-type="email-subject">Copiar Asunto</button>
                                </div>
                                <div class="email-section">
                                    <h4>Mensaje</h4>
                                    <div class="email-body"></div>
                                    <button class="copy-outreach-btn" data-type="email-body">Copiar Mensaje</button>
                                </div>
                                <div class="email-actions">
                                    <button class="send-email-btn">Enviar Email</button>
                                </div>
                            </div>
                            
                            <div class="outreach-panel" data-panel="whatsapp">
                                <div class="messaging-section">
                                    <h4>Mensaje Corto</h4>
                                    <div class="whatsapp-short"></div>
                                    <button class="copy-outreach-btn" data-type="whatsapp-short">Copiar</button>
                                </div>
                                <div class="messaging-section">
                                    <h4>Mensaje Extendido</h4>
                                    <div class="whatsapp-long"></div>
                                    <button class="copy-outreach-btn" data-type="whatsapp-long">Copiar</button>
                                </div>
                            </div>
                            
                            <div class="outreach-panel" data-panel="telegram">
                                <div class="messaging-section">
                                    <h4>Mensaje</h4>
                                    <div class="telegram-short"></div>
                                    <button class="copy-outreach-btn" data-type="telegram-short">Copiar</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="outreach-notes">
                            <h4>Notas</h4>
                            <div class="notes-content"></div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            // Setup modal event listeners
            this.setupModalEvents();
        }
    }

    setupModalEvents() {
        const modal = document.getElementById('outreach-modal');
        if (!modal) return;

        // Close button
        const closeBtn = modal.querySelector('.outreach-modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hideModal());
        }

        // Tab switching
        const tabs = modal.querySelectorAll('.outreach-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Click outside to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hideModal();
            }
        });
    }

    async generateOutreach(athleteId) {
        try {
            this.showLoading();
            this.currentAthleteId = athleteId;

            const response = await fetch(`/api/outreach/generate/${athleteId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${await response.text()}`);
            }

            const outreach = await response.json();
            this.currentOutreach = outreach;
            this.displayOutreach(outreach);
            this.showModal();

        } catch (error) {
            console.error('Error generating outreach:', error);
            this.showError('Error al generar el mensaje: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    displayOutreach(outreach) {
        const modal = document.getElementById('outreach-modal');
        if (!modal) return;

        // Display email content
        const emailSubject = modal.querySelector('.email-subject');
        const emailBody = modal.querySelector('.email-body');
        if (emailSubject && emailBody && outreach.email) {
            emailSubject.textContent = outreach.email.subject;
            emailBody.innerHTML = outreach.email.html;
        }

        // Display WhatsApp content
        const whatsappShort = modal.querySelector('.whatsapp-short');
        const whatsappLong = modal.querySelector('.whatsapp-long');
        if (whatsappShort && whatsappLong && outreach.messaging) {
            whatsappShort.textContent = outreach.messaging.whatsapp_short;
            whatsappLong.textContent = outreach.messaging.whatsapp_long;
        }

        // Display Telegram content
        const telegramShort = modal.querySelector('.telegram-short');
        if (telegramShort && outreach.messaging) {
            telegramShort.textContent = outreach.messaging.telegram_short;
        }

        // Display notes
        const notesContent = modal.querySelector('.notes-content');
        if (notesContent && outreach.notes) {
            notesContent.innerHTML = `
                <p><strong>Tono:</strong> ${outreach.notes.tone}</p>
                <p><strong>CTA:</strong> ${outreach.notes.cta}</p>
                <p><strong>Razonamiento:</strong></p>
                <ul>
                    ${outreach.notes.reasoning.map(reason => `<li>${reason}</li>`).join('')}
                </ul>
            `;
        }

        this.updateCopyButtons(outreach);
    }

    updateCopyButtons(outreach) {
        const modal = document.getElementById('outreach-modal');
        if (!modal) return;

        // Update copy buttons with actual text
        const copyButtons = modal.querySelectorAll('.copy-outreach-btn');
        copyButtons.forEach(btn => {
            const type = btn.dataset.type;
            let text = '';
            
            switch (type) {
                case 'email-subject':
                    text = outreach.email?.subject || '';
                    break;
                case 'email-body':
                    text = outreach.email?.text || '';
                    break;
                case 'whatsapp-short':
                    text = outreach.messaging?.whatsapp_short || '';
                    break;
                case 'whatsapp-long':
                    text = outreach.messaging?.whatsapp_long || '';
                    break;
                case 'telegram-short':
                    text = outreach.messaging?.telegram_short || '';
                    break;
            }
            
            btn.dataset.text = text;
        });
    }

    switchTab(tabName) {
        const modal = document.getElementById('outreach-modal');
        if (!modal) return;

        // Update tab buttons
        const tabs = modal.querySelectorAll('.outreach-tab');
        tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Update panels
        const panels = modal.querySelectorAll('.outreach-panel');
        panels.forEach(panel => {
            panel.classList.toggle('active', panel.dataset.panel === tabName);
        });
    }

    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showSuccess('Copiado al portapapeles');
        } catch (error) {
            console.error('Failed to copy:', error);
            this.showError('Error al copiar');
        }
    }

    async sendEmail() {
        if (!this.currentOutreach || !this.currentAthleteId) {
            this.showError('No hay mensaje para enviar');
            return;
        }

        try {
            // This is a placeholder - in a real implementation, you'd integrate with an email service
            this.showSuccess('Email enviado (simulado)');
            this.hideModal();
        } catch (error) {
            console.error('Error sending email:', error);
            this.showError('Error al enviar email');
        }
    }

    showModal() {
        const modal = document.getElementById('outreach-modal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    hideModal() {
        const modal = document.getElementById('outreach-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    showLoading() {
        // Show loading indicator
        const loading = document.createElement('div');
        loading.id = 'outreach-loading';
        loading.className = 'outreach-loading';
        loading.innerHTML = `
            <div class="loading-spinner"></div>
            <p>Generando mensaje...</p>
        `;
        document.body.appendChild(loading);
    }

    hideLoading() {
        const loading = document.getElementById('outreach-loading');
        if (loading) {
            loading.remove();
        }
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `outreach-notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Initialize outreach manager only on relevant pages
function shouldInitializeOutreach() {
    const currentPath = window.location.pathname;
    // Only initialize on coach todos page or athlete workspace pages
    return currentPath.includes('/coach/todos') || 
           currentPath.includes('/athletes/') && currentPath.includes('/workspace');
}

// Initialize outreach manager when DOM is loaded (only on relevant pages)
if (shouldInitializeOutreach()) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.outreachManager = new OutreachManager();
        });
    } else {
        window.outreachManager = new OutreachManager();
    }
}

// Add outreach button to coach todos (only on coach todos page)
function addOutreachButtonToTodos() {
    if (!window.location.pathname.includes('/coach/todos')) return;
    
    const todoCards = document.querySelectorAll('.card');
    todoCards.forEach(card => {
        const athleteId = card.dataset.athleteId;
        if (athleteId && !card.querySelector('.generate-outreach-btn')) {
            const actions = card.querySelector('.actions');
            if (actions) {
                const outreachBtn = document.createElement('button');
                outreachBtn.className = 'generate-outreach-btn';
                outreachBtn.dataset.athleteId = athleteId;
                outreachBtn.innerHTML = '📧 Outreach';
                outreachBtn.title = 'Generar mensaje de outreach';
                actions.appendChild(outreachBtn);
            }
        }
    });
}

// Add outreach button to athlete workspace (only on workspace pages)
function addOutreachButtonToWorkspace() {
    if (!window.location.pathname.includes('/athletes/') || !window.location.pathname.includes('/workspace')) return;
    
    const riskCard = document.querySelector('.risk-card');
    if (riskCard && !riskCard.querySelector('.generate-outreach-btn')) {
        const athleteId = window.location.pathname.split('/').pop();
        const outreachBtn = document.createElement('button');
        outreachBtn.className = 'generate-outreach-btn';
        outreachBtn.dataset.athleteId = athleteId;
        outreachBtn.innerHTML = '📧 Generar Outreach';
        outreachBtn.title = 'Generar mensaje recomendado';
        riskCard.appendChild(outreachBtn);
    }
}

// Auto-initialize buttons when content loads (only on relevant pages)
if (shouldInitializeOutreach()) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(addOutreachButtonToTodos, 1000);
            setTimeout(addOutreachButtonToWorkspace, 1000);
        });
    } else {
        setTimeout(addOutreachButtonToTodos, 1000);
        setTimeout(addOutreachButtonToWorkspace, 1000);
    }
}