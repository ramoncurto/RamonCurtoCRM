// ===== COACH TODOS BOARD =====

/**
 * Coach todos board functionality
 * Handles Kanban board, drag & drop, filtering, and todo management
 */

// State
let todos = []; // {id, athlete_id, athlete_name, text, priority, due, status, created_by, source_record_id}
let athletes = []; // {id, name}
let filterP = '';
let filterAthlete = '';
let search = '';
let view = 'kanban';
let lastCreatedTodo = null; // For undo functionality
let selectedDate = 'none'; // For quick date chips
let selectedTodos = new Set(); // For bulk selection
let isShiftPressed = false; // For multi-selection

// WIP Limits
const WIP_LIMITS = {
  backlog: Infinity,
  doing: 5,
  done: Infinity
};

// SLA thresholds (days)
const SLA_THRESHOLDS = {
  P1: 1,
  P2: 3,
  P3: 7
};

// Use API functions - $ and $$ are already defined in api.js

/**
 * Initialize coach todos board
 */
function initCoachTodos() {
  loadTodos();
  loadAthletes();
  setupEventListeners();
  setupKeyboardShortcuts();
  setupMicroFlow();
  loadSavedViews();
  setupBulkActions();
}

/**
 * Setup micro-flow input functionality
 */
function setupMicroFlow() {
  const microInput = $('#microInput');
  const sendBtn = $('#btnSendTodo');
  const quickChips = $$('.quick-chip');
  
  if (microInput) {
    microInput.addEventListener('input', (e) => {
      const text = e.target.value;
      sendBtn.disabled = !text.trim();
      
      // Auto-detect priority from text
      const priorityMatch = text.match(/@(P[123])/i);
      if (priorityMatch) {
        // Update priority chips if needed
        const priority = priorityMatch[1].toUpperCase();
        updatePriorityChips(priority);
      }
    });
    
    microInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !sendBtn.disabled) {
        createTodoFromMicroFlow();
      }
    });
  }
  
  if (sendBtn) {
    sendBtn.addEventListener('click', createTodoFromMicroFlow);
  }
  
  // Quick date chips
  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      quickChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      selectedDate = chip.dataset.date;
    });
  });
}

/**
 * Create todo from micro-flow input
 */
async function createTodoFromMicroFlow() {
  const microInput = $('#microInput');
  const text = microInput.value.trim();
  
  if (!text) return;
  
  // Parse the input text
  const parsed = parseMicroFlowInput(text);
  
  try {
    const sendBtn = $('#btnSendTodo');
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Enviando...';
    
    const response = await API.post('/api/todos', {
      text: parsed.text,
      priority: parsed.priority,
      due: parsed.dueDate,
      status: 'backlog',
      created_by: 'coach'
    });
    
    if (response.success) {
      // Store for undo
      lastCreatedTodo = {
        id: response.todo_id,
        text: parsed.text,
        priority: parsed.priority,
        due: parsed.dueDate
      };
      
      // Show success feedback
      showSuccessFeedback(parsed.priority, parsed.dueDate);
      
      // Clear input
      microInput.value = '';
      sendBtn.disabled = true;
      
      // Reload todos
      await loadTodos();
      
    } else {
      throw new Error(response.error || 'Error al crear To-Do');
    }
    
  } catch (error) {
    console.error('Failed to create todo:', error);
    API.toast('Error al crear To-Do', error.message, 'error');
  } finally {
    const sendBtn = $('#btnSendTodo');
    sendBtn.disabled = false;
    sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Enviar';
  }
}

/**
 * Parse micro-flow input text
 * @param {string} text - Input text
 * @returns {Object} Parsed data
 */
function parseMicroFlowInput(text) {
  let priority = 'P2'; // Default
  let dueDate = null;
  let cleanText = text;
  
  // Extract priority (@P1, @P2, @P3)
  const priorityMatch = text.match(/@(P[123])/i);
  if (priorityMatch) {
    priority = priorityMatch[1].toUpperCase();
    cleanText = cleanText.replace(/@P[123]/i, '').trim();
  }
  
  // Extract date keywords
  const dateKeywords = {
    'hoy': 'today',
    'mañana': 'tomorrow',
    'semana': 'week',
    'próxima semana': 'next-week'
  };
  
  for (const [keyword, value] of Object.entries(dateKeywords)) {
    if (cleanText.toLowerCase().includes(keyword)) {
      dueDate = getDateFromKeyword(value);
      cleanText = cleanText.replace(new RegExp(keyword, 'gi'), '').trim();
      break;
    }
  }
  
  // Use selected date chip if no date in text
  if (!dueDate && selectedDate !== 'none') {
    dueDate = getDateFromKeyword(selectedDate);
  }
  
  return {
    text: cleanText,
    priority,
    dueDate
  };
}

