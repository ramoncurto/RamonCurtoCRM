// ===== ATHLETES MANAGEMENT =====

/**
 * Athletes management functionality
 * Handles loading, filtering, editing, creating, and deleting athletes
 */

// State
let athletes = []; // {id, name, email, phone, sport, level, created_at, last_contact, open_todos, risk_level, risk_score, risk_color, explanations}
let filtered = [];
let editingRow = null;
let sports = new Set();
let levels = new Set();

// Use API functions to avoid conflicts - $ and $$ are already defined in api.js

/**
 * Load athletes from enhanced API (without automatic risk assessment)
 */
async function loadAthletes() {
  try {
    const response = await API.get('/api/athletes/enhanced');
    athletes = (response.athletes || []).map(athlete => ({
      id: athlete.id,
      name: athlete.name || '',
      email: athlete.email || '',
      phone: athlete.phone || '',
      sport: athlete.sport || '',
      level: athlete.level || '',
      created_at: athlete.created_at,
      last_contact: athlete.last_contact,
      open_todos: athlete.open_todos || 0,
      risk_level: 'pendiente', // Default to pending instead of loading automatically
      risk_score: 0,
      risk_color: 'warning', // Use warning color for pending
      explanations: []
    }));
    
    // Extract unique sports and levels for filters
    sports.clear();
    levels.clear();
    athletes.forEach(athlete => {
      if (athlete.sport) sports.add(athlete.sport);
      if (athlete.level) levels.add(athlete.level);
    });
    
    // Don't load risk assessments automatically - make it manual
    // await loadRiskAssessments();
    
    updateFilters();
    applySearch($('#search').value || '');
  } catch (error) {
    console.error('Failed to load athletes:', error);
    API.toast('Error al cargar atletas', error.message, 'error');
    athletes = [];
    render();
  }
}

/**
 * Load risk assessment for a specific athlete (manual trigger)
 */
async function loadRiskAssessmentForAthlete(athleteId) {
  const athlete = athletes.find(a => a.id === athleteId);
  if (!athlete) return;
  
  try {
    // Show loading state
    athlete.risk_level = 'cargando...';
    athlete.risk_color = 'info';
    render();
    
    const riskResponse = await API.get(`/api/athletes/${athleteId}/risk`);
    
    // Update athlete with new risk data
    athlete.risk_level = riskResponse.level || riskResponse.risk_level || 'bajo';
    athlete.risk_color = riskResponse.color || riskResponse.risk_color || 'success';
    athlete.score = riskResponse.score || riskResponse.risk_score || 0;
    athlete.risk_score = athlete.score;
    
    // Use new evidence format if available
    if (riskResponse.evidence && riskResponse.evidence.length > 0) {
      athlete.evidence = riskResponse.evidence;
    } else if (riskResponse.explanations && riskResponse.explanations.length > 0) {
      athlete.explanations = riskResponse.explanations;
    }
    
    // Store additional risk data for potential future use
    athlete.risk_factors = riskResponse.factors;
    athlete.raw_score = riskResponse.raw_score;
    athlete.smoothed_score = riskResponse.smoothed_score;
    athlete.days_since_contact = riskResponse.days_since_contact;
    athlete.overdue_count = riskResponse.overdue_count;
    athlete.negative_highlights = riskResponse.negative_highlights;
    athlete.total_highlights = riskResponse.total_highlights;
    athlete.sentiment_mm7 = riskResponse.sentiment_mm7;
    athlete.pain_matches = riskResponse.pain_matches;
    
    API.toast('Evaluación de riesgo completada', `Riesgo: ${athlete.risk_level}`, 'success');
    
  } catch (error) {
    console.error(`Failed to load risk for athlete ${athleteId}:`, error);
    athlete.risk_level = 'error';
    athlete.risk_color = 'danger';
    API.toast('Error al evaluar riesgo', error.message, 'error');
  }
  
  render();
}

/**
 * Load risk assessments for all athletes (manual trigger)
 */
