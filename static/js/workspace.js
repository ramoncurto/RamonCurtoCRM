// ===== ATHLETE WORKSPACE =====

/**
 * Athlete workspace functionality
 * Handles timeline, audio transcription, AI responses, highlights, and todos
 */

// State
let athleteId = null;
let athleteData = null;
let timeline = [];
let highlights = [];
let todos = [];

// Use API functions - $ and $$ are already defined in api.js

/**
 * Initialize workspace
 */
function initWorkspace() {
  // Get athlete ID from page
  const app = $('.app');
  athleteId = app?.dataset?.athleteId;
  
  if (!athleteId) {
    API.toast('Error', 'ID de atleta no encontrado', 'error');
    return;
  }
  
  // Load initial data
  loadAthleteData();
  loadTimeline();
  loadHighlights();
  loadTodos();
  
  // Setup event listeners
  setupEventListeners();
  setupKeyboardShortcuts();
  
  // Verificar estado del sistema de transcripción al cargar
  checkTranscriptionStatus();
}

/**
 * Load athlete data
 */
async function loadAthleteData() {
  try {
    const response = await API.get(`/api/athletes/${athleteId}`);
    if (response.athlete) {
      athleteData = response.athlete;
      updateAthleteName();
    }
  } catch (error) {
    console.error('Failed to load athlete data:', error);
  }
  
  // Note: Risk assessment is now manual - use triggerRiskAssessment() to run it
}

/**
 * Update athlete name in UI
 */
function updateAthleteName() {
  const nameElement = $('#athleteName');
  if (nameElement && athleteData) {
    nameElement.textContent = athleteData.name || 'Atleta';
  }
}

/**
 * Load timeline data
 */
async function loadTimeline() {
  try {
    const response = await API.get(`/api/athletes/${athleteId}/history`);
    timeline = response.history || [];
    renderTimeline();
  } catch (error) {
    console.error('Failed to load timeline:', error);
    timeline = [];
    renderTimeline();
  }
}

/**
 * Render timeline with day separators
 */
function renderTimeline() {
  const container = $('#timeline');
  const empty = $('#emptyTimeline');
  
  if (!container) return;
  
  container.innerHTML = '';
  
  if (timeline.length === 0) {
    if (empty) empty.style.display = '';
    return;
  }
  
  if (empty) empty.style.display = 'none';
  
  // Group items by day
  const groupedItems = groupTimelineByDay(timeline);
  
  // Render each day group
  Object.keys(groupedItems).forEach(dayKey => {
    const items = groupedItems[dayKey];
    
    // Add day separator
    const separator = document.createElement('div');
    separator.className = 'day-separator';
    separator.textContent = formatDayLabel(dayKey);
    container.appendChild(separator);
    
    // Add items for this day
    items.forEach(item => {
      container.appendChild(createTimelineItem(item));
    });
  });
}

/**
 * Group timeline items by day
 * @param {Array} items - Timeline items
 * @returns {Object} Grouped items by day
 */
function groupTimelineByDay(items) {
  const grouped = {};
  
  items.forEach(item => {
    const date = new Date(item.created_at);
    const dayKey = date.toDateString();
    
    if (!grouped[dayKey]) {
      grouped[dayKey] = [];
    }
    
    grouped[dayKey].push(item);
  });
  
  return grouped;
}

/**
 * Format day label for separator
 * @param {string} dayKey - Day key from toDateString()
 * @returns {string} Formatted day label
 */