/**
 * Get date from keyword
 * @param {string} keyword - Date keyword
 * @returns {string} ISO date string
 */
function getDateFromKeyword(keyword) {
  const today = new Date();
  
  switch (keyword) {
    case 'today':
      return today.toISOString().split('T')[0];
    case 'tomorrow':
      const tomorrow = new Date(today);
      tomorrow.setDate(tomorrow.getDate() + 1);
      return tomorrow.toISOString().split('T')[0];
    case 'week':
      const week = new Date(today);
      week.setDate(week.getDate() + 7);
      return week.toISOString().split('T')[0];
    case 'next-week':
      const nextWeek = new Date(today);
      nextWeek.setDate(nextWeek.getDate() + 7);
      return nextWeek.toISOString().split('T')[0];
    default:
      return null;
  }
}

/**
 * Show success feedback with undo option
 * @param {string} priority - Todo priority
 * @param {string} dueDate - Due date
 */
function showSuccessFeedback(priority, dueDate) {
  const feedback = $('#successFeedback');
  const feedbackText = $('#feedbackText');
  const undoBtn = $('#undoBtn');
  
  let status = 'Backlog';
  if (priority === 'P1') status = 'Backlog (P1)';
  
  let dateText = '';
  if (dueDate) {
    const date = new Date(dueDate);
    const today = new Date();
    const diffDays = Math.floor((date - today) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) dateText = ' · hoy';
    else if (diffDays === 1) dateText = ' · mañana';
    else dateText = ` · ${diffDays} días`;
  }
  
  feedbackText.textContent = `Creado en ${status}${dateText} · abrir tablero`;
  
  feedback.style.display = 'flex';
  
  // Auto-hide after 5 seconds
  setTimeout(() => {
    feedback.style.display = 'none';
  }, 5000);
  
  // Undo functionality
  undoBtn.onclick = async () => {
    if (lastCreatedTodo) {
      try {
        await API.delete(`/api/todos/${lastCreatedTodo.id}`);
        await loadTodos();
        API.toast('To-Do deshecho', '', 'success');
        feedback.style.display = 'none';
        lastCreatedTodo = null;
      } catch (error) {
        console.error('Failed to undo todo:', error);
        API.toast('Error al deshacer', error.message, 'error');
      }
    }
  };
}

/**
 * Load todos from API
 */
async function loadTodos() {
  try {
    const params = {};
    if (filterAthlete) params.athlete_id = filterAthlete;
    if (filterP) params.priority = filterP;
    if (search) params.q = search;
    
    const response = await API.get('/api/todos', params);
    todos = response.todos || [];
    renderBoard();
    updateWIPLimits();
    updateSLAs();
    
    // Setup drag and drop after rendering
    if (view === 'kanban') {
      setTimeout(() => {
        setupDragAndDrop();
      }, 100);
    }
  } catch (error) {
    console.error('Failed to load todos:', error);
    API.toast('Error al cargar To-Dos', error.message, 'error');
    todos = [];
    renderBoard();
  }
}

/**
 * Load athletes for filter
 */
async function loadAthletes() {
  try {
    const response = await API.get('/api/athletes');
    athletes = response.athletes || [];
    updateAthleteFilter();
  } catch (error) {
    console.error('Failed to load athletes:', error);
    athletes = [];
  }
}

/**
 * Update athlete filter dropdown
 */
function updateAthleteFilter() {
  const select = $('#filterAthlete');
  if (!select) return;
  
  // Keep current selection
  const currentValue = select.value;
  
  // Clear options except first
  select.innerHTML = '<option value="">Todos los atletas</option>';
  
  // Add athlete options
  athletes.forEach(athlete => {
    const option = document.createElement('option');
    option.value = athlete.id;
    option.textContent = athlete.name;
    select.appendChild(option);
  });
  
  // Restore selection
  select.value = currentValue;
}

/**
 * Update WIP limits display
 */
function updateWIPLimits() {
  const statuses = ['backlog', 'doing', 'done'];
  
  statuses.forEach(status => {
    const count = todos.filter(todo => todo.status === status).length;
    const limit = WIP_LIMITS[status];
    const wipElement = $(`#wip-${status}`);
    
    if (wipElement) {
      const limitText = limit === Infinity ? '∞' : limit;
      wipElement.textContent = `${count}/${limitText}`;
      
      // Add warning/danger classes
      wipElement.classList.remove('warning', 'danger');
      if (limit !== Infinity) {
        if (count >= limit * 0.8) wipElement.classList.add('warning');
        if (count >= limit) wipElement.classList.add('danger');
      }
    }
  });
}