async function loadRiskAssessmentsForAll() {
  API.toast('Iniciando evaluación de riesgo', 'Evaluando todos los atletas...', 'info');
  
  const riskPromises = athletes.map(async (athlete) => {
    if (!athlete.id) return athlete;
    
    try {
      const riskResponse = await API.get(`/api/athletes/${athlete.id}/risk`);
      
      // Update athlete with new risk data
      athlete.risk_level = riskResponse.level || riskResponse.risk_level || 'bajo';
      athlete.risk_color = riskResponse.color || riskResponse.risk_color || 'success';
      athlete.score = riskResponse.score || riskResponse.risk_score || 0;
      athlete.risk_score = athlete.score;
      
      // Use new evidence format if available
      if (riskResponse.evidence && riskResponse.evidence.length > 0) {
        athlete.evidence = riskResponse.evidence;
      } else if (riskResponse.explanations && riskResponse.explanations.length > 0) {
        athlete.explanations = riskResponse.explanations;
      }
      
      // Store additional risk data for potential future use
      athlete.risk_factors = riskResponse.factors;
      athlete.raw_score = riskResponse.raw_score;
      athlete.smoothed_score = riskResponse.smoothed_score;
      athlete.days_since_contact = riskResponse.days_since_contact;
      athlete.overdue_count = riskResponse.overdue_count;
      athlete.negative_highlights = riskResponse.negative_highlights;
      athlete.total_highlights = riskResponse.total_highlights;
      athlete.sentiment_mm7 = riskResponse.sentiment_mm7;
      athlete.pain_matches = riskResponse.pain_matches;
      
    } catch (error) {
      console.error(`Failed to load risk for athlete ${athlete.id}:`, error);
      athlete.risk_level = 'error';
      athlete.risk_color = 'danger';
    }
    
    return athlete;
  });
  
  await Promise.all(riskPromises);
  API.toast('Evaluación completada', 'Riesgo evaluado para todos los atletas', 'success');
  render();
}

/**
 * Update filter dropdowns with available options
 */
function updateFilters() {
  const sportSelect = $('#filterSport');
  const levelSelect = $('#filterLevel');
  const riskSelect = $('#filterRisk');
  
  if (sportSelect) {
    const currentSport = sportSelect.value;
    sportSelect.innerHTML = '<option value="">Todos los deportes</option>';
    Array.from(sports).sort().forEach(sport => {
      const option = document.createElement('option');
      option.value = sport;
      option.textContent = sport;
      sportSelect.appendChild(option);
    });
    sportSelect.value = currentSport;
  }
  
  if (levelSelect) {
    const currentLevel = levelSelect.value;
    levelSelect.innerHTML = '<option value="">Todos los niveles</option>';
    Array.from(levels).sort().forEach(level => {
      const option = document.createElement('option');
      option.value = level;
      option.textContent = level;
      levelSelect.appendChild(option);
    });
    levelSelect.value = currentLevel;
  }
  
  if (riskSelect) {
    const currentRisk = riskSelect.value;
    riskSelect.innerHTML = '<option value="">Todos los riesgos</option>';
    riskSelect.innerHTML += '<option value="pendiente">Pendiente</option>';
    riskSelect.innerHTML += '<option value="verde">Verde (Bajo)</option>';
    riskSelect.innerHTML += '<option value="ámbar">Ámbar (Medio)</option>';
    riskSelect.innerHTML += '<option value="rojo">Rojo (Alto)</option>';
    riskSelect.value = currentRisk;
  }
}

/**
 * Apply search and filter to athletes
 * @param {string} query - Search query
 */
function applySearch(query) {
  query = (query || '').toLowerCase();
  const sportFilter = $('#filterSport')?.value || '';
  const levelFilter = $('#filterLevel')?.value || '';
  const riskFilter = $('#filterRisk')?.value || '';
  
  filtered = athletes.filter(athlete => {
    // Search filter
    const matchesSearch = !query || 
      (athlete.name || '').toLowerCase().includes(query) ||
      (athlete.email || '').toLowerCase().includes(query) ||
      (athlete.sport || '').toLowerCase().includes(query) ||
      (athlete.level || '').toLowerCase().includes(query);
    
    // Sport filter
    const matchesSport = !sportFilter || athlete.sport === sportFilter;
    
    // Level filter
    const matchesLevel = !levelFilter || athlete.level === levelFilter;
    
    // Risk filter
    const matchesRisk = !riskFilter || athlete.risk_level === riskFilter;
    
    return matchesSearch && matchesSport && matchesLevel && matchesRisk;
  });
  
  render();
}

/**
 * Render athletes table
 */
function render() {
  const tbody = $('#tbody');
  const empty = $('#empty');
  
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  if (empty) {
    empty.style.display = filtered.length ? 'none' : 'block';
  }
  
  filtered.forEach(athlete => {
    tbody.appendChild(createAthleteRow(athlete));
  });
}

/**
 * Create athlete table row
 * @param {Object} athlete - Athlete data
 * @returns {HTMLElement} Table row element
 */