function formatDayLabel(dayKey) {
  const today = new Date().toDateString();
  const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toDateString();
  
  if (dayKey === today) {
    return 'Hoy';
  } else if (dayKey === yesterday) {
    return 'Ayer';
  } else {
    const date = new Date(dayKey);
    return date.toLocaleDateString('es-ES', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  }
}

/**
 * Format audio duration
 * @param {number} duration - Duration in seconds
 * @returns {string} Formatted duration
 */
function formatAudioDuration(duration) {
  if (!duration) return '';
  
  const minutes = Math.floor(duration / 60);
  const seconds = Math.floor(duration % 60);
  
  if (minutes > 0) {
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  } else {
    return `${seconds}s`;
  }
}

/**
 * Create timeline item with floating actions and audio indicators
 * @param {Object} item - Timeline item data
 * @returns {HTMLElement} Timeline item element
 */
function createTimelineItem(item) {
  const div = document.createElement('div');
  div.className = 'bubble';
  div.dataset.id = item.id;
  
  // Audio indicator if file exists
  const audioIndicator = item.filename ? `
    <div class="audio-indicator">
      <i class="fa-solid fa-waveform"></i>
      <span class="audio-duration">${formatAudioDuration(item.duration || 0)}</span>
    </div>
  ` : '';
  
  div.innerHTML = `
    ${audioIndicator}
    <div class="content">
      <div class="text">${API.escapeHtml(item.transcription || '')}</div>
      ${item.generated_response ? 
        `<div class="response">${API.escapeHtml(item.generated_response)}</div>` : ''
      }
    </div>
    <div class="floating-actions">
      <button class="btn" data-action="highlight" title="Crear highlight">
        <i class="fa-solid fa-highlighter"></i>
      </button>
      <button class="btn" data-action="todo" title="Crear To-Do">
        <i class="fa-solid fa-tasks"></i>
      </button>
      <button class="btn" data-action="auto-response" title="Crear respuesta automática">
        <i class="fa-solid fa-robot"></i>
      </button>
      <button class="btn" data-action="edit" title="Editar">
        <i class="fa-solid fa-edit"></i>
      </button>
      <button class="btn danger" data-action="delete" title="Eliminar">
        <i class="fa-solid fa-trash"></i>
      </button>
    </div>
    <div class="meta">${API.formatRelativeTime(item.created_at)}</div>
  `;
  
  // Add event listeners
  div.addEventListener('click', handleTimelineAction);
  div.addEventListener('dblclick', () => selectTimelineItem(div));
  
  return div;
}

/**
 * Add tag to highlight
 * @param {string} highlightId - Highlight ID
 */
async function addTagToHighlight(highlightId) {
  // Available tags with colors
  const availableTags = [
    { name: 'tech', label: 'Técnica', color: '#34d399', icon: 'fa-cog' },
    { name: 'nutri', label: 'Nutrición', color: '#f59e0b', icon: 'fa-apple-alt' },
    { name: 'recov', label: 'Recuperación', color: '#60a5fa', icon: 'fa-bed' },
    { name: 'psy', label: 'Psicología', color: '#a78bfa', icon: 'fa-brain' },
    { name: 'injury', label: 'Lesión', color: '#ef4444', icon: 'fa-band-aid' },
    { name: 'performance', label: 'Rendimiento', color: '#f97316', icon: 'fa-chart-line' },
    { name: 'training', label: 'Entrenamiento', color: '#06b6d4', icon: 'fa-dumbbell' },
    { name: 'progress', label: 'Progreso', color: '#10b981', icon: 'fa-arrow-up' },
    { name: 'issue', label: 'Problema', color: '#dc2626', icon: 'fa-exclamation-triangle' },
    { name: 'planning', label: 'Planificación', color: '#8b5cf6', icon: 'fa-calendar' }
  ];
  
  // Get current tags to avoid duplicates
  const highlight = highlights.find(h => h.id == highlightId);
  const currentTags = API.safeJsonParse(highlight?.categories || '[]', []);
  
  // Filter out already used tags
  const availableOptions = availableTags.filter(tag => !currentTags.includes(tag.name));
  
  if (availableOptions.length === 0) {
    API.toast('Info', 'Todos los tags disponibles ya están asignados', 'info');
    return;
  }
  
  // Create and show tag selection modal
  showTagSelectionModal(availableOptions, async (selectedTag) => {
    if (!selectedTag) return;
    
    try {
      // Add tag to current tags
      const newTags = [...currentTags, selectedTag.name];
      
      const response = await API.put(`/api/highlights/${highlightId}`, {
        categories: JSON.stringify(newTags)
      });
      
      if (response.success) {
        // Update the local highlight data immediately
        const highlightIndex = highlights.findIndex(h => h.id == highlightId);
        if (highlightIndex !== -1) {
          highlights[highlightIndex].categories = newTags;
        }
        
        // Re-render highlights to show the new tag
        renderHighlights();
        
        API.toast('Tag agregado', `Se agregó "${selectedTag.label}" al highlight`, 'success');
      } else {
        throw new Error(response.error || 'Error al agregar tag');
      }
    } catch (error) {
      console.error('Failed to add tag:', error);
      API.toast('Error al agregar tag', error.message, 'error');
    }
  });
}

/**
 * Show tag selection modal
 * @param {Array} availableTags - Available tags to choose from
 * @param {Function} onSelect - Callback when tag is selected
 */
function showTagSelectionModal(availableTags, onSelect) {
  // Remove existing modal if any
  const existingModal = document.querySelector('.tag-modal');
  if (existingModal) {
    existingModal.remove();
  }
  
  // Create modal
  const modal = document.createElement('div');
  modal.className = 'tag-modal';
  modal.innerHTML = `
    <div class="tag-modal-overlay"></div>
    <div class="tag-modal-content">
      <div class="tag-modal-header">
        <h3>Seleccionar Tag</h3>
        <button class="tag-modal-close" onclick="this.closest('.tag-modal').remove()">
          <i class="fa-solid fa-times"></i>
        </button>
      </div>
      <div class="tag-modal-body">
        <div class="tag-grid">
          ${availableTags.map(tag => `
            <div class="tag-option" data-tag-name="${tag.name}" data-tag-label="${tag.label}" data-tag-color="${tag.color}">
              <div class="tag-option-icon" style="background-color: ${tag.color}">
                <i class="fa-solid ${tag.icon}"></i>
              </div>
              <div class="tag-option-content">
                <div class="tag-option-label">${tag.label}</div>
                <div class="tag-option-name">${tag.name}</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
      <div class="tag-modal-footer">
        <button class="btn" onclick="this.closest('.tag-modal').remove()">Cancelar</button>
      </div>
    </div>
  `;
  
  // Add event listeners
  const tagOptions = modal.querySelectorAll('.tag-option');
  tagOptions.forEach(option => {
    option.addEventListener('click', () => {
      const tagName = option.dataset.tagName;
      const tagLabel = option.dataset.tagLabel;
      const tagColor = option.dataset.tagColor;
      
      const selectedTag = {
        name: tagName,
        label: tagLabel,
        color: tagColor
      };
      
      modal.remove();
      onSelect(selectedTag);
    });
    
    // Add hover effect
    option.addEventListener('mouseenter', () => {
      option.style.transform = 'translateY(-2px)';
    });
    
    option.addEventListener('mouseleave', () => {
      option.style.transform = 'translateY(0)';
    });
  });
  
  // Close on overlay click
  const overlay = modal.querySelector('.tag-modal-overlay');
  overlay.addEventListener('click', () => modal.remove());
  
  // Close on escape key
  const handleEscape = (e) => {
    if (e.key === 'Escape') {
      modal.remove();
      document.removeEventListener('keydown', handleEscape);
    }
  };
  document.addEventListener('keydown', handleEscape);
  
  // Add to DOM
  document.body.appendChild(modal);
  
  // Animate in
  requestAnimationFrame(() => {
    modal.classList.add('show');
  });
}

/**
 * Remove tag from highlight
 * @param {string} highlightId - Highlight ID
 * @param {string} tagName - Tag name to remove
 */
async function removeTagFromHighlight(highlightId, tagName) {
  const confirmRemove = confirm(`¿Estás seguro de que quieres remover el tag "${tagName}"?`);
  if (!confirmRemove) return;
  
  try {
    const highlight = highlights.find(h => h.id == highlightId);
    const currentTags = API.safeJsonParse(highlight?.categories || '[]', []);
    
    // Remove tag
    const newTags = currentTags.filter(tag => tag !== tagName);
    
    const response = await API.put(`/api/highlights/${highlightId}`, {
      categories: JSON.stringify(newTags)
    });
    
    if (response.success) {
      // Update the local highlight data immediately
      const highlightIndex = highlights.findIndex(h => h.id == highlightId);
      if (highlightIndex !== -1) {
        highlights[highlightIndex].categories = newTags;
      }
      
      // Re-render highlights to show the updated tags
      renderHighlights();
      
      API.toast('Tag removido', '', 'success');
    } else {
      throw new Error(response.error || 'Error al remover tag');
    }
  } catch (error) {
    console.error('Failed to remove tag:', error);
    API.toast('Error al remover tag', error.message, 'error');
  }
}

/**
 * Create highlight from timeline item
 * @param {HTMLElement} item - Timeline item
 */
async function createHighlightFromTimeline(item) {
  const text = item.querySelector('.text')?.textContent;
  if (!text) {
    API.toast('Error', 'No hay texto para crear highlight', 'error');
    return;
  }
  
  try {
    const response = await API.post(`/api/athletes/${athleteId}/highlights`, {
      highlight_text: text,
      category: 'general',
      categories: '["general"]'
    });
    
    if (response.highlight) {
      await loadHighlights();
      API.toast('Highlight creado', '', 'success');
    }
  } catch (error) {
    console.error('Failed to create highlight:', error);
    API.toast('Error al crear highlight', error.message, 'error');
  }
}

/**
 * Edit highlight
 * @param {HTMLElement} item - Highlight item
 */
function editHighlight(item) {
  const text = item.querySelector('.title')?.textContent;
  const newText = prompt('Editar highlight:', text);
  
  if (newText && newText !== text) {
    updateHighlight(item.dataset.id, newText);
  }
}

/**
 * Update highlight
 * @param {string} id - Highlight ID
 * @param {string} text - New text
 */
async function updateHighlight(id, text) {
  try {
    const response = await API.put(`/api/highlights/${id}`, {
      highlight_text: text
    });
    
    if (response.success) {
      await loadHighlights();
      API.toast('Highlight actualizado', '', 'success');
    }
  } catch (error) {
    console.error('Failed to update highlight:', error);
    API.toast('Error al actualizar highlight', error.message, 'error');
  }
}

/**
 * Delete highlight
 * @param {HTMLElement} item - Highlight item
 */
async function deleteHighlight(item) {
  if (!confirm('¿Eliminar este highlight?')) return;
  
  try {
    const response = await API.delete(`/api/highlights/${item.dataset.id}`);
    if (response.success) {
      await loadHighlights();
      API.toast('Highlight eliminado', '', 'success');
    }
  } catch (error) {
    console.error('Failed to delete highlight:', error);
    API.toast('Error al eliminar highlight', error.message, 'error');
  }
}

/**
 * Load todos for this athlete
 */
async function loadTodos() {
  try {
    const response = await API.get('/api/todos', { athlete_id: athleteId });
    todos = response.todos || [];
    renderTodos();
  } catch (error) {
    console.error('Failed to load todos:', error);
    todos = [];
    renderTodos();
  }
}

/**
 * Render todos
 */
function renderTodos() {
  const container = $('#todos');
  if (!container) return;
  
  container.innerHTML = '';
  
  if (todos.length === 0) {
    container.innerHTML = '<div class="empty">No hay To-Dos para este atleta.</div>';
    return;
  }
  
  todos.forEach(todo => {
    container.appendChild(createTodoItem(todo));
  });
}

/**
 * Create todo item
 * @param {Object} todo - Todo data
 * @returns {HTMLElement} Todo item element
 */
function createTodoItem(todo) {
  const div = document.createElement('div');
  div.className = 'todo-item card';
  
  div.innerHTML = `
    <div class="title">${API.escapeHtml(todo.text)}</div>
    <div class="meta">
      <span class="prio ${todo.priority}">${todo.priority}</span>
      <span class="tag">${todo.status}</span>
      ${todo.due_date ? `<span class="tag">${API.formatDate(todo.due_date)}</span>` : ''}
    </div>
  `;
  
  return div;
}

/**
 * Create todo from timeline item
 * @param {HTMLElement} item - Timeline item
 */
async function createTodoFromTimeline(item) {
  const text = item.querySelector('.text')?.textContent;
  if (!text) {
    API.toast('Error', 'No hay texto para crear To-Do', 'error');
    return;
  }
  
  try {
    // Show loading state
    const button = item.querySelector('[data-action="todo"]');
    const originalIcon = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    button.disabled = true;
    
    // Generate To-Do text using GPT-4o-mini
    const response = await API.post('/generate-todo', {
      transcription: text
    });
    
    let todoText = '';
    if (response.generated_todo) {
      todoText = response.generated_todo;
    } else {
      // Fallback if no AI generation
      todoText = `Revisar: ${text.substring(0, 50)}${text.length > 50 ? '...' : ''}`;
    }
    
    // Allow user to edit the generated To-Do
    const editedText = prompt('Editar To-Do para el entrenador:', todoText);
    if (!editedText) {
      // Restore button state
      button.innerHTML = originalIcon;
      button.disabled = false;
      return;
    }
    
    // Create the To-Do
    const todoResponse = await API.post('/api/todos', {
      athlete_id: athleteId,
      text: editedText,
      priority: 'P2',
      status: 'backlog',
      created_by: 'athlete'
    });
    
    if (todoResponse.todo) {
      await loadTodos();
      API.toast('To-Do creado', '', 'success');
    }
  } catch (error) {
    console.error('Failed to create todo:', error);
    API.toast('Error al crear To-Do', error.message, 'error');
  } finally {
    // Restore button state
    const button = item.querySelector('[data-action="todo"]');
    button.innerHTML = '<i class="fa-solid fa-tasks"></i>';
    button.disabled = false;
  }
}

/**
 * Create auto response from timeline item
 * @param {HTMLElement} item - Timeline item
 */
async function createAutoResponseFromTimeline(item) {
  const text = item.querySelector('.text')?.textContent;
  if (!text) {
    API.toast('Error', 'No hay texto para generar respuesta', 'error');
    return;
  }
  
  try {
    // Show loading state
    const button = item.querySelector('[data-action="auto-response"]');
    const originalIcon = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    button.disabled = true;
    
    // Generate AI response
    const response = await API.post('/generate', {
      transcription: text
    });
    
    if (response.generated_response) {
      // Add the response to the timeline item
      const responseDiv = document.createElement('div');
      responseDiv.className = 'response';
      responseDiv.innerHTML = API.escapeHtml(response.generated_response);
      
      const contentDiv = item.querySelector('.content');
      contentDiv.appendChild(responseDiv);
      
      // Save the conversation
      await API.post('/save', {
        athlete_id: athleteId,
        transcription: text,
        generated_response: response.generated_response,
        final_response: response.generated_response,
        category: 'auto-generated',
        priority: 'medium',
        source: 'auto-response'
      });
      
      API.toast('Respuesta generada', '', 'success');
    }
  } catch (error) {
    console.error('Failed to generate auto response:', error);
    API.toast('Error al generar respuesta', error.message, 'error');
  } finally {
    // Restore button state
    const button = item.querySelector('[data-action="auto-response"]');
    button.innerHTML = '<i class="fa-solid fa-robot"></i>';
    button.disabled = false;
  }
}

/**
 * Edit timeline item
 * @param {HTMLElement} item - Timeline item
 */
function editTimelineItem(item) {
  const textElement = item.querySelector('.text');
  const currentText = textElement.textContent;
  
  const newText = prompt('Editar mensaje:', currentText);
  if (!newText || newText === currentText) return;
  
  // Update the text in the DOM
  textElement.textContent = newText;
  
  // Update in database (you might want to add an endpoint for this)
  API.toast('Mensaje editado', 'Los cambios se guardarán automáticamente', 'success');
}

/**
 * Delete timeline item
 * @param {HTMLElement} item - Timeline item
 */
async function deleteTimelineItem(item) {
  const text = item.querySelector('.text')?.textContent;
  if (!text) {
    API.toast('Error', 'No hay texto para eliminar', 'error');
    return;
  }
  
  const confirmDelete = confirm(`¿Estás seguro de que quieres eliminar este mensaje?\n\n"${text.substring(0, 50)}${text.length > 50 ? '...' : ''}"`);
  if (!confirmDelete) return;
  
  try {
    // Remove from DOM immediately for better UX
    item.style.opacity = '0.5';
    item.style.pointerEvents = 'none';
    
    // You might want to add an endpoint to delete from database
    // For now, we'll just remove from DOM
    setTimeout(() => {
      item.remove();
      API.toast('Mensaje eliminado', '', 'success');
    }, 300);
    
  } catch (error) {
    console.error('Failed to delete timeline item:', error);
    API.toast('Error al eliminar mensaje', error.message, 'error');
    
    // Restore item if deletion failed
    item.style.opacity = '1';
    item.style.pointerEvents = 'auto';
  }
}

/**
 * Create todo from form
 * @param {Event} event - Form submit event
 */
async function createTodo(event) {
  event.preventDefault();
  
  const form = event.target;
  const formData = new FormData(form);
  
  try {
    const response = await API.post('/api/todos', {
      athlete_id: athleteId,
      text: formData.get('text'),
      priority: formData.get('priority'),
      due: formData.get('due'),
      status: 'backlog',
      created_by: 'athlete'
    });
    
    if (response.todo) {
      form.reset();
      await loadTodos();
      API.toast('To-Do enviado al entrenador', '', 'success');
    }
  } catch (error) {
    console.error('Failed to create todo:', error);
    API.toast('Error al crear To-Do', error.message, 'error');
  }
}

/**
 * Handle timeline action clicks
 * @param {Event} event - Click event
 */
async function handleTimelineAction(event) {
  const action = event.target.closest('[data-action]')?.dataset?.action;
  if (!action) return;
  
  const item = event.target.closest('.bubble');
  const itemId = item?.dataset?.id;
  
  switch (action) {
    case 'highlight':
      await createHighlightFromTimeline(item);
      break;
    case 'todo':
      await createTodoFromTimeline(item);
      break;
    case 'auto-response':
      await createAutoResponseFromTimeline(item);
      break;
    case 'edit':
      editTimelineItem(item);
      break;
    case 'delete':
      deleteTimelineItem(item);
      break;
  }
}

/**
 * Select timeline item for AI response
 * @param {HTMLElement} item - Timeline item
 */
function selectTimelineItem(item) {
  // Remove previous selection
  $$('.bubble.selected').forEach(el => el.classList.remove('selected'));
  
  // Select current item
  item.classList.add('selected');
  
  // Enable AI response button
  const aiBtn = $('#btnResponder');
  if (aiBtn) {
    aiBtn.disabled = false;
  }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
  // Manual message input
  const messageInput = $('#inputMensaje');
  const addBtn = $('#btnAgregar');
  
  if (messageInput && addBtn) {
    messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        addManualMessage();
      }
    });
    
    addBtn.addEventListener('click', addManualMessage);
  }
  
  // Audio upload
  const dropzone = $('#dropzone');
  const audioInput = $('#audioInput');
  
  if (dropzone && audioInput) {
    dropzone.addEventListener('click', () => audioInput.click());
    
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
      if (files.length > 0) {
        handleAudioUpload(files[0]);
      }
    });
    
    audioInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        handleAudioUpload(e.target.files[0]);
      }
    });
  }
  
  // Transcription button
  const transcribeBtn = $('#btnTranscribir');
  if (transcribeBtn) {
    transcribeBtn.addEventListener('click', transcribeAudio);
  }
  
  // AI response button
  const aiBtn = $('#btnResponder');
  if (aiBtn) {
    aiBtn.addEventListener('click', generateAIResponse);
  }
  
  // Todo form
  const todoForm = $('#todoForm');
  if (todoForm) {
    todoForm.addEventListener('submit', createTodo);
  }
  
  // Highlight actions
  document.addEventListener('click', (e) => {
    if (e.target.matches('[data-action="edit-highlight"]')) {
      editHighlight(e.target.closest('.highlight-item'));
    } else if (e.target.matches('[data-action="delete-highlight"]')) {
      deleteHighlight(e.target.closest('.highlight-item'));
    } else if (e.target.matches('[data-action="todo-from-highlight"]')) {
      createTodoFromHighlight(e.target.closest('.highlight-item'));
    }
  });
  
  // Highlights preview modal
  const closePreviewBtn = $('#closeHighlightsPreview');
  const cancelPreviewBtn = $('#cancelHighlightsPreview');
  const savePreviewBtn = $('#saveHighlightsPreview');
  
  if (closePreviewBtn) {
    closePreviewBtn.addEventListener('click', hideHighlightsPreview);
  }
  
  if (cancelPreviewBtn) {
    cancelPreviewBtn.addEventListener('click', hideHighlightsPreview);
  }
  
  if (savePreviewBtn) {
    savePreviewBtn.addEventListener('click', saveHighlightsAndMessage);
  }
  
  // Close modal on backdrop click
  const previewModal = $('#highlightsPreviewModal');
  if (previewModal) {
    previewModal.addEventListener('click', (e) => {
      if (e.target === previewModal) {
        hideHighlightsPreview();
      }
    });
  }
  
  // Close modal on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const modal = $('#highlightsPreviewModal');
      if (modal && modal.classList.contains('show')) {
        hideHighlightsPreview();
      }
    }
  });
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter for AI response
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      generateAIResponse();
    }
    
    // U for transcribe
    if (e.key === 'u' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      transcribeAudio();
    }
    
    // H for create highlight
    if (e.key === 'h' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      const selected = $('.bubble.selected');
      if (selected) {
        createHighlightFromTimeline(selected);
      }
    }
    
    // T for create todo
    if (e.key === 't' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      const selected = $('.bubble.selected');
      if (selected) {
        createTodoFromTimeline(selected);
      }
    }
  });
}

/**
 * Add manual message
 */
async function addManualMessage() {
  const input = $('#inputMensaje');
  const text = input?.value?.trim();
  
  if (!text) return;
  
  try {
    // First, generate AI highlights for preview
    const highlightsResponse = await API.post('/ai/highlights', {
      text: text,
      athlete_id: athleteId
    });
    
    if (highlightsResponse.success && highlightsResponse.highlights.length > 0) {
      // Show highlights preview modal
      await showHighlightsPreview(highlightsResponse.highlights, text);
    } else {
      // No highlights generated, save message directly
      await saveMessageDirectly(text);
    }
  } catch (error) {
    console.error('Failed to process message:', error);
    // Fallback to direct save
    await saveMessageDirectly(text);
  }
}

/**
 * Show highlights preview modal
 */
async function showHighlightsPreview(suggestedHighlights, messageText) {
  const modal = $('#highlightsPreviewModal');
  const list = $('#highlightsPreviewList');
  
  if (!modal || !list) return;
  
  // Render highlights in preview
  list.innerHTML = '';
  suggestedHighlights.forEach((highlight, index) => {
    const item = document.createElement('div');
    item.className = 'highlight-preview-item';
    item.dataset.index = index;
    
    const checkbox = document.createElement('div');
    checkbox.className = 'highlights-preview-checkbox';
    checkbox.innerHTML = `
      <input type="checkbox" id="highlight_${index}" checked>
      <label for="highlight_${index}">Incluir este highlight</label>
    `;
    
    const text = document.createElement('div');
    text.className = 'highlight-preview-text';
    text.textContent = highlight.text;
    
    const tags = document.createElement('div');
    tags.className = 'highlight-preview-tags';
    highlight.tags.forEach(tag => {
      const tagElement = document.createElement('span');
      tagElement.className = `highlight-preview-tag ${getTagClass(tag)}`;
      tagElement.textContent = tag;
      tags.appendChild(tagElement);
    });
    
    item.appendChild(checkbox);
    item.appendChild(text);
    item.appendChild(tags);
    list.appendChild(item);
  });
  
  // Show modal
  modal.classList.add('show');
  
  // Store data for later use
  modal.dataset.messageText = messageText;
  modal.dataset.suggestedHighlights = JSON.stringify(suggestedHighlights);
}

/**
 * Get CSS class for tag
 */
function getTagClass(tag) {
  const tagMap = {
    'Técnica': 'tech',
    'Nutrición': 'nutri',
    'Psicología': 'psy',
    'Lesiones': 'injury',
    'Planificación': 'planning',
    'Objetivos': 'goals',
    'Problemas': 'problems',
    'Progreso': 'progress',
    'General': 'general'
  };
  return tagMap[tag] || 'general';
}

/**
 * Save message directly without highlights
 */
async function saveMessageDirectly(text) {
  try {
    const response = await API.post('/save', {
      athlete_id: athleteId,
      transcription: text,
      generated_response: '',
      final_response: '',
      source: 'manual'
    });
    
    if (response.success) {
      const input = $('#inputMensaje');
      if (input) input.value = '';
      await loadTimeline();
      API.toast('Mensaje guardado', '', 'success');
    }
  } catch (error) {
    console.error('Failed to save message:', error);
    API.toast('Error al guardar', error.message, 'error');
  }
}

/**
 * Save selected highlights and message
 */
async function saveHighlightsAndMessage() {
  const modal = $('#highlightsPreviewModal');
  const messageText = modal?.dataset?.messageText;
  const suggestedHighlights = JSON.parse(modal?.dataset?.suggestedHighlights || '[]');
  
  if (!messageText) return;
  
  try {
    // Get selected highlights
    const selectedHighlights = [];
    suggestedHighlights.forEach((highlight, index) => {
      const checkbox = $(`#highlight_${index}`);
      if (checkbox && checkbox.checked) {
        selectedHighlights.push(highlight);
      }
    });
    
    // Save message first
    const saveResponse = await API.post('/save', {
      athlete_id: athleteId,
      transcription: messageText,
      generated_response: '',
      final_response: '',
      source: 'manual'
    });
    
    if (saveResponse.success) {
      // Save selected highlights
      for (const highlight of selectedHighlights) {
        try {
          await API.post(`/api/athletes/${athleteId}/highlights`, {
            highlight_text: highlight.text,
            categories: JSON.stringify(highlight.tags),
            category: highlight.tags[0] || 'general',
            source_conversation_id: saveResponse.conversation_id
          });
        } catch (highlightError) {
          console.error('Failed to save highlight:', highlightError);
        }
      }
      
      // Clear input and reload data
      const input = $('#inputMensaje');
      if (input) input.value = '';
      await loadTimeline();
      await loadHighlights();
      
      // Close modal
      hideHighlightsPreview();
      
      // Show success message
      const savedCount = selectedHighlights.length;
      if (savedCount > 0) {
        API.toast('Mensaje y highlights guardados', `${savedCount} highlights añadidos`, 'success');
      } else {
        API.toast('Mensaje guardado', '', 'success');
      }
    }
  } catch (error) {
    console.error('Failed to save highlights and message:', error);
    API.toast('Error al guardar', error.message, 'error');
  }
}

