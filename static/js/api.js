// ===== API HELPERS =====

/**
 * API helper functions for consistent HTTP requests and error handling
 */

// Base API configuration
const API_BASE = '';

// Utility functions
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

/**
 * Show a toast notification
 * @param {string} title - Toast title
 * @param {string} msg - Toast message (optional)
 * @param {string} type - Toast type: 'success', 'error', 'warning', 'info'
 * @param {number} duration - Duration in milliseconds (default: 4000)
 */
function toast(title, msg = '', type = 'info', duration = 4000) {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  // Enhanced icons for each type
  const icons = {
    'error': 'fa-circle-exclamation',
    'success': 'fa-circle-check',
    'warning': 'fa-triangle-exclamation',
    'info': 'fa-circle-info',
    'loading': 'fa-spinner fa-spin'
  };
  
  const icon = icons[type] || icons.info;
  
  // Enhanced styling based on type
  const typeStyles = {
    'error': 'border-left-color: var(--danger); background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(239, 68, 68, 0.05));',
    'success': 'border-left-color: var(--success); background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(16, 185, 129, 0.05));',
    'warning': 'border-left-color: var(--warning); background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(245, 158, 11, 0.05));',
    'info': 'border-left-color: var(--info); background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(59, 130, 246, 0.05));',
    'loading': 'border-left-color: var(--primary); background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(99, 102, 241, 0.05));'
  };
  
  toast.style = typeStyles[type] || typeStyles.info;
  
  toast.innerHTML = `
    <div class="toast-icon">
      <i class="fa-solid ${icon}"></i>
    </div>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      ${msg ? `<div class="toast-message">${msg}</div>` : ''}
    </div>
    <button class="toast-close" onclick="this.closest('.toast').remove()">
      <i class="fa-solid fa-times"></i>
    </button>
    <div class="toast-progress"></div>
  `;
  
  const toastsContainer = $('#toasts') || createToastsContainer();
  toastsContainer.appendChild(toast);
  
  // Enhanced animation
  requestAnimationFrame(() => {
    toast.classList.add('show');
    
    // Start progress bar animation
    const progressBar = toast.querySelector('.toast-progress');
    if (progressBar) {
      progressBar.style.transition = `width ${duration}ms linear`;
      requestAnimationFrame(() => {
        progressBar.style.width = '0%';
      });
    }
  });
  
  // Auto remove after duration
  const timeoutId = setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => {
      if (toast.parentNode) {
        toast.remove();
      }
    }, 300);
  }, duration);
  
  // Store timeout ID for manual removal
  toast.dataset.timeoutId = timeoutId;
  
  // Add hover pause functionality
  toast.addEventListener('mouseenter', () => {
    clearTimeout(timeoutId);
    const progressBar = toast.querySelector('.toast-progress');
    if (progressBar) {
      progressBar.style.transition = 'none';
    }
  });
  
  toast.addEventListener('mouseleave', () => {
    const remainingTime = duration - (Date.now() - toast.dataset.startTime);
    if (remainingTime > 0) {
      const newTimeoutId = setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
          if (toast.parentNode) {
            toast.remove();
          }
        }, 300);
      }, remainingTime);
      toast.dataset.timeoutId = newTimeoutId;
      
      const progressBar = toast.querySelector('.toast-progress');
      if (progressBar) {
        progressBar.style.transition = `width ${remainingTime}ms linear`;
        requestAnimationFrame(() => {
          progressBar.style.width = '0%';
        });
      }
    }
  });
  
  // Store start time for hover functionality
  toast.dataset.startTime = Date.now();
}

/**
 * Show a loading toast that can be dismissed manually
 * @param {string} title - Toast title
 * @param {string} msg - Toast message (optional)
 * @returns {HTMLElement} The toast element for manual removal
 */
function showLoadingToast(title, msg = '') {
  const toast = document.createElement('div');
  toast.className = 'toast toast-loading';
  toast.style = 'border-left-color: var(--primary); background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(99, 102, 241, 0.05));';
  
  toast.innerHTML = `
    <div class="toast-icon">
      <i class="fa-solid fa-spinner fa-spin"></i>
    </div>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      ${msg ? `<div class="toast-message">${msg}</div>` : ''}
    </div>
    <button class="toast-close" onclick="this.closest('.toast').remove()">
      <i class="fa-solid fa-times"></i>
    </button>
  `;
  
  const toastsContainer = $('#toasts') || createToastsContainer();
  toastsContainer.appendChild(toast);
  
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });
  
  return toast;
}