function createAthleteRow(athlete) {
  const tr = document.createElement('tr');
  tr.dataset.id = athlete.id || '';
  tr.dataset.editing = 'false';
  
  // Format last contact
  const lastContact = formatLastContact(athlete.last_contact);
  
  // Format todos count
  const todosCount = formatTodosCount(athlete.open_todos);
  
  // Format risk chip
  const riskChip = formatRiskChip(athlete);
  
  tr.innerHTML = `
    <td class="id">${athlete.id || '—'}</td>
    <td>
      <input class="input mini" value="${API.escapeHtml(athlete.name || '')}" 
             data-field="name" placeholder="Nombre" ${!athlete.id ? 'autofocus' : ''}>
    </td>
    <td>
      <input class="input mini" value="${API.escapeHtml(athlete.email || '')}" 
             data-field="email" placeholder="Email">
    </td>
    <td>
      <input class="input mini" value="${API.escapeHtml(athlete.phone || '')}" 
             data-field="phone" placeholder="Teléfono">
    </td>
    <td>
      <input class="input mini" value="${API.escapeHtml(athlete.sport || '')}" 
             data-field="sport" placeholder="Deporte">
    </td>
    <td>
      <input class="input mini" value="${API.escapeHtml(athlete.level || '')}" 
             data-field="level" placeholder="Nivel">
    </td>
    <td>
      ${riskChip}
      ${athlete.id ? `<button class="btn mini" onclick="loadRiskAssessmentForAthlete(${athlete.id})" title="Evaluar riesgo">
        <i class="fa-solid fa-calculator"></i>
      </button>` : ''}
    </td>
    <td>
      <span class="last-contact ${lastContact.class}">${lastContact.text}</span>
    </td>
    <td>
      <span class="todos-count ${todosCount.class}">${todosCount.text}</span>
    </td>
    <td>
      <div class="row-actions">
        ${athlete.id ? 
          `<a class="btn" href="/athletes/${athlete.id}/workspace" title="Workspace">
             <i class="fa-solid fa-up-right-from-square"></i>
           </a>` : ''
        }
        <button class="btn success" data-action="save" title="Guardar">
          <i class="fa-solid fa-floppy-disk"></i>
        </button>
        ${athlete.id ? 
          `<button class="btn danger" data-action="delete" title="Eliminar">
             <i class="fa-solid fa-trash"></i>
           </button>` : ''
        }
      </div>
    </td>
  `;
  
  // Add event listeners
  tr.addEventListener('click', handleRowAction);
  
  // Add keyboard shortcuts
  const inputs = $$('input', tr);
  inputs.forEach(input => {
    input.addEventListener('keydown', handleInputKeydown);
    input.addEventListener('blur', () => validateRow(tr));
    input.addEventListener('input', () => validateField(input));
  });
  
  return tr;
}

/**
 * Format last contact date
 * @param {string} lastContact - Last contact timestamp
 * @returns {Object} Formatted contact info
 */
function formatLastContact(lastContact) {
  if (!lastContact) {
    return { text: 'Sin contacto', class: 'old' };
  }
  
  const date = new Date(lastContact);
  const now = new Date();
  const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
  
  if (diffDays <= 7) {
    return { text: `${diffDays} días`, class: 'recent' };
  } else if (diffDays <= 30) {
    return { text: `${diffDays} días`, class: '' };
  } else {
    return { text: `${diffDays} días`, class: 'old' };
  }
}

/**
 * Format todos count
 * @param {number} count - Number of open todos
 * @returns {Object} Formatted todos info
 */
function formatTodosCount(count) {
  if (count === 0) {
    return { text: '0', class: '' };
  } else if (count <= 3) {
    return { text: count.toString(), class: 'has-todos' };
  } else {
    return { text: count.toString(), class: 'many-todos' };
  }
}

/**
 * Format risk chip
 * @param {Object} athlete - Athlete data
 * @returns {string} HTML for risk chip
 */