/**
 * Update SLA indicators
 */
function updateSLAs() {
  const today = new Date();
  
  todos.forEach(todo => {
    if (todo.due_date && todo.status !== 'done') {
      const dueDate = new Date(todo.due_date);
      const diffDays = Math.floor((dueDate - today) / (1000 * 60 * 60 * 24));
      const threshold = SLA_THRESHOLDS[todo.priority] || 3;
      
      // Add SLA indicator to card
      const card = document.querySelector(`[data-id="${todo.id}"]`);
      if (card) {
        let slaClass = 'sla-green';
        if (diffDays < 0) slaClass = 'sla-red';
        else if (diffDays <= threshold) slaClass = 'sla-amber';
        
        // Remove existing SLA indicators
        card.querySelectorAll('.sla-indicator').forEach(el => el.remove());
        
        // Add new SLA indicator
        const indicator = document.createElement('div');
        indicator.className = `sla-indicator ${slaClass}`;
        indicator.title = `Vence en ${diffDays} días`;
        card.appendChild(indicator);
      }
    }
  });
}

/**
 * Render the Kanban board
 */
function renderBoard() {
  if (view === 'kanban') {
    renderKanban();
  } else {
    renderList();
  }
  updateCounts();
  updateBulkActions();
}

/**
 * Render Kanban view
 */
function renderKanban() {
  const statuses = ['backlog', 'doing', 'done'];
  
  statuses.forEach(status => {
    const lane = $(`#lane-${status}`);
    if (!lane) return;
    
    lane.innerHTML = '';
    
    const statusTodos = todos.filter(todo => todo.status === status);
    statusTodos.forEach(todo => {
      lane.appendChild(createTodoCard(todo));
    });
  });
  
  // Setup drag and drop after rendering cards
  setupCardDragAndDrop();
}

/**
 * Render list view
 */
function renderList() {
  const container = $('#board');
  if (!container) return;
  
  container.innerHTML = `
    <div class="list-view">
      <div class="list-header">
        <div class="col">✓</div>
        <div class="col">Tarea</div>
        <div class="col">Atleta</div>
        <div class="col">Prioridad</div>
        <div class="col">Estado</div>
        <div class="col">Fecha</div>
        <div class="col">SLA</div>
        <div class="col">Acciones</div>
      </div>
      <div class="list-body">
        ${todos.map(todo => createTodoRow(todo)).join('')}
      </div>
    </div>
  `;
}

/**
 * Create todo card for Kanban
 * @param {Object} todo - Todo data
 * @returns {HTMLElement} Todo card element
 */
function createTodoCard(todo) {
  const div = document.createElement('div');
  div.className = 'card';
  div.dataset.id = todo.id;
  
  // Add selection class if selected
  if (selectedTodos.has(todo.id.toString())) {
    div.classList.add('selected');
  }
  
  // Calculate SLA
  const slaInfo = calculateSLA(todo);
  
  // Determine priority class
  const priorityClass = `prio ${todo.priority}`;
  
  // Determine due date class
  let dueDateClass = '';
  if (slaInfo) {
    if (slaInfo.type === 'overdue') {
      dueDateClass = 'overdue';
    } else if (slaInfo.type === 'due-soon') {
      dueDateClass = 'due-soon';
    }
  }
  
  // Get context preview
  const contextPreview = getContextPreview(todo);
  
  div.innerHTML = `
    <div class="drag-handle" title="Arrastrar">≡</div>
    <div class="title">${API.escapeHtml(todo.text)}</div>
    <div class="meta">
      <span class="badge">${todo.athlete_name || 'Sin atleta'}</span>
      <span class="${priorityClass}">${todo.priority}</span>
      ${todo.due_date ? `<span class="tag ${dueDateClass}">${API.formatDate(todo.due_date)}</span>` : ''}
    </div>
    ${slaInfo ? `<div class="meta"><span class="badge ${slaInfo.class}">${slaInfo.text}</span></div>` : ''}
    <div class="actions">
      <button class="btn-icon" data-action="edit" title="Editar" aria-label="Editar to-do">
        <i class="fa-solid fa-edit"></i>
      </button>
      <button class="btn-icon" data-action="workspace" title="Workspace" aria-label="Abrir workspace">
        <i class="fa-solid fa-up-right-from-square"></i>
      </button>
      <button class="btn-icon danger" data-action="delete" title="Eliminar" aria-label="Eliminar to-do">
        <i class="fa-solid fa-trash"></i>
      </button>
    </div>
    ${todo.status === 'backlog' ? `
      <button class="btn-icon primary" data-action="quick-triage" title="Enviar a Doing" aria-label="Enviar a Doing">
        <i class="fa-solid fa-play"></i>
      </button>
    ` : ''}
    ${contextPreview ? `
      <div class="context-preview">
        <div class="context-title">${contextPreview.title}</div>
        <div class="context-text">${contextPreview.text}</div>
      </div>
    ` : ''}
  `;
  
  // Add event listeners
  div.addEventListener('click', handleCardAction);
  div.addEventListener('click', handleCardSelection);
  
  return div;
}