/**
 * Show a toast notification with undo functionality
 * @param {string} title - Toast title
 * @param {string} undoText - Undo button text
 * @param {Function} undoCallback - Function to call when undo is clicked
 * @param {string} type - Toast type: 'success', 'error', 'warning', 'info'
 * @param {number} duration - Duration in milliseconds (default: 5000)
 */
function showToastWithUndo(title, undoText, undoCallback, type = 'success', duration = 5000) {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  // Enhanced icons for each type
  const icons = {
    'error': 'fa-circle-exclamation',
    'success': 'fa-circle-check',
    'warning': 'fa-triangle-exclamation',
    'info': 'fa-circle-info',
    'loading': 'fa-spinner fa-spin'
  };
  
  const icon = icons[type] || icons.info;
  
  // Enhanced styling based on type
  const typeStyles = {
    'error': 'border-left-color: var(--danger); background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(239, 68, 68, 0.05));',
    'success': 'border-left-color: var(--success); background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(16, 185, 129, 0.05));',
    'warning': 'border-left-color: var(--warning); background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(245, 158, 11, 0.05));',
    'info': 'border-left-color: var(--info); background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(59, 130, 246, 0.05));',
    'loading': 'border-left-color: var(--primary); background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(99, 102, 241, 0.05));'
  };
  
  toast.style = typeStyles[type] || typeStyles.info;
  
  toast.innerHTML = `
    <div class="toast-icon">
      <i class="fa-solid ${icon}"></i>
    </div>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <button class="toast-undo" onclick="this.closest('.toast').undoAction()">
        ${undoText}
      </button>
    </div>
    <button class="toast-close" onclick="this.closest('.toast').remove()">
      <i class="fa-solid fa-times"></i>
    </button>
    <div class="toast-progress"></div>
  `;
  
  // Store undo callback
  toast.undoAction = undoCallback;
  
  const toastsContainer = $('#toasts') || createToastsContainer();
  toastsContainer.appendChild(toast);
  
  // Enhanced animation
  requestAnimationFrame(() => {
    toast.classList.add('show');
    
    // Start progress bar animation
    const progressBar = toast.querySelector('.toast-progress');
    if (progressBar) {
      progressBar.style.transition = `width ${duration}ms linear`;
      requestAnimationFrame(() => {
        progressBar.style.width = '0%';
      });
    }
  });
  
  // Auto remove after duration
  const timeoutId = setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => {
      if (toast.parentNode) {
        toast.remove();
      }
    }, 300);
  }, duration);
  
  // Store timeout ID for manual removal
  toast.dataset.timeoutId = timeoutId;
  
  // Add hover pause functionality
  toast.addEventListener('mouseenter', () => {
    clearTimeout(timeoutId);
    const progressBar = toast.querySelector('.toast-progress');
    if (progressBar) {
      progressBar.style.transition = 'none';
    }
  });
  
  toast.addEventListener('mouseleave', () => {
    const remainingTime = duration - (Date.now() - toast.dataset.startTime);
    if (remainingTime > 0) {
      const newTimeoutId = setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
          if (toast.parentNode) {
            toast.remove();
          }
        }, 300);
      }, remainingTime);
      toast.dataset.timeoutId = newTimeoutId;
      
      const progressBar = toast.querySelector('.toast-progress');
      if (progressBar) {
        progressBar.style.transition = `width ${remainingTime}ms linear`;
        requestAnimationFrame(() => {
          progressBar.style.width = '0%';
        });
      }
    }
  });
  
  // Store start time for hover functionality
  toast.dataset.startTime = Date.now();
}

/**
 * Create toasts container if it doesn't exist
 */
function createToastsContainer() {
  const container = document.createElement('div');
  container.className = 'toasts';
  container.setAttribute('aria-live', 'polite');
  container.setAttribute('aria-atomic', 'true');
  container.id = 'toasts';
  document.body.appendChild(container);
  return container;
}

/**
 * Make HTTP request with consistent error handling
 * @param {string} url - Request URL
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} Response data
 */
async function apiRequest(url, options = {}) {
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...options.headers
      },
      ...options
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    } else {
      return { success: true, data: await response.text() };
    }
  } catch (error) {
    console.error('API Request failed:', error);
    throw error;
  }
}