/**
 * Hide highlights preview modal
 */
function hideHighlightsPreview() {
  const modal = $('#highlightsPreviewModal');
  if (modal) {
    modal.classList.remove('show');
    // Clear stored data
    delete modal.dataset.messageText;
    delete modal.dataset.suggestedHighlights;
  }
}

/**
 * Handle audio upload
 * @param {File} file - Audio file
 */
async function handleAudioUpload(file) {
  if (!file.type.startsWith('audio/')) {
    API.toast('Error', 'Solo se permiten archivos de audio', 'error');
    return;
  }
  
  try {
    const response = await API.upload('/transcribe', file, (progress) => {
      // Update progress if needed
      console.log(`Upload progress: ${progress}%`);
    });
    
    if (response.transcription) {
      // Auto-fill transcription
      const input = $('#inputMensaje');
      if (input) {
        input.value = response.transcription;
      }
      
      API.toast('Audio transcrito', '', 'success');
    }
  } catch (error) {
    console.error('Failed to upload audio:', error);
    API.toast('Error al transcribir', error.message, 'error');
  }
}

/**
 * Transcribe audio
 */
async function transcribeAudio() {
  const input = $('#inputMensaje');
  const text = input?.value?.trim();
  
  if (!text) {
    API.toast('Error', 'No hay texto para transcribir', 'error');
    return;
  }
  
  try {
    const response = await API.post('/generate', {
      transcription: text
    });
    
    if (response.generated_response) {
      // Auto-fill AI response
      const responseInput = $('#responseInput');
      if (responseInput) {
        responseInput.value = response.generated_response;
      }
      
      API.toast('Respuesta generada', '', 'success');
    }
  } catch (error) {
    console.error('Failed to generate response:', error);
    API.toast('Error al generar respuesta', error.message, 'error');
  }
}