/**
 * Create todo row for list view
 * @param {Object} todo - Todo data
 * @returns {string} HTML string
 */
function createTodoRow(todo) {
  const slaInfo = calculateSLA(todo);
  const isSelected = selectedTodos.has(todo.id.toString());
  
  return `
    <div class="list-row ${isSelected ? 'selected' : ''}" data-id="${todo.id}">
      <div class="col">
        <input type="checkbox" ${isSelected ? 'checked' : ''} data-todo-id="${todo.id}" />
      </div>
      <div class="col">${API.escapeHtml(todo.text)}</div>
      <div class="col">${API.escapeHtml(todo.athlete_name || 'Sin atleta')}</div>
      <div class="col"><span class="prio ${todo.priority}">${todo.priority}</span></div>
      <div class="col"><span class="tag">${todo.status}</span></div>
      <div class="col">${todo.due_date ? API.formatDate(todo.due_date) : '—'}</div>
      <div class="col">${slaInfo ? slaInfo.text : '—'}</div>
      <div class="col">
        <div class="cell-actions">
          <button class="btn" data-action="edit" title="Editar">
            <i class="fa-solid fa-edit"></i>
          </button>
          <button class="btn" data-action="workspace" title="Workspace">
            <i class="fa-solid fa-up-right-from-square"></i>
          </button>
          <button class="btn danger" data-action="delete" title="Eliminar">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
    </div>
  `;
}

/**
 * Get context preview for a todo
 * @param {Object} todo - Todo data
 * @returns {Object|null} Context preview
 */
function getContextPreview(todo) {
  if (!todo.source_record_id) return null;
  
  // This would typically fetch from the source record
  // For now, return a mock preview
  return {
    title: 'Origen: Conversación',
    text: 'Fragmento del mensaje o highlight que originó este To-Do...'
  };
}

/**
 * Calculate SLA for a todo
 * @param {Object} todo - Todo data
 * @returns {Object|null} SLA info
 */
function calculateSLA(todo) {
  if (!todo.due_date || todo.status === 'done') return null;
  
  const today = new Date();
  const dueDate = new Date(todo.due_date);
  const diffDays = Math.floor((dueDate - today) / (1000 * 60 * 60 * 24));
  
  const threshold = SLA_THRESHOLDS[todo.priority] || 3;
  
  // Calculate days overdue or remaining
  if (diffDays < 0) {
    // Overdue
    const overdueDays = Math.abs(diffDays);
    return {
      text: `Vencido hace ${overdueDays} día${overdueDays > 1 ? 's' : ''}`,
      class: 'overdue',
      type: 'overdue',
      days: overdueDays
    };
  } else if (diffDays <= 2) {
    // Due soon (within 48h)
    return {
      text: `Vence en ${diffDays} día${diffDays > 1 ? 's' : ''}`,
      class: 'due-soon',
      type: 'due-soon',
      days: diffDays
    };
  } else if (diffDays <= threshold) {
    // Within SLA threshold
    return {
      text: `Vence en ${diffDays} días`,
      class: '',
      type: 'within-sla',
      days: diffDays
    };
  } else {
    // Well within SLA
    return {
      text: `Vence en ${diffDays} días`,
      class: '',
      type: 'well-within-sla',
      days: diffDays
    };
  }
}

/**
 * Handle card action clicks
 * @param {Event} event - Click event
 */
async function handleCardAction(event) {
  const action = event.target.closest('[data-action]')?.dataset?.action;
  if (!action) return;
  
  const card = event.target.closest('.card, .list-row');
  const todoId = card?.dataset?.id;
  
  switch (action) {
    case 'edit':
      editTodo(todoId);
      break;
    case 'workspace':
      openWorkspace(todoId);
      break;
    case 'delete':
      deleteTodo(todoId);
      break;
    case 'quick-triage':
      quickTriage(todoId);
      break;
  }
}

/**
 * Handle card selection
 * @param {Event} event - Click event
 */