/**
 * GET request helper
 * @param {string} url - Request URL
 * @param {Object} params - Query parameters
 * @returns {Promise<Object>} Response data
 */
async function apiGet(url, params = {}) {
  const queryString = new URLSearchParams(params).toString();
  const fullUrl = queryString ? `${url}?${queryString}` : url;
  return apiRequest(fullUrl, { method: 'GET' });
}

/**
 * POST request helper
 * @param {string} url - Request URL
 * @param {Object} data - Form data
 * @returns {Promise<Object>} Response data
 */
async function apiPost(url, data = {}) {
  const formData = new URLSearchParams();
  for (const [key, value] of Object.entries(data)) {
    if (value !== null && value !== undefined) {
      formData.append(key, value);
    }
  }
  
  return apiRequest(url, {
    method: 'POST',
    body: formData
  });
}

/**
 * PUT request helper
 * @param {string} url - Request URL
 * @param {Object} data - Form data
 * @returns {Promise<Object>} Response data
 */
async function apiPut(url, data = {}) {
  const formData = new URLSearchParams();
  for (const [key, value] of Object.entries(data)) {
    if (value !== null && value !== undefined) {
      formData.append(key, value);
    }
  }
  
  return apiRequest(url, {
    method: 'PUT',
    body: formData
  });
}

/**
 * DELETE request helper
 * @param {string} url - Request URL
 * @returns {Promise<Object>} Response data
 */
async function apiDelete(url) {
  return apiRequest(url, { method: 'DELETE' });
}

/**
 * Upload file with progress tracking
 * @param {string} url - Upload URL
 * @param {File} file - File to upload
 * @param {Function} onProgress - Progress callback (optional)
 * @returns {Promise<Object>} Response data
 */
async function apiUpload(url, file, onProgress = null) {
  const formData = new FormData();
  formData.append('file', file);
  
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    
    if (onProgress) {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100;
          onProgress(percentComplete);
        }
      });
    }
    
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response);
        } catch (e) {
          resolve({ success: true, data: xhr.responseText });
        }
      } else {
        reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
      }
    });
    
    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed: Network error'));
    });
    
    xhr.open('POST', url);
    xhr.send(formData);
  });
}

/**
 * Debounce function to limit API calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function to limit API calls
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
function throttle(func, limit) {
  let inThrottle;
  return function() {
    const args = arguments;
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Safe JSON parse with error handling
 * @param {string} str - JSON string
 * @param {*} defaultValue - Default value if parsing fails
 * @returns {*} Parsed value or default
 */
function safeJsonParse(str, defaultValue = null) {
  try {
    return JSON.parse(str);
  } catch (e) {
    return defaultValue;
  }
}

/**
 * Escape HTML to prevent XSS
 * @param {string} str - String to escape
 * @returns {string} Escaped string
 */
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Format date for display
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date
 */
function formatDate(date) {
  if (!date) return '';
  
  // Handle ISO string normalization
  let d;
  if (typeof date === 'string') {
    // Normalize ISO string to ensure proper parsing
    const isoString = date.includes('T') ? date : `${date}T00:00:00`;
    d = new Date(isoString);
  } else {
    d = new Date(date);
  }
  
  if (isNaN(d.getTime())) return '';
  
  // Format with Europe/Madrid timezone
  return new Intl.DateTimeFormat('es-ES', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Europe/Madrid'
  }).format(d);
}

/**
 * Format relative time (e.g., "2 hours ago")
 * @param {string|Date} date - Date to format
 * @returns {string} Relative time string
 */
function formatRelativeTime(date) {
  if (!date) return '';
  
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';
  
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 1) return 'Justo ahora';
  if (diffMins < 60) return `Hace ${diffMins} min`;
  if (diffHours < 24) return `Hace ${diffHours} h`;
  if (diffDays < 7) return `Hace ${diffDays} días`;
  
  return formatDate(date);
}

// Export functions for use in other modules
window.API = {
  get: apiGet,
  post: apiPost,
  put: apiPut,
  delete: apiDelete,
  upload: apiUpload,
  toast,
  showToastWithUndo,
  showLoadingToast,
  debounce,
  throttle,
  safeJsonParse,
  escapeHtml,
  formatDate,
  formatRelativeTime
};