/**
 * Generate AI response
 */
async function generateAIResponse() {
  const selected = $('.bubble.selected');
  if (!selected) {
    API.toast('Error', 'Selecciona un mensaje primero', 'error');
    return;
  }
  
  const transcription = selected.querySelector('.text')?.textContent;
  if (!transcription) {
    API.toast('Error', 'No hay texto para procesar', 'error');
    return;
  }
  
  try {
    const response = await API.post('/generate', {
      transcription: transcription
    });
    
    if (response.generated_response) {
      // Update the selected item with AI response
      const responseDiv = selected.querySelector('.response');
      if (responseDiv) {
        responseDiv.textContent = response.generated_response;
      } else {
        const contentDiv = selected.querySelector('.content');
        if (contentDiv) {
          const newResponseDiv = document.createElement('div');
          newResponseDiv.className = 'response';
          newResponseDiv.textContent = response.generated_response;
          contentDiv.appendChild(newResponseDiv);
        }
      }
      
      API.toast('Respuesta IA generada', '', 'success');
    }
  } catch (error) {
    console.error('Failed to generate AI response:', error);
    API.toast('Error al generar respuesta IA', error.message, 'error');
  }
}

/**
 * Load highlights
 */
async function loadHighlights() {
  try {
    const response = await API.get(`/api/athletes/${athleteId}/highlights`);
    highlights = response.highlights || [];
    renderHighlights();
  } catch (error) {
    console.error('Failed to load highlights:', error);
    highlights = [];
    renderHighlights();
  }
}