function formatRiskChip(athlete) {
  if (!athlete.id) {
    return '<span class="risk-chip">—</span>';
  }
  
  const riskLevel = athlete.risk_level || 'pendiente';
  const riskColor = athlete.risk_color || 'warning';
  const riskScore = athlete.score || athlete.risk_score || 0;
  
  // Handle special states
  if (riskLevel === 'pendiente') {
    return `<span class="risk-chip warning" title="Evaluación de riesgo pendiente">
      <i class="fa-solid fa-clock"></i>
      PENDIENTE
    </span>`;
  }
  
  if (riskLevel === 'cargando...') {
    return `<span class="risk-chip info" title="Evaluando riesgo...">
      <i class="fa-solid fa-spinner fa-spin"></i>
      EVALUANDO
    </span>`;
  }
  
  if (riskLevel === 'error') {
    return `<span class="risk-chip danger" title="Error al evaluar riesgo">
      <i class="fa-solid fa-exclamation-circle"></i>
      ERROR
    </span>`;
  }
  
  // Build tooltip with evidence
  let tooltip = '';
  if (athlete.evidence && athlete.evidence.length > 0) {
    tooltip = `title="${athlete.evidence.join(' • ')}"`;
  } else if (athlete.explanations && athlete.explanations.length > 0) {
    tooltip = `title="${athlete.explanations.join(' • ')}"`;
  }
  
  // Map risk levels to Spanish
  const levelMap = {
    'bajo': 'BAJO',
    'medio': 'MEDIO', 
    'alto': 'ALTO',
    'verde': 'BAJO',
    'ámbar': 'MEDIO',
    'rojo': 'ALTO'
  };
  
  const displayLevel = levelMap[riskLevel] || riskLevel.toUpperCase();
  
  return `<span class="risk-chip ${riskColor}" ${tooltip}>
    <i class="fa-solid fa-exclamation-triangle"></i>
    ${displayLevel}
    <span class="risk-score">${Math.round(riskScore)}</span>
  </span>`;
}

/**
 * Handle row action clicks
 * @param {Event} event - Click event
 */
async function handleRowAction(event) {
  const action = event.target.closest('[data-action]')?.dataset?.action;
  if (!action) return;
  
  const row = event.target.closest('tr');
  
  switch (action) {
    case 'save':
      await saveAthlete(row);
      break;
    case 'delete':
      await deleteAthlete(row);
      break;
  }
}

/**
 * Handle input keyboard events
 * @param {Event} event - Keyboard event
 */
function handleInputKeydown(event) {
  const row = event.target.closest('tr');
  
  switch (event.key) {
    case 'Enter':
      event.preventDefault();
      saveAthlete(row);
      break;
    case 'Escape':
      event.preventDefault();
      if (row.dataset.id) {
        // Cancel editing for existing athlete
        loadAthletes();
      } else {
        // Remove new athlete row
        row.remove();
      }
      break;
  }
}

/**
 * Validate a single field
 * @param {HTMLElement} input - Input element
 */
function validateField(input) {
  const field = input.dataset.field;
  const value = input.value.trim();
  
  // Remove existing validation classes
  input.classList.remove('error', 'success');
  
  switch (field) {
    case 'name':
      if (!value) {
        input.classList.add('error');
      } else {
        input.classList.add('success');
      }
      break;
    case 'email':
      if (value && !isValidEmail(value)) {
        input.classList.add('error');
      } else if (value) {
        input.classList.add('success');
      }
      break;
    case 'phone':
      if (value && !isValidPhone(value)) {
        input.classList.add('error');
      } else if (value) {
        input.classList.add('success');
      }
      break;
  }
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} Is valid email
 */
function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validate phone format
 * @param {string} phone - Phone to validate
 * @returns {boolean} Is valid phone
 */
function isValidPhone(phone) {
  const phoneRegex = /^[\+]?[0-9\s\-\(\)]{8,}$/;
  return phoneRegex.test(phone);
}

/**
 * Validate entire row
 * @param {HTMLElement} row - Table row
 * @returns {boolean} Is valid
 */
function validateRow(row) {
  const inputs = $$('input', row);
  let isValid = true;
  
  inputs.forEach(input => {
    validateField(input);
    if (input.classList.contains('error')) {
      isValid = false;
    }
  });
  
  return isValid;
}

/**
 * Collect data from row inputs
 * @param {HTMLElement} row - Table row
 * @returns {Object} Athlete data
 */
function collectRowData(row) {
  const inputs = $$('input', row);
  const data = {};
  
  inputs.forEach(input => {
    const field = input.dataset.field;
    if (field) {
      data[field] = input.value.trim();
    }
  });
  
  if (row.dataset.id) {
    data.id = row.dataset.id;
  }
  
  return data;
}

/**
 * Save athlete (create or update)
 * @param {HTMLElement} row - Table row
 */