function handleCardSelection(event) {
  // Don't handle selection if clicking on action buttons
  if (event.target.closest('[data-action]')) return;
  
  const card = event.target.closest('.card, .list-row');
  if (!card) return;
  
  const todoId = card.dataset.id;
  
  if (isShiftPressed) {
    // Multi-selection mode
    if (selectedTodos.has(todoId)) {
      selectedTodos.delete(todoId);
      card.classList.remove('selected');
    } else {
      selectedTodos.add(todoId);
      card.classList.add('selected');
    }
  } else {
    // Single selection mode
    selectedTodos.clear();
    $$('.card.selected, .list-row.selected').forEach(el => el.classList.remove('selected'));
    
    selectedTodos.add(todoId);
    card.classList.add('selected');
  }
  
  updateBulkActions();
}

/**
 * Update bulk actions visibility and count
 */
function updateBulkActions() {
  const bulkActions = $('#bulkActions');
  const bulkCount = $('#bulkCount');
  
  if (selectedTodos.size > 0) {
    bulkActions.classList.remove('hidden');
    bulkCount.textContent = selectedTodos.size;
  } else {
    bulkActions.classList.add('hidden');
  }
}

/**
 * Setup bulk actions
 */
function setupBulkActions() {
  const btnBulkEdit = $('#btnBulkEdit');
  const btnBulkMove = $('#btnBulkMove');
  const btnBulkDelete = $('#btnBulkDelete');
  const bulkModal = $('#bulkModal');
  const bulkModalClose = $('#bulkModalClose');
  const bulkCancel = $('#bulkCancel');
  const bulkForm = $('#bulkForm');
  
  if (btnBulkEdit) {
    btnBulkEdit.addEventListener('click', () => {
      bulkModal.classList.add('show');
    });
  }
  
  if (btnBulkMove) {
    btnBulkMove.addEventListener('click', () => {
      // Quick move to next status
      bulkMoveTodos();
    });
  }
  
  if (btnBulkDelete) {
    btnBulkDelete.addEventListener('click', () => {
      if (confirm(`¿Eliminar ${selectedTodos.size} To-Do(s) seleccionado(s)?`)) {
        bulkDeleteTodos();
      }
    });
  }
  
  if (bulkModalClose) {
    bulkModalClose.addEventListener('click', () => {
      bulkModal.classList.remove('show');
    });
  }
  
  if (bulkCancel) {
    bulkCancel.addEventListener('click', () => {
      bulkModal.classList.remove('show');
    });
  }
  
  if (bulkForm) {
    bulkForm.addEventListener('submit', (e) => {
      e.preventDefault();
      bulkEditTodos();
    });
  }
  
  // Close modal on outside click
  bulkModal.addEventListener('click', (e) => {
    if (e.target === bulkModal) {
      bulkModal.classList.remove('show');
    }
  });
}

/**
 * Bulk edit todos
 */
async function bulkEditTodos() {
  const priority = $('#bulkPriority').value;
  const status = $('#bulkStatus').value;
  const dueDate = $('#bulkDueDate').value;
  
  const updates = {};
  if (priority) updates.priority = priority;
  if (status) updates.status = status;
  if (dueDate) updates.due = dueDate;
  
  if (Object.keys(updates).length === 0) {
    API.toast('No hay cambios para aplicar', '', 'warning');
    return;
  }
  
  try {
    const promises = Array.from(selectedTodos).map(todoId =>
      API.put(`/api/todos/${todoId}`, updates)
    );
    
    await Promise.all(promises);
    
    selectedTodos.clear();
    await loadTodos();
    $('#bulkModal').classList.remove('show');
    API.toast('To-Dos actualizados', '', 'success');
    
  } catch (error) {
    console.error('Failed to bulk edit todos:', error);
    API.toast('Error al actualizar To-Dos', error.message, 'error');
  }
}

/**
 * Bulk move todos to next status
 */
async function bulkMoveTodos() {
  try {
    const promises = Array.from(selectedTodos).map(todoId => {
      const todo = todos.find(t => String(t.id) === String(todoId));
      if (!todo) return Promise.resolve();
      
      let newStatus = todo.status;
      if (todo.status === 'backlog') newStatus = 'doing';
      else if (todo.status === 'doing') newStatus = 'done';
      
      return API.put(`/api/todos/${todoId}`, { status: newStatus });
    });
    
    await Promise.all(promises);
    
    selectedTodos.clear();
    await loadTodos();
    API.toast('To-Dos movidos', '', 'success');
    
  } catch (error) {
    console.error('Failed to bulk move todos:', error);
    API.toast('Error al mover To-Dos', error.message, 'error');
  }
}

/**
 * Bulk delete todos
 */