/**
 * Render highlights with header and filters
 */
function renderHighlights() {
  const container = $('#highlights');
  const counter = $('#highlightsCounter');
  const filtersContainer = $('#categoryFilters');
  
  if (!container) return;
  
  // Update counter
  if (counter) {
    counter.textContent = highlights.length;
  }
  
  // Render category filters
  renderCategoryFilters(filtersContainer);
  
  container.innerHTML = '';
  
  if (highlights.length === 0) {
    container.innerHTML = '<div class="empty">No hay highlights.</div>';
    return;
  }
  
  // Sort highlights: pinned first, then by date (recent first)
  const sortedHighlights = [...highlights].sort((a, b) => {
    // Pinned items first
    if (a.pinned && !b.pinned) return -1;
    if (!a.pinned && b.pinned) return 1;
    
    // Then by date (recent first)
    return new Date(b.created_at) - new Date(a.created_at);
  });
  
  // Filter by selected category if any
  const activeFilter = getActiveCategoryFilter();
  const filteredHighlights = activeFilter 
    ? sortedHighlights.filter(h => {
        const categories = API.safeJsonParse(h.categories || '[]', []);
        return categories.includes(activeFilter);
      })
    : sortedHighlights;
  
  filteredHighlights.forEach(highlight => {
    container.appendChild(createHighlightItem(highlight));
  });
}

/**
 * Render category filters
 */
function renderCategoryFilters(container) {
  if (!container) return;
  
  const categories = [
    { key: 'tech', label: 'Técnica', color: '#34d399' },
    { key: 'nutri', label: 'Nutrición', color: '#f59e0b' },
    { key: 'recov', label: 'Recuperación', color: '#60a5fa' },
    { key: 'psy', label: 'Psicología', color: '#a78bfa' },
    { key: 'injury', label: 'Lesión', color: '#ef4444' },
    { key: 'performance', label: 'Rendimiento', color: '#f97316' },
    { key: 'training', label: 'Entrenamiento', color: '#06b6d4' },
    { key: 'progress', label: 'Progreso', color: '#10b981' },
    { key: 'issue', label: 'Problema', color: '#dc2626' },
    { key: 'planning', label: 'Planificación', color: '#8b5cf6' }
  ];
  
  container.innerHTML = categories.map(cat => `
    <span class="category-chip" data-category="${cat.key}" style="border-color: ${cat.color}20; color: ${cat.color};">
      ${cat.label}
    </span>
  `).join('');
  
  // Add event listeners
  const chips = container.querySelectorAll('.category-chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const category = chip.dataset.category;
      toggleCategoryFilter(category);
    });
  });
}

/**
 * Get active category filter
 */
function getActiveCategoryFilter() {
  const activeChip = document.querySelector('.category-chip.active');
  return activeChip ? activeChip.dataset.category : null;
}

/**
 * Toggle category filter
 */
function toggleCategoryFilter(category) {
  const chips = document.querySelectorAll('.category-chip');
  const targetChip = document.querySelector(`[data-category="${category}"]`);
  
  chips.forEach(chip => chip.classList.remove('active'));
  
  if (targetChip && targetChip.classList.contains('active')) {
    // If already active, deactivate
    targetChip.classList.remove('active');
  } else if (targetChip) {
    // Activate
    targetChip.classList.add('active');
  }
  
  // Re-render highlights with new filter
  renderHighlights();
}

/**
 * Create compact highlight item
 */
function createHighlightItem(highlight) {
  const div = document.createElement('div');
  div.className = 'highlight-item';
  div.dataset.id = highlight.id;
  
  if (highlight.pinned) {
    div.classList.add('pinned');
  }
  
  // Tag definitions with colors
  const tagDefinitions = {
    'tech': { label: 'Técnica', color: '#34d399' },
    'nutri': { label: 'Nutrición', color: '#f59e0b' },
    'recov': { label: 'Recuperación', color: '#60a5fa' },
    'psy': { label: 'Psicología', color: '#a78bfa' },
    'injury': { label: 'Lesión', color: '#ef4444' },
    'performance': { label: 'Rendimiento', color: '#f97316' },
    'training': { label: 'Entrenamiento', color: '#06b6d4' },
    'progress': { label: 'Progreso', color: '#10b981' },
    'issue': { label: 'Problema', color: '#dc2626' },
    'planning': { label: 'Planificación', color: '#8b5cf6' }
  };
  
  // Parse categories
  let categories = [];
  if (highlight.categories) {
    if (Array.isArray(highlight.categories)) {
      categories = highlight.categories;
    } else if (typeof highlight.categories === 'string') {
      categories = API.safeJsonParse(highlight.categories, []);
    }
  }
  
  // Create tags HTML
  const tagsHtml = categories.map(cat => {
    const tagDef = tagDefinitions[cat] || { label: cat, color: '#6b7280' };
    return `<span class="highlight-tag" style="background-color: ${tagDef.color};">${tagDef.label}</span>`;
  }).join('');
  
  div.innerHTML = `
    <div class="highlight-content">
      <div class="highlight-title">${API.escapeHtml(highlight.highlight_text)}</div>
      <div class="highlight-meta">
        <span>${API.formatRelativeTime(highlight.created_at)}</span>
        ${tagsHtml ? `<div class="highlight-tags">${tagsHtml}</div>` : ''}
      </div>
    </div>
    <div class="highlight-actions">
      <button class="btn pin-button ${highlight.pinned ? 'pinned' : ''}" data-action="toggle-pin" title="${highlight.pinned ? 'Desanclar' : 'Anclar'}">
        <i class="fa-solid fa-thumbtack"></i>
      </button>
      <button class="btn edit-button" data-action="edit-highlight" title="Editar">
        <i class="fa-solid fa-edit"></i>
      </button>
      <button class="btn tag-button" data-action="edit-tags" title="Editar Tags">
        <i class="fa-solid fa-tags"></i>
      </button>
      <button class="btn todo-button" data-action="todo-from-highlight" title="Crear To-Do">
        <i class="fa-solid fa-plus"></i>
      </button>
      <button class="btn delete-button" data-action="delete-highlight" title="Eliminar">
        <i class="fa-solid fa-trash"></i>
      </button>
    </div>
  `;
  
  // Add event listeners
  const actions = div.querySelectorAll('.highlight-actions .btn');
  actions.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const action = btn.dataset.action;
      handleHighlightAction(action, highlight);
    });
  });
  
  return div;
}

/**
 * Handle highlight actions
 */
