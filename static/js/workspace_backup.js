// ===== WORKSPACE.JS MODERNIZADO - NUEVA ARQUITECTURA =====

class WorkspaceManager {
  constructor(athleteId) {
    this.athleteId = athleteId;
    this.currentConversationId = null;
    this.pendingHighlights = new Map();
  }

  // ✅ Usa workflow para transcripción
  async transcribeAudio(file) {
    try {
      showLoading('Transcribiendo audio...');
      
      // Paso 1: Transcribir usando servicio existente
      const formData = new FormData();
      formData.append('file', file);
      
      const transcriptionResponse = await fetch('/transcribe', {
        method: 'POST',
        body: formData
      });
      
      const transcriptionResult = await transcriptionResponse.json();
      
      if (!transcriptionResult.success) {
        throw new Error(transcriptionResult.error || 'Error en transcripción');
      }
      
      // Paso 2: Ingerir en workflow con todas las acciones
      const ingestData = {
        athlete_id: this.athleteId,
        transcription: transcriptionResult.transcription,
        content_audio_url: transcriptionResult.filename ? `/uploads/${transcriptionResult.filename}` : null,
        source_channel: 'manual',
        generate_highlights: true,
        suggest_reply: true,
        maybe_todo: true
      };
      
      const workflowResponse = await fetch('/ingest/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ingestData)
      });
      
      const workflowResult = await workflowResponse.json();
      
      if (workflowResult.status === 'success') {
        // Mostrar highlights sugeridos si los hay
        if (workflowResult.result.actions_performed?.highlights?.length > 0) {
          this.showHighlightsPreview(workflowResult.result.actions_performed.highlights);
        }
        
        // Actualizar interfaz
        await this.loadConversations();
        showToast('Audio procesado exitosamente', 'success');
        
        return {
          success: true,
          messageId: workflowResult.result.message_id,
          suggestedReply: workflowResult.result.actions_performed.suggested_reply,
          highlights: workflowResult.result.actions_performed.highlights,
          todo: workflowResult.result.actions_performed.todo
        };
      } else {
        throw new Error(workflowResult.message || 'Error en workflow');
      }
      
    } catch (error) {
      console.error('Error processing audio:', error);
      showToast(`Error: ${error.message}`, 'error');
      return { success: false, error: error.message };
    } finally {
      hideLoading();
    }
  }

  // ✅ Usa workflow para mensaje manual
  async addManualMessage(text) {
    try {
      const ingestData = {
        athlete_id: this.athleteId,
        content_text: text,
        source_channel: 'manual',
        generate_highlights: true,
        suggest_reply: true,
        maybe_todo: true
      };
      
      const response = await fetch('/ingest/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ingestData)
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        // Procesar resultados igual que transcripción
        if (result.result.actions_performed?.highlights?.length > 0) {
          this.showHighlightsPreview(result.result.actions_performed.highlights);
        }
        
        await this.loadConversations();
        return result.result;
      } else {
        throw new Error(result.message);
      }
      
    } catch (error) {
      console.error('Error adding manual message:', error);
      showToast(`Error: ${error.message}`, 'error');
      throw error;
    }
  }

  // ✅ Carga conversaciones usando nueva API
  async loadConversations() {
    try {
      const response = await fetch(`/communication-hub/conversations/${this.athleteId}`);
      const data = await response.json();
      
      if (data.conversations.length > 0) {
        this.currentConversationId = data.conversations[0].id;
        await this.loadMessages(this.currentConversationId);
      } else {
        this.renderEmptyState();
      }
      
    } catch (error) {
      console.error('Error loading conversations:', error);
      showToast('Error cargando conversaciones', 'error');
    }
  }

  // ✅ Carga mensajes de una conversación
  async loadMessages(conversationId) {
    try {
      const response = await fetch(`/communication-hub/conversations/${conversationId}/messages`);
      const data = await response.json();
      
      this.renderTimeline(data.messages);
      
    } catch (error) {
      console.error('Error loading messages:', error);
      showToast('Error cargando mensajes', 'error');
    }
  }

  // ✅ Genera highlights para mensaje específico
  async generateHighlightsForMessage(messageId) {
    try {
      const response = await fetch(`/messages/${messageId}/highlights/generate`, {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (result.highlights?.length > 0) {
        this.showHighlightsPreview(result.highlights, messageId);
      } else {
        showToast('No se encontraron highlights relevantes', 'info');
      }
      
    } catch (error) {
      console.error('Error generating highlights:', error);
      showToast('Error generando highlights', 'error');
    }
  }

  // ✅ Muestra preview de highlights con selección
  showHighlightsPreview(highlights, messageId = null) {
    const modal = document.getElementById('highlightsPreviewModal');
    const list = document.getElementById('highlightsPreviewList');
    
    // Limpiar lista
    list.innerHTML = '';
    
    // Renderizar highlights
    highlights.forEach((highlight, index) => {
      const item = document.createElement('div');
      item.className = 'highlight-preview-item';
      item.innerHTML = `
        <div class="highlights-preview-checkbox">
          <input type="checkbox" id="highlight_${index}" checked>
          <label for="highlight_${index}">Incluir este highlight</label>
        </div>
        <div class="highlight-preview-text">${highlight.text}</div>
        <div class="highlight-preview-tags">
          <span class="highlight-preview-tag ${highlight.category}">${highlight.category}</span>
          ${highlight.score ? `<span class="highlight-preview-tag general">Score: ${(highlight.score * 100).toFixed(0)}%</span>` : ''}
        </div>
      `;
      list.appendChild(item);
    });
    
    // Mostrar modal
    modal.classList.add('show');
    
    // Guardar datos para procesamiento
    this.pendingHighlights.set('current', { highlights, messageId });
  }

  // ✅ Procesa highlights seleccionados
  async saveSelectedHighlights() {
    try {
      const data = this.pendingHighlights.get('current');
      if (!data) return;
      
      const checkboxes = document.querySelectorAll('#highlightsPreviewList input[type="checkbox"]:checked');
      const selectedIndices = Array.from(checkboxes).map(cb => 
        parseInt(cb.id.replace('highlight_', ''))
      );
      
      // Actualizar estado de highlights
      const updates = [];
      selectedIndices.forEach(index => {
        const highlight = data.highlights[index];
        if (highlight.id) {
          updates.push({
            highlight_id: highlight.id,
            status: 'accepted',
            reviewed_by: 'user'
          });
        }
      });
      
      // Actualizar highlights en lote
      if (updates.length > 0) {
        await fetch('/highlights/bulk', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            highlight_ids: updates.map(u => u.highlight_id),
            status: 'accepted',
            reviewed_by: 'user'
          })
        });
      }
      
      // Rechazar no seleccionados
      const rejectedIds = data.highlights
        .filter((_, index) => !selectedIndices.includes(index))
        .map(h => h.id)
        .filter(id => id);
      
      if (rejectedIds.length > 0) {
        await fetch('/highlights/bulk', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            highlight_ids: rejectedIds,
            status: 'rejected',
            reviewed_by: 'user'
          })
        });
      }
      
      // Recargar highlights del atleta
      await this.loadAthleteHighlights();
      
      // Cerrar modal
      this.hideHighlightsPreview();
      
      showToast(`${selectedIndices.length} highlights guardados`, 'success');
      
    } catch (error) {
      console.error('Error saving highlights:', error);
      showToast('Error guardando highlights', 'error');
    }
  }

  // ✅ Carga highlights del atleta usando nueva API
  async loadAthleteHighlights(filters = {}) {
    try {
      const params = new URLSearchParams({
        status: filters.status || 'accepted',
        source: filters.source || 'all'
      });
      
      if (filters.category) {
        params.append('category', filters.category);
      }
      
      const response = await fetch(`/highlights/${this.athleteId}?${params}`);
      const data = await response.json();
      
      this.renderHighlights(data.highlights);
      
    } catch (error) {
      console.error('Error loading highlights:', error);
      showToast('Error cargando highlights', 'error');
    }
  }

  // ✅ Envía todo al entrenador usando workflow
  async sendTodoToCoach(todoText, priority = 'P2', dueDate = null) {
    try {
      const formData = new FormData();
      formData.append('athlete_id', this.athleteId);
      formData.append('text', todoText);
      formData.append('priority', priority);
      formData.append('status', 'backlog');
      formData.append('created_by', 'athlete');
      
      if (dueDate) {
        formData.append('due', dueDate);
      }
      
      const response = await fetch('/api/todos', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (result.success) {
        showToast('To-Do enviado al entrenador', 'success');
        
        // Limpiar formulario
        document.getElementById('todoText').value = '';
        document.getElementById('todoDue').value = '';
        
        return result.todo;
      } else {
        throw new Error(result.error);
      }
      
    } catch (error) {
      console.error('Error sending todo:', error);
      showToast(`Error: ${error.message}`, 'error');
    }
  }

  // ✅ Evalúa riesgo usando nueva API
  async assessRisk() {
    try {
      showLoading('Evaluando riesgo...');
      
      const response = await fetch(`/api/athletes/${this.athleteId}/risk`);
      const riskData = await response.json();
      
      if (riskData.athlete_id) {
        this.renderRiskAssessment(riskData);
        showToast(`Riesgo evaluado: ${riskData.level}`, 'info');
      } else {
        throw new Error(riskData.message || 'Error evaluando riesgo');
      }
      
    } catch (error) {
      console.error('Error assessing risk:', error);
      showToast(`Error: ${error.message}`, 'error');
    } finally {
      hideLoading();
    }
  }

  // Métodos de renderizado (mantener los existentes pero actualizados)
  renderTimeline(messages) {
    const timeline = document.getElementById('timeline');
    const empty = document.getElementById('emptyTimeline');
    
    if (!messages || messages.length === 0) {
      timeline.style.display = 'none';
      empty.style.display = 'block';
      return;
    }
    
    timeline.style.display = 'flex';
    empty.style.display = 'none';
    timeline.innerHTML = '';
    
    // Agrupar por días
    const grouped = this.groupMessagesByDay(messages);
    
    Object.entries(grouped).forEach(([date, dayMessages]) => {
      // Day separator
      const separator = document.createElement('div');
      separator.className = 'day-separator';
      separator.textContent = this.formatDate(date);
      timeline.appendChild(separator);
      
      // Messages
      dayMessages.forEach(message => {
        const bubble = this.createMessageBubble(message);
        timeline.appendChild(bubble);
      });
    });
  }

  createMessageBubble(message) {
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.dataset.messageId = message.id;
    
    const isIncoming = message.direction === 'in';
    const content = message.content_text || message.transcription || '';
    
    bubble.innerHTML = `
      <div class="avatar">
        <i class="fa-solid ${isIncoming ? 'fa-user' : 'fa-user-tie'}"></i>
      </div>
      <div class="content">
        ${message.content_audio_url ? `
          <div class="audio-indicator">
            <i class="fa-solid fa-volume-up"></i>
            <span class="audio-duration">Audio message</span>
          </div>
        ` : ''}
        <div class="text">${content}</div>
        <div class="meta">
          ${this.formatTime(message.created_at)} • ${message.source_channel}
        </div>
      </div>
      <div class="floating-actions">
        <button class="btn mini" onclick="workspace.generateHighlightsForMessage(${message.id})" title="Generar highlights">
          <i class="fa-solid fa-lightbulb"></i>
        </button>
        <button class="btn mini" onclick="workspace.createTodoFromMessage(${message.id})" title="Crear to-do">
          <i class="fa-solid fa-tasks"></i>
        </button>
      </div>
    `;
    
    return bubble;
  }

  renderHighlights(highlights) {
    const container = document.getElementById('highlights');
    const counter = document.getElementById('highlightsCounter');
    
    counter.textContent = highlights.length;
    container.innerHTML = '';
    
    if (highlights.length === 0) {
      container.innerHTML = '<div class="empty">No hay highlights.</div>';
      return;
    }
    
    highlights.forEach(highlight => {
      const item = document.createElement('div');
      item.className = 'highlight-item';
      if (highlight.status === 'suggested') item.classList.add('suggested');
      
      item.innerHTML = `
        <div class="highlight-content">
          <div class="highlight-title">${highlight.text}</div>
          <div class="highlight-meta">
            <span class="highlight-tag ${highlight.category}">${highlight.category}</span>
            <span>${this.formatTime(highlight.created_at)}</span>
            <span>${highlight.source === 'ai' ? 'IA' : 'Manual'}</span>
          </div>
        </div>
        <div class="highlight-actions">
          ${highlight.status === 'suggested' ? `
            <button class="btn mini success" onclick="workspace.acceptHighlight(${highlight.id})" title="Aceptar">
              <i class="fa-solid fa-check"></i>
            </button>
            <button class="btn mini danger" onclick="workspace.rejectHighlight(${highlight.id})" title="Rechazar">
              <i class="fa-solid fa-times"></i>
            </button>
          ` : `
            <button class="btn mini edit-button" onclick="workspace.editHighlight(${highlight.id})" title="Editar">
              <i class="fa-solid fa-edit"></i>
            </button>
            <button class="btn mini delete-button" onclick="workspace.deleteHighlight(${highlight.id})" title="Eliminar">
              <i class="fa-solid fa-trash"></i>
            </button>
          `}
        </div>
      `;
      
      container.appendChild(item);
    });
  }

  renderRiskAssessment(risk) {
    const container = document.getElementById('riskAssessment');
    const colorClass = risk.color;
    
    container.innerHTML = `
      <div class="risk-chip ${colorClass}">${risk.level.toUpperCase()}</div>
      <div class="risk-explanations" title="${risk.evidence?.join(', ') || ''}">
        Score: ${risk.score} • ${risk.evidence?.length || 0} factores
      </div>
    `;
  }

  // Utility methods
  groupMessagesByDay(messages) {
    const grouped = {};
    messages.forEach(message => {
      const date = message.created_at.split('T')[0];
      if (!grouped[date]) grouped[date] = [];
      grouped[date].push(message);
    });
    return grouped;
  }

  formatDate(dateStr) {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (dateStr === today.toISOString().split('T')[0]) return 'Hoy';
    if (dateStr === yesterday.toISOString().split('T')[0]) return 'Ayer';
    
    return date.toLocaleDateString('es-ES', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  }

  formatTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString('es-ES', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  hideHighlightsPreview() {
    document.getElementById('highlightsPreviewModal').classList.remove('show');
    this.pendingHighlights.delete('current');
  }

  // Métodos adicionales para highlights
  async acceptHighlight(highlightId) {
    await this.updateHighlightStatus(highlightId, 'accepted');
  }

  async rejectHighlight(highlightId) {
    await this.updateHighlightStatus(highlightId, 'rejected');
  }

  async updateHighlightStatus(highlightId, status) {
    try {
      const response = await fetch(`/highlights/${highlightId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, reviewed_by: 'user' })
      });
      
      if (response.ok) {
        await this.loadAthleteHighlights();
        showToast(`Highlight ${status === 'accepted' ? 'aceptado' : 'rechazado'}`, 'success');
      }
    } catch (error) {
      console.error('Error updating highlight:', error);
      showToast('Error actualizando highlight', 'error');
    }
  }

  renderEmptyState() {
    const timeline = document.getElementById('timeline');
    const empty = document.getElementById('emptyTimeline');
    
    timeline.style.display = 'none';
    empty.style.display = 'block';
  }
}

// ✅ Inicialización modernizada
let workspace;

document.addEventListener('DOMContentLoaded', function() {
  const athleteId = document.querySelector('.app').dataset.athleteId;
  workspace = new WorkspaceManager(parseInt(athleteId));
  
  // Event listeners
  setupEventListeners();
  
  // Carga inicial
  workspace.loadConversations();
  workspace.loadAthleteHighlights();
  workspace.assessRisk();
});

function setupEventListeners() {
  // Audio input
  const audioInput = document.getElementById('audioInput');
  const dropzone = document.getElementById('dropzone');
  
  audioInput.addEventListener('change', (e) => {
    if (e.target.files[0]) {
      workspace.transcribeAudio(e.target.files[0]);
    }
  });
  
  // Drag & drop
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag');
  });
  
  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('drag');
  });
  
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag');
    
    const files = e.dataTransfer.files;
    if (files[0] && files[0].type.startsWith('audio/')) {
      workspace.transcribeAudio(files[0]);
    }
  });
  
  // Manual message input
  const inputMensaje = document.getElementById('inputMensaje');
  const btnAgregar = document.getElementById('btnAgregar');
  
  btnAgregar.addEventListener('click', () => {
    const text = inputMensaje.value.trim();
    if (text) {
      workspace.addManualMessage(text);
      inputMensaje.value = '';
    }
  });
  
  inputMensaje.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      btnAgregar.click();
    }
  });
  
  // Todo form
  const btnSendTodo = document.getElementById('btnSendTodo');
  btnSendTodo.addEventListener('click', () => {
    const text = document.getElementById('todoText').value.trim();
    const priority = document.getElementById('todoPriority').value;
    const dueDate = document.getElementById('todoDue').value;
    
    if (text) {
      workspace.sendTodoToCoach(text, priority, dueDate || null);
    }
  });
  
  // Highlights preview modal
  document.getElementById('closeHighlightsPreview').addEventListener('click', () => {
    workspace.hideHighlightsPreview();
  });
  
  document.getElementById('cancelHighlightsPreview').addEventListener('click', () => {
    workspace.hideHighlightsPreview();
  });
  
  document.getElementById('saveHighlightsPreview').addEventListener('click', () => {
    workspace.saveSelectedHighlights();
  });
}

// Utility functions
function showToast(message, type = 'info') {
  // Implementar toast notifications
  console.log(`${type.toUpperCase()}: ${message}`);
}

function showLoading(message) {
  // Implementar loading indicator
  console.log(`Loading: ${message}`);
}

function hideLoading() {
  // Ocultar loading indicator
  console.log('Loading hidden');
}