async function bulkDeleteTodos() {
  try {
    const promises = Array.from(selectedTodos).map(todoId =>
      API.delete(`/api/todos/${todoId}`)
    );
    
    await Promise.all(promises);
    
    selectedTodos.clear();
    await loadTodos();
    API.toast('To-Dos eliminados', '', 'success');
    
  } catch (error) {
    console.error('Failed to bulk delete todos:', error);
    API.toast('Error al eliminar To-Dos', error.message, 'error');
  }
}

/**
 * Quick triage: move to doing + set date to today
 * @param {string} todoId - Todo ID
 */
async function quickTriage(todoId) {
  try {
    const today = new Date().toISOString().split('T')[0];
    
    const response = await API.put(`/api/todos/${todoId}`, {
      status: 'doing',
      due: today
    });
    
    if (response.success) {
      await loadTodos();
      API.toast('To-Do enviado a Doing', 'Fecha establecida a hoy', 'success');
    }
  } catch (error) {
    console.error('Failed to quick triage todo:', error);
    API.toast('Error en quick triage', error.message, 'error');
  }
}

/**
 * Edit todo
 * @param {string} todoId - Todo ID
 */
function editTodo(todoId) {
  const todo = todos.find(t => String(t.id) === String(todoId));
  if (!todo) return;
  
  const newText = prompt('Editar To-Do:', todo.text);
  if (newText && newText !== todo.text) {
    updateTodo(todoId, { text: newText });
  }
}

/**
 * Update todo
 * @param {string} todoId - Todo ID
 * @param {Object} data - Update data
 */
async function updateTodo(todoId, data) {
  try {
    const response = await API.put(`/api/todos/${todoId}`, data);
    if (response.success) {
      await loadTodos();
      API.toast('To-Do actualizado', '', 'success');
    }
  } catch (error) {
    console.error('Failed to update todo:', error);
    API.toast('Error al actualizar To-Do', error.message, 'error');
  }
}

/**
 * Open athlete workspace
 * @param {string} todoId - Todo ID
 */
function openWorkspace(todoId) {
  const todo = todos.find(t => String(t.id) === String(todoId));
  if (!todo || !todo.athlete_id) {
    API.toast('Error', 'No se puede abrir el workspace', 'error');
    return;
  }
  
  window.open(`/athletes/${todo.athlete_id}/workspace`, '_blank');
}

/**
 * Delete todo with undo functionality
 * @param {number} todoId - Todo ID to delete
 */
async function deleteTodo(todoId) {
  try {
    // Store the todo for potential undo
    const todo = todos.find(t => t.id === todoId);
    if (!todo) return;
    
    // Show loading state
    const deleteBtn = document.querySelector(`[data-id="${todoId}"] .btn[data-action="delete"]`);
    if (deleteBtn) {
      const originalContent = deleteBtn.innerHTML;
      deleteBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
      deleteBtn.disabled = true;
      
      // Delete the todo
      await API.delete(`/api/todos/${todoId}`);
      
      // Remove from local state
      todos = todos.filter(t => t.id !== todoId);
      
      // Show undo toast
      API.showToastWithUndo(
        'To-Do eliminado',
        'Deshacer',
        async () => {
          try {
            // Restore the todo
            const restoredTodo = await API.post('/api/todos', {
              athlete_id: todo.athlete_id,
              text: todo.text,
              priority: todo.priority,
              due_date: todo.due_date,
              status: todo.status,
              source_record_id: todo.source_record_id
            });
            
            todos.push(restoredTodo);
            renderBoard();
            updateCounts();
            API.toast('To-Do restaurado', '', 'success');
          } catch (error) {
            console.error('Failed to restore todo:', error);
            API.toast('Error al restaurar', error.message, 'error');
          }
        },
        'success',
        5000
      );
      
      // Re-render
      renderBoard();
      updateCounts();
      
      // Restore button state
      deleteBtn.innerHTML = originalContent;
      deleteBtn.disabled = false;
      
    } else {
      // Fallback if button not found
      await API.delete(`/api/todos/${todoId}`);
      todos = todos.filter(t => t.id !== todoId);
      renderBoard();
      updateCounts();
      API.toast('To-Do eliminado', '', 'success');
    }
    
  } catch (error) {
    console.error('Failed to delete todo:', error);
    API.toast('Error al eliminar', error.message, 'error');
  }
}

/**
 * Update counts for each column
 */
function updateCounts() {
  const statuses = ['backlog', 'doing', 'done'];
  
  statuses.forEach(status => {
    const count = todos.filter(todo => todo.status === status).length;
    const countElement = $(`#count-${status}`);
    if (countElement) {
      countElement.textContent = count;
    }
  });
}

/**
 * Load saved views from localStorage
 */