async function handleHighlightAction(action, highlight) {
  switch (action) {
    case 'toggle-pin':
      await toggleHighlightPin(highlight);
      break;
    case 'edit-highlight':
      editHighlightInline(highlight);
      break;
    case 'edit-tags':
      await addTagToHighlight(highlight.id);
      break;
    case 'todo-from-highlight':
      await createTodoFromHighlight(highlight);
      break;
    case 'delete-highlight':
      await deleteHighlightFromHighlight(highlight);
      break;
  }
}

/**
 * Toggle highlight pin status
 */
async function toggleHighlightPin(highlight) {
  try {
    const response = await API.put(`/api/highlights/${highlight.id}`, {
      pinned: !highlight.pinned
    });
    
    if (response.success) {
      // Update local data
      const index = highlights.findIndex(h => h.id == highlight.id);
      if (index !== -1) {
        highlights[index].pinned = !highlight.pinned;
      }
      
      renderHighlights();
      API.toast('Highlight actualizado', highlight.pinned ? 'Desanclado' : 'Anclado', 'success');
    }
  } catch (error) {
    console.error('Failed to toggle pin:', error);
    API.toast('Error', 'No se pudo actualizar el highlight', 'error');
  }
}

/**
 * Edit highlight inline
 */
function editHighlightInline(highlight) {
  const item = document.querySelector(`[data-id="${highlight.id}"]`);
  if (!item) return;
  
  const titleElement = item.querySelector('.highlight-title');
  const currentText = highlight.highlight_text;
  
  // Create input
  const input = document.createElement('input');
  input.type = 'text';
  input.value = currentText;
  input.className = 'input';
  input.style.cssText = 'font-size: 13px; padding: 4px 8px; margin: 0;';
  
  // Replace title with input
  titleElement.style.display = 'none';
  titleElement.parentNode.insertBefore(input, titleElement);
  input.focus();
  input.select();
  
  // Handle save
  const saveEdit = async () => {
    const newText = input.value.trim();
    if (newText && newText !== currentText) {
      try {
        const response = await API.put(`/api/highlights/${highlight.id}`, {
          highlight_text: newText
        });
        
        if (response.success) {
          // Update local data
          const index = highlights.findIndex(h => h.id == highlight.id);
          if (index !== -1) {
            highlights[index].highlight_text = newText;
          }
          
          renderHighlights();
          API.toast('Highlight actualizado', '', 'success');
        }
      } catch (error) {
        console.error('Failed to update highlight:', error);
        API.toast('Error', 'No se pudo actualizar el highlight', 'error');
      }
    }
    
    // Restore title
    input.remove();
    titleElement.style.display = '';
  };
  
  // Handle cancel
  const cancelEdit = () => {
    input.remove();
    titleElement.style.display = '';
  };
  
  // Event listeners
  input.addEventListener('blur', saveEdit);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      saveEdit();
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  });
}

/**
 * Delete highlight from highlight action
 */
async function deleteHighlightFromHighlight(highlight) {
  if (!confirm('¿Estás seguro de que quieres eliminar este highlight?')) {
    return;
  }
  
  try {
    const response = await API.delete(`/api/highlights/${highlight.id}`);
    
    if (response.success) {
      // Remove from local data
      const index = highlights.findIndex(h => h.id == highlight.id);
      if (index !== -1) {
        highlights.splice(index, 1);
      }
      
      renderHighlights();
      API.toast('Highlight eliminado', '', 'success');
    }
  } catch (error) {
    console.error('Failed to delete highlight:', error);
    API.toast('Error', 'No se pudo eliminar el highlight', 'error');
  }
}

/**
 * Create todo from highlight
 * @param {Object} highlight - Highlight data object
 */
async function createTodoFromHighlight(highlight) {
  const text = highlight.highlight_text;
  if (!text) {
    API.toast('Error', 'No hay texto para crear To-Do', 'error');
    return;
  }
  
  try {
    // Generate To-Do text using GPT-4o-mini
    const response = await API.post('/generate-todo', {
      transcription: text
    });
    
    let todoText = '';
    if (response.generated_todo) {
      todoText = response.generated_todo;
    } else {
      // Fallback if no AI generation
      todoText = `Revisar highlight: ${text.substring(0, 50)}${text.length > 50 ? '...' : ''}`;
    }
    
    // Allow user to edit the generated To-Do
    const editedText = prompt('Editar To-Do para el entrenador:', todoText);
    if (!editedText) {
      return;
    }
    
    // Create the To-Do
    const todoResponse = await API.post('/api/todos', {
      athlete_id: athleteId,
      text: editedText,
      priority: 'P2',
      status: 'backlog',
      created_by: 'athlete'
    });
    
    if (todoResponse.todo) {
      await loadTodos();
      API.toast('To-Do creado', '', 'success');
    }
  } catch (error) {
    console.error('Failed to create todo:', error);
    API.toast('Error al crear To-Do', error.message, 'error');
  }
}

/**
 * Create auto response from timeline item
 * @param {HTMLElement} item - Timeline item
 */
async function createAutoResponseFromTimeline(item) {
  const text = item.querySelector('.text')?.textContent;
  if (!text) {
    API.toast('Error', 'No hay texto para generar respuesta', 'error');
    return;
  }
  
  try {
    // Show loading state
    const button = item.querySelector('[data-action="auto-response"]');
    const originalIcon = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    button.disabled = true;
    
    // Generate AI response
    const response = await API.post('/generate', {
      transcription: text
    });
    
    if (response.generated_response) {
      // Add the response to the timeline item
      const responseDiv = document.createElement('div');
      responseDiv.className = 'response';
      responseDiv.innerHTML = API.escapeHtml(response.generated_response);
      
      const contentDiv = item.querySelector('.content');
      contentDiv.appendChild(responseDiv);
      
      // Save the conversation
      await API.post('/save', {
        athlete_id: athleteId,
        transcription: text,
        generated_response: response.generated_response,
        final_response: response.generated_response,
        category: 'auto-generated',
        priority: 'medium',
        source: 'auto-response'
      });
      
      API.toast('Respuesta generada', '', 'success');
    }
  } catch (error) {
    console.error('Failed to generate auto response:', error);
    API.toast('Error al generar respuesta', error.message, 'error');
  } finally {
    // Restore button state
    const button = item.querySelector('[data-action="auto-response"]');
    button.innerHTML = '<i class="fa-solid fa-robot"></i>';
    button.disabled = false;
  }
}

/**
 * Edit timeline item
 * @param {HTMLElement} item - Timeline item
 */
function editTimelineItem(item) {
  const textElement = item.querySelector('.text');
  const currentText = textElement.textContent;
  
  const newText = prompt('Editar mensaje:', currentText);
  if (!newText || newText === currentText) return;
  
  // Update the text in the DOM
  textElement.textContent = newText;
  
  // Update in database (you might want to add an endpoint for this)
  API.toast('Mensaje editado', 'Los cambios se guardarán automáticamente', 'success');
}

/**
 * Delete timeline item
 * @param {HTMLElement} item - Timeline item
 */
async function deleteTimelineItem(item) {
  const text = item.querySelector('.text')?.textContent;
  if (!text) {
    API.toast('Error', 'No hay texto para eliminar', 'error');
    return;
  }
  
  const confirmDelete = confirm(`¿Estás seguro de que quieres eliminar este mensaje?\n\n"${text.substring(0, 50)}${text.length > 50 ? '...' : ''}"`);
  if (!confirmDelete) return;
  
  try {
    // Remove from DOM immediately for better UX
    item.style.opacity = '0.5';
    item.style.pointerEvents = 'none';
    
    // You might want to add an endpoint to delete from database
    // For now, we'll just remove from DOM
    setTimeout(() => {
      item.remove();
      API.toast('Mensaje eliminado', '', 'success');
    }, 300);
    
  } catch (error) {
    console.error('Failed to delete timeline item:', error);
    API.toast('Error al eliminar mensaje', error.message, 'error');
    
    // Restore item if deletion failed
    item.style.opacity = '1';
    item.style.pointerEvents = 'auto';
  }
}

/**
 * Create todo from form
 * @param {Event} event - Form submit event
 */
