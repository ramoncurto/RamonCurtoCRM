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

  // ✅ Sugiere respuesta para mensaje
  async suggestReplyForMessage(messageId) {
    try {
      const response = await fetch(`/messages/${messageId}/reply/suggest`, {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (result.suggested_reply) {
        // Mostrar la respuesta sugerida en un modal o área específica
        this.showSuggestedReply(result.suggested_reply, messageId);
      } else {
        showToast('No se pudo generar una respuesta sugerida', 'info');
      }
      
    } catch (error) {
      console.error('Error suggesting reply:', error);
      showToast('Error generando respuesta sugerida', 'error');
    }
  }

  // ✅ Copia texto del mensaje al portapapeles
  async copyMessageText(messageId) {
    try {
      const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
      const textElement = messageElement?.querySelector('.text');
      
      if (textElement) {
        const text = textElement.textContent;
        await navigator.clipboard.writeText(text);
        showToast('Texto copiado al portapapeles', 'success');
      }
    } catch (error) {
      console.error('Error copying text:', error);
      showToast('Error copiando texto', 'error');
    }
  }

  // ✅ Edita mensaje
  async editMessage(messageId) {
    try {
      const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
      const textElement = messageElement?.querySelector('.text');
      
      if (textElement) {
        const currentText = textElement.textContent;
        const newText = prompt('Editar mensaje:', currentText);
        
        if (newText !== null && newText !== currentText) {
          const response = await fetch(`/messages/${messageId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content_text: newText })
          });
          
          if (response.ok) {
            textElement.textContent = newText;
            showToast('Mensaje actualizado', 'success');
          } else {
            throw new Error('Error actualizando mensaje');
          }
        }
      }
    } catch (error) {
      console.error('Error editing message:', error);
      showToast('Error editando mensaje', 'error');
    }
  }

  // ✅ Elimina mensaje
  async deleteMessage(messageId) {
    try {
      if (confirm('¿Estás seguro de que quieres eliminar este mensaje?')) {
        const response = await fetch(`/messages/${messageId}`, {
          method: 'DELETE'
        });
        
        if (response.ok) {
          const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
          messageElement?.remove();
          showToast('Mensaje eliminado', 'success');
        } else {
          throw new Error('Error eliminando mensaje');
        }
      }
    } catch (error) {
      console.error('Error deleting message:', error);
      showToast('Error eliminando mensaje', 'error');
    }
  }

  // ✅ Crea to-do desde mensaje
  async createTodoFromMessage(messageId) {
    try {
      const response = await fetch(`/messages/${messageId}/todo`, {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (result.todo) {
        showToast('To-do creado exitosamente', 'success');
        // Opcional: actualizar la lista de to-dos en la interfaz
        await this.loadAthleteTodos();
      } else {
        showToast('No se pudo crear el to-do', 'info');
      }
      
    } catch (error) {
      console.error('Error creating todo:', error);
      showToast('Error creando to-do', 'error');
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
        ${isIncoming ? `
          <button class="btn mini" data-action="generate-highlights" data-message-id="${message.id}" title="Generar highlights">
            <i class="fa-solid fa-lightbulb"></i>
          </button>
          <button class="btn mini" data-action="suggest-reply" data-message-id="${message.id}" title="Sugerir respuesta">
            <i class="fa-solid fa-comment"></i>
          </button>
          <button class="btn mini" data-action="create-todo" data-message-id="${message.id}" title="Crear to-do">
            <i class="fa-solid fa-tasks"></i>
          </button>
          <button class="btn mini" data-action="copy-text" data-message-id="${message.id}" title="Copiar texto">
            <i class="fa-solid fa-copy"></i>
          </button>
          <button class="btn mini" data-action="edit-message" data-message-id="${message.id}" title="Editar mensaje">
            <i class="fa-solid fa-edit"></i>
          </button>
          <button class="btn mini danger" data-action="delete-message" data-message-id="${message.id}" title="Eliminar mensaje">
            <i class="fa-solid fa-trash"></i>
          </button>
        ` : `
          <button class="btn mini" data-action="edit-message" data-message-id="${message.id}" title="Editar respuesta">
            <i class="fa-solid fa-edit"></i>
          </button>
          <button class="btn mini" data-action="copy-text" data-message-id="${message.id}" title="Copiar texto">
            <i class="fa-solid fa-copy"></i>
          </button>
          <button class="btn mini danger" data-action="delete-message" data-message-id="${message.id}" title="Eliminar respuesta">
            <i class="fa-solid fa-trash"></i>
          </button>
        `}
      </div>
    `;
    
    // Add event listeners to the buttons
    const buttons = bubble.querySelectorAll('[data-action]');
    buttons.forEach(button => {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        const action = button.dataset.action;
        const messageId = parseInt(button.dataset.messageId);
        
        switch(action) {
          case 'generate-highlights':
            this.generateHighlightsForMessage(messageId);
            break;
          case 'suggest-reply':
            this.suggestReplyForMessage(messageId);
            break;
          case 'create-todo':
            this.createTodoFromMessage(messageId);
            break;
          case 'copy-text':
            this.copyMessageText(messageId);
            break;
          case 'edit-message':
            this.editMessage(messageId);
            break;
          case 'delete-message':
            this.deleteMessage(messageId);
            break;
        }
      });
    });
    
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
      item.dataset.highlightId = highlight.id;
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
            <button class="btn mini success" data-action="accept-highlight" data-highlight-id="${highlight.id}" title="Aceptar">
              <i class="fa-solid fa-check"></i>
            </button>
            <button class="btn mini danger" data-action="reject-highlight" data-highlight-id="${highlight.id}" title="Rechazar">
              <i class="fa-solid fa-times"></i>
            </button>
          ` : `
            <button class="btn mini pin-button" data-action="pin-highlight" data-highlight-id="${highlight.id}" title="Fijar">
              <i class="fa-solid fa-thumbtack"></i>
            </button>
            <button class="btn mini edit-button" data-action="edit-highlight" data-highlight-id="${highlight.id}" title="Editar">
              <i class="fa-solid fa-edit"></i>
            </button>
            <button class="btn mini tag-button" data-action="tag-highlight" data-highlight-id="${highlight.id}" title="Etiquetar">
              <i class="fa-solid fa-tags"></i>
            </button>
            <button class="btn mini todo-button" data-action="todo-highlight" data-highlight-id="${highlight.id}" title="Crear To-Do">
              <i class="fa-solid fa-tasks"></i>
            </button>
            <button class="btn mini delete-button" data-action="delete-highlight" data-highlight-id="${highlight.id}" title="Eliminar">
              <i class="fa-solid fa-trash"></i>
            </button>
          `}
        </div>
      `;
      
      // Add event listeners to highlight buttons
      const highlightButtons = item.querySelectorAll('[data-action]');
      highlightButtons.forEach(button => {
        button.addEventListener('click', (e) => {
          e.preventDefault();
          const action = button.dataset.action;
          const highlightId = parseInt(button.dataset.highlightId);
          
                     switch(action) {
             case 'accept-highlight':
               this.acceptHighlight(highlightId);
               break;
             case 'reject-highlight':
               this.rejectHighlight(highlightId);
               break;
             case 'pin-highlight':
               this.pinHighlight(highlightId);
               break;
             case 'edit-highlight':
               this.editHighlight(highlightId);
               break;
             case 'tag-highlight':
               this.tagHighlight(highlightId);
               break;
             case 'todo-highlight':
               this.createTodoFromHighlight(highlightId);
               break;
             case 'delete-highlight':
               this.deleteHighlight(highlightId);
               break;
           }
        });
      });
      
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

  // ✅ Edita highlight
  async editHighlight(highlightId) {
    try {
      const highlightElement = document.querySelector(`[data-highlight-id="${highlightId}"]`);
      const textElement = highlightElement?.querySelector('.highlight-title');
      
      if (textElement) {
        const currentText = textElement.textContent;
        const newText = prompt('Editar highlight:', currentText);
        
        if (newText !== null && newText !== currentText) {
          const response = await fetch(`/highlights/${highlightId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: newText })
          });
          
          if (response.ok) {
            textElement.textContent = newText;
            showToast('Highlight actualizado', 'success');
          } else {
            throw new Error('Error actualizando highlight');
          }
        }
      }
    } catch (error) {
      console.error('Error editing highlight:', error);
      showToast('Error editando highlight', 'error');
    }
  }

  // ✅ Fija/desfija highlight
  async pinHighlight(highlightId) {
    try {
      const response = await fetch(`/highlights/${highlightId}/pin`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        await this.loadAthleteHighlights();
        showToast('Highlight fijado/desfijado', 'success');
      } else {
        throw new Error('Error fijando highlight');
      }
    } catch (error) {
      console.error('Error pinning highlight:', error);
      showToast('Error fijando highlight', 'error');
    }
  }

  // ✅ Etiqueta highlight
  async tagHighlight(highlightId) {
    try {
      const highlightElement = document.querySelector(`[data-highlight-id="${highlightId}"]`);
      const currentCategory = highlightElement?.querySelector('.highlight-tag')?.textContent || '';
      
      const newCategory = prompt('Nueva categoría para el highlight:', currentCategory);
      
      if (newCategory !== null && newCategory !== currentCategory) {
        const response = await fetch(`/highlights/${highlightId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category: newCategory })
        });
        
        if (response.ok) {
          await this.loadAthleteHighlights();
          showToast('Categoría actualizada', 'success');
        } else {
          throw new Error('Error actualizando categoría');
        }
      }
    } catch (error) {
      console.error('Error tagging highlight:', error);
      showToast('Error etiquetando highlight', 'error');
    }
  }

  // ✅ Crea to-do desde highlight
  async createTodoFromHighlight(highlightId) {
    try {
      const response = await fetch(`/highlights/${highlightId}/todo`, {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (result.todo) {
        showToast('To-do creado desde highlight', 'success');
        await this.loadAthleteTodos();
      } else {
        showToast('No se pudo crear el to-do', 'info');
      }
      
    } catch (error) {
      console.error('Error creating todo from highlight:', error);
      showToast('Error creando to-do desde highlight', 'error');
    }
  }

  // ✅ Elimina highlight
  async deleteHighlight(highlightId) {
    try {
      if (confirm('¿Estás seguro de que quieres eliminar este highlight?')) {
        const response = await fetch(`/highlights/${highlightId}`, {
          method: 'DELETE'
        });
        
        if (response.ok) {
          await this.loadAthleteHighlights();
          showToast('Highlight eliminado', 'success');
        } else {
          throw new Error('Error eliminando highlight');
        }
      }
    } catch (error) {
      console.error('Error deleting highlight:', error);
      showToast('Error eliminando highlight', 'error');
    }
  }

  renderEmptyState() {
    const timeline = document.getElementById('timeline');
    const empty = document.getElementById('emptyTimeline');
    
    timeline.style.display = 'none';
    empty.style.display = 'block';
  }

  // Métodos adicionales para to-dos
  async editTodo(todoId) {
    const newTitle = prompt('Nuevo título para el to-do:', '');
    if (newTitle) {
      try {
        const response = await fetch(`/todos/${todoId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: newTitle })
        });
        if (response.ok) {
          showToast('To-do actualizado', 'success');
          await this.loadAthleteTodos();
        } else {
          throw new Error('Error actualizando to-do');
        }
      } catch (error) {
        console.error('Error editing todo:', error);
        showToast('Error editando to-do', 'error');
      }
    }
  }

  async deleteTodo(todoId) {
    if (confirm('¿Estás seguro de que quieres eliminar este to-do?')) {
      try {
        const response = await fetch(`/todos/${todoId}`, {
          method: 'DELETE'
        });
        if (response.ok) {
          showToast('To-do eliminado', 'success');
          await this.loadAthleteTodos();
        } else {
          throw new Error('Error eliminando to-do');
        }
      } catch (error) {
        console.error('Error deleting todo:', error);
        showToast('Error eliminando to-do', 'error');
      }
    }
  }

  // Métodos adicionales para respuesta sugerida
  showSuggestedReply(suggestedReply, messageId) {
    // Crear modal para mostrar respuesta sugerida
    const modal = document.createElement('div');
    modal.className = 'suggested-reply-modal';
    modal.innerHTML = `
      <div class="suggested-reply-overlay"></div>
      <div class="suggested-reply-content">
        <div class="suggested-reply-header">
          <h3>Respuesta Sugerida</h3>
          <button class="suggested-reply-close">
            <i class="fa-solid fa-times"></i>
          </button>
        </div>
        <div class="suggested-reply-text">${suggestedReply}</div>
        <div class="suggested-reply-actions">
          <button class="btn" data-action="cancel-reply">Cancelar</button>
          <button class="btn primary" data-action="send-reply" data-reply-text="${suggestedReply.replace(/"/g, '&quot;')}" data-message-id="${messageId}">
            <i class="fa-solid fa-paper-plane"></i> Enviar Respuesta
          </button>
        </div>
      </div>
    `;
    
    // Add event listeners to modal buttons
    const modalButtons = modal.querySelectorAll('[data-action]');
    modalButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        const action = button.dataset.action;
        
        switch(action) {
          case 'cancel-reply':
            modal.remove();
            break;
          case 'send-reply':
            const replyText = button.dataset.replyText;
            const messageId = parseInt(button.dataset.messageId);
            this.sendSuggestedReply(replyText, messageId);
            break;
        }
      });
    });
    
    document.body.appendChild(modal);
    
    // Cerrar modal al hacer clic en overlay o botón de cerrar
    modal.querySelector('.suggested-reply-overlay').addEventListener('click', () => modal.remove());
    modal.querySelector('.suggested-reply-close').addEventListener('click', () => modal.remove());
  }

  async sendSuggestedReply(replyText, messageId) {
    try {
      const response = await fetch('/send/whatsapp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          athlete_id: this.athleteId,
          message: replyText,
          reply_to_message_id: messageId
        })
      });
      
      const result = await response.json();
      
      if (result.status === 'sent') {
        showToast('Respuesta enviada exitosamente', 'success');
        // Cerrar modal
        document.querySelector('.suggested-reply-modal')?.remove();
        // Recargar conversación
        await this.loadConversations();
      } else {
        throw new Error(result.message || 'Error enviando respuesta');
      }
      
    } catch (error) {
      console.error('Error sending reply:', error);
      showToast('Error enviando respuesta', 'error');
    }
  }

  // ✅ Carga to-dos del atleta
  async loadAthleteTodos() {
    try {
      const response = await fetch(`/athletes/${this.athleteId}/todos`);
      const data = await response.json();
      
      const container = document.getElementById('todos');
      if (container) {
        this.renderTodos(data.todos);
      }
      
    } catch (error) {
      console.error('Error loading todos:', error);
    }
  }

  // ✅ Renderiza to-dos
  renderTodos(todos) {
    const container = document.getElementById('todos');
    if (!container) return;
    
    if (todos.length === 0) {
      container.innerHTML = '<div class="empty">No hay to-dos.</div>';
      return;
    }
    
    container.innerHTML = todos.map(todo => `
      <div class="todo-item" data-todo-id="${todo.id}">
        <div class="todo-content">
          <div class="todo-text">${todo.title}</div>
          <div class="todo-meta">
            <span class="prio ${todo.priority}">${todo.priority}</span>
            <span class="tag ${todo.status}">${todo.status}</span>
            ${todo.due_at ? `<span class="tag">${this.formatDate(todo.due_at)}</span>` : ''}
          </div>
        </div>
        <div class="todo-actions">
          <button class="btn mini" data-action="edit-todo" data-todo-id="${todo.id}" title="Editar">
            <i class="fa-solid fa-edit"></i>
          </button>
          <button class="btn mini danger" data-action="delete-todo" data-todo-id="${todo.id}" title="Eliminar">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
    `).join('');
    
    // Add event listeners to todo buttons
    const todoButtons = container.querySelectorAll('[data-action]');
    todoButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        const action = button.dataset.action;
        const todoId = parseInt(button.dataset.todoId);
        
        switch(action) {
          case 'edit-todo':
            this.editTodo(todoId);
            break;
          case 'delete-todo':
            this.deleteTodo(todoId);
            break;
        }
      });
    });
  }
}

// ✅ Inicialización modernizada
let workspace;

document.addEventListener('DOMContentLoaded', function() {
  const athleteId = document.querySelector('.app').dataset.athleteId;
  window.workspace = new WorkspaceManager(parseInt(athleteId));
  
  // Event listeners
  setupEventListeners();
  
  // Carga inicial
  window.workspace.loadConversations();
  window.workspace.loadAthleteHighlights();
  window.workspace.assessRisk();
});

// Global function for risk assessment trigger
function triggerRiskAssessment() {
  if (window.workspace) {
    window.workspace.assessRisk();
  }
}

function setupEventListeners() {
  // Audio input
  const audioInput = document.getElementById('audioInput');
  const dropzone = document.getElementById('dropzone');
  
  audioInput.addEventListener('change', (e) => {
    if (e.target.files[0]) {
      window.workspace.transcribeAudio(e.target.files[0]);
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
      window.workspace.transcribeAudio(files[0]);
    }
  });
  
  // Manual message input
  const inputMensaje = document.getElementById('inputMensaje');
  const btnAgregar = document.getElementById('btnAgregar');
  
  btnAgregar.addEventListener('click', () => {
    const text = inputMensaje.value.trim();
    if (text) {
      window.workspace.addManualMessage(text);
      inputMensaje.value = '';
    }
  });
  
  inputMensaje.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      btnAgregar.click();
    }
  });
  
  // Transcribe button
  const btnTranscribir = document.getElementById('btnTranscribir');
  btnTranscribir.addEventListener('click', () => {
    const audioInput = document.getElementById('audioInput');
    if (audioInput.files[0]) {
      window.workspace.transcribeAudio(audioInput.files[0]);
    } else {
      showToast('Por favor selecciona un archivo de audio primero', 'warning');
    }
  });

  // Responder button (AI response generation)
  const btnResponder = document.getElementById('btnResponder');
  btnResponder.addEventListener('click', () => {
    // Trigger AI response generation for the current conversation
    if (window.workspace.currentConversationId) {
      window.workspace.suggestReplyForMessage(window.workspace.currentConversationId);
    } else {
      showToast('No hay conversación activa para generar respuesta', 'warning');
    }
  });

  // Todo form
  const btnSendTodo = document.getElementById('btnSendTodo');
  btnSendTodo.addEventListener('click', () => {
    const text = document.getElementById('todoText').value.trim();
    const priority = document.getElementById('todoPriority').value;
    const dueDate = document.getElementById('todoDue').value;
    
    if (text) {
      window.workspace.sendTodoToCoach(text, priority, dueDate || null);
    }
  });
  
  // Highlights preview modal
  document.getElementById('closeHighlightsPreview').addEventListener('click', () => {
    window.workspace.hideHighlightsPreview();
  });
  
  document.getElementById('cancelHighlightsPreview').addEventListener('click', () => {
    window.workspace.hideHighlightsPreview();
  });
  
  document.getElementById('saveHighlightsPreview').addEventListener('click', () => {
    window.workspace.saveSelectedHighlights();
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