function loadSavedViews() {
  try {
    const savedViews = JSON.parse(localStorage.getItem('coach_todos_saved_views') || '{}');
    
    // Apply saved view if exists
    if (savedViews.currentView) {
      applySavedView(savedViews.currentView);
    }
  } catch (error) {
    console.error('Failed to load saved views:', error);
  }
}

/**
 * Save current view to localStorage
 * @param {string} viewName - View name
 */
function saveCurrentView(viewName) {
  try {
    const savedViews = JSON.parse(localStorage.getItem('coach_todos_saved_views') || '{}');
    savedViews.currentView = viewName;
    localStorage.setItem('coach_todos_saved_views', JSON.stringify(savedViews));
  } catch (error) {
    console.error('Failed to save view:', error);
  }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
  // Search
  const searchInput = $('#search');
  if (searchInput) {
    searchInput.addEventListener('input', API.debounce((e) => {
      search = e.target.value;
      loadTodos();
    }, 300));
  }
  
  // Athlete filter
  const athleteFilter = $('#filterAthlete');
  if (athleteFilter) {
    athleteFilter.addEventListener('change', (e) => {
      filterAthlete = e.target.value;
      loadTodos();
    });
  }
  
  // Priority filter
  const priorityChips = $$('#prioChips .chip');
  priorityChips.forEach(chip => {
    chip.addEventListener('click', () => {
      priorityChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      filterP = chip.dataset.p;
      loadTodos();
    });
  });
  
  // View toggle
  const viewChips = $$('#viewChips .chip');
  viewChips.forEach(chip => {
    chip.addEventListener('click', () => {
      viewChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      view = chip.dataset.view;
      renderBoard();
      
      // Setup drag and drop for Kanban view
      if (view === 'kanban') {
        setTimeout(() => {
          setupDragAndDrop();
        }, 100);
      }
    });
  });
  
  // Saved views
  const savedViewChips = $$('.view-chip');
  savedViewChips.forEach(chip => {
    chip.addEventListener('click', () => {
      savedViewChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const viewName = chip.dataset.view;
      applySavedView(viewName);
      saveCurrentView(viewName);
    });
  });
  
  // Refresh button
  const refreshBtn = $('#btnRefresh');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadTodos);
  }
  
  // Keyboard shortcuts for selection
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Shift') {
      isShiftPressed = true;
    }
  });
  
  document.addEventListener('keyup', (e) => {
    if (e.key === 'Shift') {
      isShiftPressed = false;
    }
  });
  
  // Initial drag and drop setup for Kanban
  if (view === 'kanban') {
    setTimeout(() => {
      setupDragAndDrop();
    }, 100);
  }
}

/**
 * Apply saved view
 * @param {string} viewName - View name
 */
function applySavedView(viewName) {
  // Reset filters
  filterP = '';
  filterAthlete = '';
  search = '';
  
  // Update UI
  $('#search').value = '';
  $('#filterAthlete').value = '';
  $$('#prioChips .chip').forEach(c => c.classList.remove('active'));
  $('#prioChips .chip[data-p=""]').classList.add('active');
  
  // Apply view-specific filters
  switch (viewName) {
    case 'p1-week':
      filterP = 'P1';
      $('#prioChips .chip[data-p="P1"]').classList.add('active');
      break;
    case 'new-by-athlete':
      // Show todos created in last 7 days, grouped by athlete
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      todos = todos.filter(todo => {
        const created = new Date(todo.created_at);
        return created >= weekAgo;
      });
      break;
    case 'overdue':
      // Show overdue todos
      const today = new Date();
      todos = todos.filter(todo => {
        if (!todo.due_date || todo.status === 'done') return false;
        const due = new Date(todo.due_date);
        return due < today;
      });
      break;
  }
  
  renderBoard();
}

/**
 * Setup drag and drop functionality
 */
function setupDragAndDrop() {
  const lanes = $$('.lane');
  
  lanes.forEach(lane => {
    lane.addEventListener('dragover', (e) => {
      e.preventDefault();
      lane.classList.add('drag-over');
    });
    
    lane.addEventListener('dragleave', () => {
      lane.classList.remove('drag-over');
    });
    
    lane.addEventListener('drop', async (e) => {
      e.preventDefault();
      lane.classList.remove('drag-over');
      
      const todoId = e.dataTransfer.getData('text/plain');
      const newStatus = lane.dataset.status;
      
      if (todoId && newStatus) {
        await moveTodo(todoId, newStatus);
      }
    });
  });
  
  // Setup cards after they are rendered
  setupCardDragAndDrop();
}

/**
 * Setup drag and drop for cards
 */