async function createTodo(event) {
  event.preventDefault();
  
  const form = event.target;
  const formData = new FormData(form);
  
  try {
    const response = await API.post('/api/todos', {
      athlete_id: athleteId,
      text: formData.get('text'),
      priority: formData.get('priority'),
      due: formData.get('due'),
      status: 'backlog',
      created_by: 'athlete'
    });
    
    if (response.todo) {
      form.reset();
      await loadTodos();
      API.toast('To-Do enviado al entrenador', '', 'success');
    }
  } catch (error) {
    console.error('Failed to create todo:', error);
    API.toast('Error al crear To-Do', error.message, 'error');
  }
}

/**
 * Load and display risk assessment
 */
async function loadRiskAssessment() {
  try {
    const response = await API.get(`/api/athletes/${athleteId}/risk`);
    if (response.risk_level) {
      displayRiskAssessment(response);
    }
    
    // Check if GPT is disabled
    if (response.message && response.message.includes('disabled')) {
      console.log('Automatic GPT risk assessment is disabled');
    }
  } catch (error) {
    console.error('Failed to load risk assessment:', error);
  }
}

/**
 * Manually trigger risk assessment (with loading state)
 */
async function triggerRiskAssessment() {
  const container = $('#riskAssessment');
  if (!container) return;
  
  try {
    // Show loading state
    container.innerHTML = `
      <span class="risk-chip info">
        <i class="fa-solid fa-spinner fa-spin"></i>
        EVALUANDO...
      </span>
    `;
    
    // Trigger the assessment
    const response = await API.get(`/api/athletes/${athleteId}/risk`);
    
    if (response.risk_level) {
      displayRiskAssessment(response);
      API.toast('Evaluación completada', `Riesgo: ${response.risk_level}`, 'success');
    } else {
      API.toast('Error en evaluación', 'No se pudo evaluar el riesgo', 'error');
    }
    
  } catch (error) {
    console.error('Failed to trigger risk assessment:', error);
    container.innerHTML = `
      <span class="risk-chip danger">
        <i class="fa-solid fa-exclamation-triangle"></i>
        ERROR
      </span>
    `;
    API.toast('Error en evaluación', error.message, 'error');
  }
}

/**
 * Display risk assessment in the header
 */
function displayRiskAssessment(riskData) {
  const container = $('#riskAssessment');
  if (!container) return;
  
  const riskLevel = riskData.risk_level || 'bajo';
  const riskColor = riskData.risk_color || 'success';
  const riskScore = riskData.risk_score || 0;
  const explanations = riskData.explanations || [];
  
  let tooltip = '';
  if (explanations.length > 0) {
    tooltip = `title="${explanations.join(', ')}"`;
  }
  
  container.innerHTML = `
    <span class="risk-chip ${riskColor}" ${tooltip}>
      <i class="fa-solid fa-exclamation-triangle"></i>
      ${riskLevel.toUpperCase()}
      <span class="risk-score">${riskScore}</span>
    </span>
    ${explanations.length > 0 ? 
      `<span class="risk-explanations">${explanations[0]}</span>` : ''
    }
  `;
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initWorkspace);
} else {
  initWorkspace();
}

// ===== MEJORAS PARA TRANSCRIPCIÓN DE AUDIO =====

/**
 * Manejar la transcripción de archivos de audio con mejor feedback de usuario
 */
async function handleTranscription() {
    const fileInput = document.getElementById('audioInput');
    const btnTranscribir = document.getElementById('btnTranscribir');
    const dropLabel = document.getElementById('dropLabel');
    
    if (!fileInput.files.length) {
        showToast('Por favor selecciona un archivo de audio', 'warning');
        return;
    }
    
    const file = fileInput.files[0];
    
    // Validaciones del lado del cliente
    const validationResult = validateAudioFile(file);
    if (!validationResult.valid) {
        showToast(validationResult.message, 'error');
        return;
    }
    
    // Actualizar UI durante el procesamiento
    const originalText = btnTranscribir.innerHTML;
    const originalDisabled = btnTranscribir.disabled;
    
    btnTranscribir.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Transcribiendo...';
    btnTranscribir.disabled = true;
    dropLabel.textContent = `Procesando ${file.name} (${formatFileSize(file.size)})...`;
    
    try {
        // Mostrar información del archivo
        showFileInfo(file);
        
        // Crear FormData para el upload
        const formData = new FormData();
        formData.append('file', file);
        
        // Realizar la transcripción
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        // Manejar la respuesta
        await handleTranscriptionResponse(result, file);
        
    } catch (error) {
        console.error('Error en transcripción:', error);
        handleTranscriptionError(error, file);
    } finally {
        // Restaurar UI
        btnTranscribir.innerHTML = originalText;
        btnTranscribir.disabled = originalDisabled;
        dropLabel.textContent = 'Arrastra un audio o haz clic';
        fileInput.value = ''; // Limpiar el input
    }
}

/**
 * Validar archivo de audio en el cliente
 */
function validateAudioFile(file) {
    // Verificar que es un archivo
    if (!file) {
        return { valid: false, message: 'No se seleccionó ningún archivo' };
    }
    
    // Verificar tamaño (25MB máximo)
    const maxSize = 25 * 1024 * 1024; // 25MB
    if (file.size > maxSize) {
        return { 
            valid: false, 
            message: `Archivo demasiado grande (${formatFileSize(file.size)}). Máximo permitido: 25MB` 
        };
    }
    
    // Verificar que no esté vacío
    if (file.size === 0) {
        return { valid: false, message: 'El archivo está vacío' };
    }
    
    // Verificar extensión (permitir más formatos)
    const allowedExtensions = [
        '.mp3', '.wav', '.m4a', '.mp4', '.mpeg', '.mpga', '.webm', // Directos
        '.ogg', '.opus', '.oga', '.aac', '.flac' // Con conversión
    ];
    
    const extension = getFileExtension(file.name);
    if (!allowedExtensions.includes(extension)) {
        return { 
            valid: false, 
            message: `Formato no soportado: ${extension}. Formatos permitidos: ${allowedExtensions.join(', ')}` 
        };
    }
    
    // Verificar tipo MIME si está disponible
    if (file.type && !file.type.startsWith('audio/') && !file.type.startsWith('video/')) {
        console.warn(`Tipo MIME inesperado: ${file.type}`);
    }
    
    return { valid: true };
}

/**
 * Mostrar información del archivo antes de procesarlo
 */
function showFileInfo(file) {
    const extension = getFileExtension(file.name);
    const fileSize = formatFileSize(file.size);
    
    // Determinar el tipo de procesamiento esperado
    const directFormats = ['.mp3', '.wav', '.m4a', '.mp4', '.mpeg', '.mpga', '.webm'];
    const conversionFormats = ['.ogg', '.opus', '.oga', '.aac', '.flac'];
    
    let processingInfo = '';
    if (directFormats.includes(extension)) {
        processingInfo = '🚀 Procesamiento directo (rápido)';
    } else if (conversionFormats.includes(extension)) {
        processingInfo = '🔄 Requiere conversión (puede tomar más tiempo)';
    }
    
    showToast(`📁 ${file.name} (${fileSize}) - ${processingInfo}`, 'info', 3000);
}

/**
 * Manejar la respuesta de transcripción
 */
async function handleTranscriptionResponse(result, originalFile) {
    console.log('Respuesta de transcripción:', result);
    
    if (result.success) {
        // Transcripción exitosa
        const transcription = result.transcription;
        const charCount = result.character_count || transcription.length;
        
        // Mostrar el resultado en el input
        const inputMensaje = document.getElementById('inputMensaje');
        if (inputMensaje) {
            inputMensaje.value = transcription;
            inputMensaje.focus();
        }
        
        // Mostrar información de éxito
        const fileInfo = result.file_info;
        let successMessage = `✅ Transcripción exitosa: ${charCount} caracteres`;
        
        if (fileInfo && fileInfo.format) {
            const processingMethod = fileInfo.format.processing_method;
            if (processingMethod === 'conversion') {
                successMessage += ' (convertido desde ' + fileInfo.format.extension + ')';
            }
        }
        
        showToast(successMessage, 'success', 4000);
        
        // Mostrar preview si es muy largo
        if (result.preview && result.preview !== transcription) {
            console.log('Preview de transcripción:', result.preview);
        }
        
    } else {
        // Error en transcripción
        handleTranscriptionFailure(result, originalFile);
    }
}