async function saveAthlete(row) {
  const data = collectRowData(row);
  
  if (!validateRow(row)) {
    API.toast('Error', 'Por favor corrige los errores de validación', 'error');
    return;
  }
  
  try {
    const saveBtn = row.querySelector('[data-action="save"]');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    saveBtn.disabled = true;
    
    if (data.id) {
      // Update existing athlete
      const response = await API.put(`/api/athletes/${data.id}`, data);
      if (response.success) {
        API.toast('Atleta actualizado', '', 'success');
        // Update local data
        const index = athletes.findIndex(a => a.id === data.id);
        if (index !== -1) {
          athletes[index] = { ...athletes[index], ...data };
        }
      } else {
        throw new Error(response.error || 'Error al actualizar');
      }
    } else {
      // Create new athlete
      const response = await API.post('/api/athletes', data);
      if (response.athlete_id) {
        data.id = response.athlete_id;
        athletes.unshift(data);
        API.toast('Atleta creado', '', 'success');
        // Replace row with new one that has ID
        row.replaceWith(createAthleteRow(data));
        return; // Exit early since we replaced the row
      } else {
        throw new Error('Error al crear atleta');
      }
    }
    
    // Refresh data
    await loadAthletes();
    
  } catch (error) {
    console.error('Failed to save athlete:', error);
    API.toast('Error al guardar', error.message, 'error');
  } finally {
    const saveBtn = row.querySelector('[data-action="save"]');
    if (saveBtn) {
      saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i>';
      saveBtn.disabled = false;
    }
  }
}

/**
 * Delete athlete
 * @param {HTMLElement} row - Table row
 */
async function deleteAthlete(row) {
  const athleteId = row.dataset.id;
  if (!athleteId) {
    row.remove();
    return;
  }
  
  if (!confirm('¿Eliminar atleta y todos sus datos? Esta acción no se puede deshacer.')) {
    return;
  }
  
  try {
    const deleteBtn = row.querySelector('[data-action="delete"]');
    const originalText = deleteBtn.innerHTML;
    deleteBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    deleteBtn.disabled = true;
    
    const response = await API.delete(`/api/athletes/${athleteId}`);
    if (response.success) {
      API.toast('Atleta eliminado', '', 'success');
      // Remove from local data
      athletes = athletes.filter(a => String(a.id) !== String(athleteId));
      row.remove();
    } else {
      throw new Error(response.error || 'Error al eliminar');
    }
  } catch (error) {
    console.error('Failed to delete athlete:', error);
    API.toast('Error al eliminar', error.message, 'error');
  } finally {
    const deleteBtn = row.querySelector('[data-action="delete"]');
    if (deleteBtn) {
      deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
      deleteBtn.disabled = false;
    }
  }
}

/**
 * Create new athlete row
 */
function createNewAthlete() {
  const tbody = $('#tbody');
  if (!tbody) {
    return;
  }
  
  const newAthlete = {
    name: '',
    email: '',
    phone: '',
    sport: '',
    level: '',
    open_todos: 0
  };
  
  const newRow = createAthleteRow(newAthlete);
  tbody.insertBefore(newRow, tbody.firstChild);
  
  // Focus on name input
  const nameInput = newRow.querySelector('input[data-field="name"]');
  if (nameInput) {
    nameInput.focus();
  }
}

/**
 * Initialize athletes page
 */
function initAthletesPage() {
  // Load initial data
  loadAthletes();
  
  // Search functionality
  const searchInput = $('#search');
  if (searchInput) {
    searchInput.addEventListener('input', API.debounce((e) => {
      applySearch(e.target.value);
    }, 300));
  }
  
  // Filter functionality
  const sportFilter = $('#filterSport');
  const levelFilter = $('#filterLevel');
  const riskFilter = $('#filterRisk');
  
  if (sportFilter) {
    sportFilter.addEventListener('change', () => {
      applySearch($('#search').value || '');
    });
  }
  
  if (levelFilter) {
    levelFilter.addEventListener('change', () => {
      applySearch($('#search').value || '');
    });
  }

  if (riskFilter) {
    riskFilter.addEventListener('change', () => {
      applySearch($('#search').value || '');
    });
  }
  
  // New athlete button
  const newBtn = $('#btnNew');
  if (newBtn) {
    newBtn.addEventListener('click', createNewAthlete);
  }
  
  // Risk assessment button
  const riskBtn = $('#btnRiskAssessment');
  if (riskBtn) {
    riskBtn.addEventListener('click', loadRiskAssessmentsForAll);
  }
  
  // Saved views button
  const savedViewsBtn = $('#btnSavedViews');
  if (savedViewsBtn) {
    savedViewsBtn.addEventListener('click', () => {
      API.toast('Vistas guardadas', 'Funcionalidad próximamente', 'info');
    });
  }
  
  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      searchInput?.focus();
    }
    
    // Ctrl/Cmd + N to create new athlete
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
      e.preventDefault();
      createNewAthlete();
    }
    
    // Ctrl/Cmd + R to evaluate all risks
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
      e.preventDefault();
      loadRiskAssessmentsForAll();
    }
  });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAthletesPage);
} else {
  initAthletesPage();
}