function setupCardDragAndDrop() {
  const cards = $$('.card');
  
  cards.forEach(card => {
    const dragHandle = card.querySelector('.drag-handle');
    
    if (dragHandle) {
      dragHandle.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', card.dataset.id);
        card.classList.add('dragging');
      });
      
      dragHandle.addEventListener('dragend', () => {
        card.classList.remove('dragging');
      });
    }
  });
}

/**
 * Move todo to new status
 * @param {string} todoId - Todo ID
 * @param {string} newStatus - New status
 */
async function moveTodo(todoId, newStatus) {
  try {
    const response = await API.put(`/api/todos/${todoId}`, {
      status: newStatus
    });
    
    if (response.success) {
      await loadTodos();
      API.toast('To-Do movido', '', 'success');
    }
  } catch (error) {
    console.error('Failed to move todo:', error);
    API.toast('Error al mover To-Do', error.message, 'error');
  }
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Command palette (⌘/Ctrl+K)
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      showCommandPalette();
    }
    
    // Select all (⌘/Ctrl+A)
    if ((e.metaKey || e.ctrlKey) && e.key === 'a') {
      e.preventDefault();
      selectAllTodos();
    }
    
    // Deselect all (Escape)
    if (e.key === 'Escape') {
      selectedTodos.clear();
      $$('.card.selected, .list-row.selected').forEach(el => el.classList.remove('selected'));
      updateBulkActions();
    }
  });
}

/**
 * Select all todos
 */
function selectAllTodos() {
  todos.forEach(todo => {
    selectedTodos.add(todo.id.toString());
  });
  
  $$('.card, .list-row').forEach(el => {
    el.classList.add('selected');
  });
  
  updateBulkActions();
}

/**
 * Show command palette
 */
function showCommandPalette() {
  // Create command palette modal
  const modal = document.createElement('div');
  modal.className = 'command-palette';
  modal.innerHTML = `
    <div class="command-palette-overlay"></div>
    <div class="command-palette-content">
      <div class="command-palette-header">
        <i class="fa-solid fa-search"></i>
        <input type="text" placeholder="Buscar comandos..." class="command-input">
      </div>
      <div class="command-list">
        <div class="command-item" data-action="select-all">
          <i class="fa-solid fa-check-double"></i>
          <span>Seleccionar todos</span>
          <kbd>⌘+A</kbd>
        </div>
        <div class="command-item" data-action="deselect-all">
          <i class="fa-solid fa-times"></i>
          <span>Deseleccionar todos</span>
          <kbd>Esc</kbd>
        </div>
        <div class="command-item" data-action="bulk-edit">
          <i class="fa-solid fa-edit"></i>
          <span>Editar seleccionados</span>
        </div>
        <div class="command-item" data-action="bulk-move">
          <i class="fa-solid fa-arrow-right"></i>
          <span>Mover seleccionados</span>
        </div>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Focus input
  const input = modal.querySelector('.command-input');
  input.focus();
  
  // Handle input
  input.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    const items = modal.querySelectorAll('.command-item');
    
    items.forEach(item => {
      const text = item.textContent.toLowerCase();
      if (text.includes(query)) {
        item.style.display = 'flex';
      } else {
        item.style.display = 'none';
      }
    });
  });
  
  // Handle selection
  modal.addEventListener('click', (e) => {
    const item = e.target.closest('.command-item');
    if (item) {
      const action = item.dataset.action;
      executeCommand(action);
      modal.remove();
    }
  });
  
  // Close on escape
  document.addEventListener('keydown', function closeOnEscape(e) {
    if (e.key === 'Escape') {
      modal.remove();
      document.removeEventListener('keydown', closeOnEscape);
    }
  });
}

/**
 * Execute command from palette
 * @param {string} action - Command action
 */
function executeCommand(action) {
  switch (action) {
    case 'select-all':
      selectAllTodos();
      break;
    case 'deselect-all':
      selectedTodos.clear();
      $$('.card.selected, .list-row.selected').forEach(el => el.classList.remove('selected'));
      updateBulkActions();
      break;
    case 'bulk-edit':
      $('#bulkModal').classList.add('show');
      break;
    case 'bulk-move':
      bulkMoveTodos();
      break;
  }
}

/**
 * Update priority chips based on detected priority
 * @param {string} priority - Detected priority
 */
function updatePriorityChips(priority) {
  const priorityChips = $$('#prioChips .chip');
  priorityChips.forEach(chip => {
    chip.classList.remove('active');
    if (chip.dataset.p === priority) {
      chip.classList.add('active');
    }
  });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCoachTodos);
} else {
  initCoachTodos();
}