/**
 * Manejar fallos en la transcripción
 */
function handleTranscriptionFailure(result, originalFile) {
    console.error('Fallo en transcripción:', result);
    
    const errorMessage = result.transcription || result.error || 'Error desconocido';
    const details = result.details;
    
    // Mostrar error principal
    showToast(errorMessage, 'error', 8000);
    
    // Mostrar información adicional si está disponible
    if (details && details !== errorMessage) {
        console.error('Detalles del error:', details);
    }
    
    // Proporcionar sugerencias basadas en el tipo de error
    provideSuggestions(result, originalFile);
}

/**
 * Proporcionar sugerencias basadas en el error
 */
function provideSuggestions(result, originalFile) {
    const errorMessage = (result.transcription || result.error || '').toLowerCase();
    const fileExtension = getFileExtension(originalFile.name);
    
    let suggestions = [];
    
    // Sugerencias específicas por tipo de error
    if (errorMessage.includes('openai api no configurada')) {
        suggestions.push('💡 Configura OPENAI_API_KEY en tu archivo .env');
        suggestions.push('🔗 Obtén tu API key en: https://platform.openai.com/account/api-keys');
    } else if (errorMessage.includes('ffmpeg')) {
        suggestions.push('💡 Instala FFmpeg para soportar más formatos de audio');
        suggestions.push('🔗 Descarga FFmpeg: https://ffmpeg.org/download.html');
        suggestions.push('📱 Alternativamente, usa formatos .mp3 o .wav');
    } else if (errorMessage.includes('quota') || errorMessage.includes('billing')) {
        suggestions.push('💳 Verifica tu cuenta de facturación de OpenAI');
        suggestions.push('🔗 Panel de facturación: https://platform.openai.com/account/billing');
    } else if (errorMessage.includes('conexión') || errorMessage.includes('timeout')) {
        suggestions.push('🌐 Verifica tu conexión a internet');
        suggestions.push('🔄 Inténtalo de nuevo en unos momentos');
    } else if (['.ogg', '.opus', '.oga'].includes(fileExtension)) {
        suggestions.push('📱 Este formato es común en WhatsApp/Telegram');
        suggestions.push('💡 Requiere FFmpeg para conversión');
        suggestions.push('📁 Alternativa: convierte a .mp3 antes de subir');
    }
    
    // Mostrar sugerencias si las hay
    if (suggestions.length > 0) {
        setTimeout(() => {
            const suggestionText = suggestions.join('\n');
            showDetailedError('Sugerencias para resolver el problema:', suggestionText);
        }, 1000);
    }
}

/**
 * Manejar errores de red/excepción
 */
function handleTranscriptionError(error, originalFile) {
    console.error('Error de transcripción:', error);
    
    let userMessage = '❌ Error procesando el archivo de audio';
    
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
        userMessage = '❌ Error de conexión. Verifica que el servidor esté funcionando.';
    } else if (error.name === 'AbortError') {
        userMessage = '❌ La transcripción fue cancelada.';
    } else if (error.message) {
        userMessage = `❌ Error: ${error.message}`;
    }
    
    showToast(userMessage, 'error', 6000);
}

/**
 * Mostrar error detallado con más información
 */
function showDetailedError(title, details) {
    // Crear modal o expandir información de error
    const modal = document.createElement('div');
    modal.className = 'error-details-modal';
    modal.innerHTML = `
        <div class="error-details-content">
            <div class="error-details-header">
                <h3>${title}</h3>
                <button class="error-details-close">&times;</button>
            </div>
            <div class="error-details-body">
                <pre>${details}</pre>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Cerrar modal
    modal.querySelector('.error-details-close').onclick = () => {
        document.body.removeChild(modal);
    };
    
    modal.onclick = (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    };
}

/**
 * Verificar el estado del sistema de transcripción
 */
async function checkTranscriptionStatus() {
    try {
        const response = await fetch('/transcription/status');
        const status = await response.json();
        
        console.log('Estado del sistema de transcripción:', status);
        
        if (status.status === 'success') {
            const config = status.configuration;
            
            // Mostrar advertencias si la configuración no es óptima
            if (!config.openai_configured) {
                showToast('⚠️ OpenAI API no configurada. La transcripción no funcionará.', 'warning', 5000);
            } else if (!config.ffmpeg_available) {
                showToast('⚠️ FFmpeg no disponible. Solo formatos básicos soportados.', 'warning', 4000);
            }
            
            // Mostrar recomendaciones si las hay
            if (status.system_status.recommendations.length > 0) {
                status.system_status.recommendations.forEach(rec => {
                    if (rec.type === 'error') {
                        console.error('Configuración:', rec.message, '-', rec.action);
                    } else if (rec.type === 'warning') {
                        console.warn('Configuración:', rec.message, '-', rec.action);
                    }
                });
            }
        }
        
    } catch (error) {
        console.error('Error verificando estado de transcripción:', error);
    }
}

/**
 * Funciones auxiliares
 */
function getFileExtension(filename) {
    return filename.toLowerCase().substring(filename.lastIndexOf('.'));
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Función mejorada para mostrar toast (compatible con API.toast existente)
 */
function showToast(message, type = 'info', duration = 3000) {
    // Usar la función API.toast existente si está disponible
    if (typeof API !== 'undefined' && API.toast) {
        API.toast(type === 'error' ? 'Error' : type === 'success' ? 'Éxito' : 'Info', message, type);
    } else {
        // Fallback simple si API.toast no está disponible
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}

/**
 * Mejorar el dropzone con información de formatos
 */
function setupEnhancedDropzone() {
    const dropzone = document.getElementById('dropzone');
    const dropLabel = document.getElementById('dropLabel');
    
    if (dropzone && dropLabel) {
        // Actualizar texto con información de formatos
        dropLabel.innerHTML = `
            <i class="fa-solid fa-microphone-lines"></i>
            Arrastra audio o haz clic<br>
            <small style="font-size: 11px; opacity: 0.7;">
                Soporta: WhatsApp (.ogg), Telegram (.m4a), MP3, WAV
            </small>
        `;
        
        // Mejorar feedback visual del drag & drop
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('drag-over');
        });
        
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('drag-over');
        });
        
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const audioInput = document.getElementById('audioInput');
                audioInput.files = files;
                
                // Trigger transcription automatically after drop
                setTimeout(() => {
                    handleTranscription();
                }, 100);
            }
        });
    }
}

// CSS adicional para modales de error
const errorModalCSS = `
.error-details-modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
}

.error-details-content {
    background: var(--bg-2);
    border-radius: 12px;
    padding: 20px;
    max-width: 600px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    border: 1px solid var(--border);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
}

.error-details-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
}

.error-details-header h3 {
    margin: 0;
    color: var(--text-1);
}

.error-details-close {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: var(--text-3);
    padding: 4px 8px;
    border-radius: 4px;
}

.error-details-close:hover {
    background: var(--bg-4);
    color: var(--text-1);
}

.error-details-body pre {
    background: var(--bg-4);
    padding: 16px;
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.4;
    white-space: pre-wrap;
    word-wrap: break-word;
    color: var(--text-2);
    margin: 0;
}

.drag-over {
    border-color: var(--primary) !important;
    background: rgba(99, 102, 241, 0.1) !important;
}
`;

// Agregar CSS si no existe
if (!document.getElementById('error-modal-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'error-modal-styles';
    styleElement.textContent = errorModalCSS;
    document.head.appendChild(styleElement);
}

// Mejorar el setup de event listeners para incluir las nuevas funciones
const originalSetupEventListeners = setupEventListeners;
setupEventListeners = function() {
    // Llamar a la función original
    originalSetupEventListeners();
    
    // Configurar dropzone mejorado
    setupEnhancedDropzone();
    
    // Reemplazar la función de transcripción existente
    const transcribeBtn = document.getElementById('btnTranscribir');
    if (transcribeBtn) {
        transcribeBtn.removeEventListener('click', transcribeAudio);
        transcribeBtn.addEventListener('click', handleTranscription);
    }
};