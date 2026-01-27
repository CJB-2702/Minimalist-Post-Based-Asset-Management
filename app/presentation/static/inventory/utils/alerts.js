/**
 * Alert utilities for inventory module
 * Handles displaying flash messages and toast notifications
 */

/**
 * Display flash messages from the page (flashed by Flask)
 * This should be called on page load to show any flash messages
 */
function displayFlashMessages() {
    // Check for flash messages in the page
    const flashMessages = document.querySelectorAll('.alert.alert-dismissible');
    
    flashMessages.forEach(function(alertEl) {
        // If it's a flash message (not a toast), show it
        if (alertEl.closest('.container') && !alertEl.classList.contains('position-fixed')) {
            // Flash messages are already rendered, but we can enhance them
            // Scroll to the first flash message if it exists
            if (flashMessages.length > 0) {
                flashMessages[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    });
}

/**
 * Show a toast notification using Bootstrap's toast system
 * @param {string} message - The message to display
 * @param {string} type - Type of alert: 'success', 'error', 'warning', 'info' (default: 'info')
 * @param {string} title - Optional title for the toast
 * @param {number} delay - Delay in milliseconds before auto-hiding (default: 5000)
 */
function showToast(message, type = 'info', title = null, delay = 5000) {
    // Map type to Bootstrap alert class
    const alertClassMap = {
        'success': 'success',
        'error': 'danger',
        'danger': 'danger',
        'warning': 'warning',
        'info': 'info'
    };
    
    const alertClass = alertClassMap[type] || 'info';
    
    // Get or create global toast element
    let toastContainer = document.getElementById('globalToastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'globalToastContainer';
        toastContainer.className = 'position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '11000';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <strong class="me-auto">${title || (type === 'success' ? 'Success' : type === 'error' || type === 'danger' ? 'Error' : 'Notification')}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body bg-${alertClass} text-white">
                ${message}
            </div>
        </div>
    `;
    
    // Insert toast
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = toastHtml;
    const toastEl = tempDiv.firstElementChild;
    toastContainer.appendChild(toastEl);
    
    // Initialize and show toast
    const toast = new bootstrap.Toast(toastEl, { 
        delay: delay,
        autohide: delay > 0
    });
    
    toast.show();
    
    // Remove toast element after it's hidden
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
    
    return toast;
}

/**
 * Show an inline alert in a specific container
 * @param {HTMLElement|string} container - Container element or selector
 * @param {string} message - The message to display
 * @param {string} type - Type of alert: 'success', 'error', 'warning', 'info' (default: 'info')
 * @param {boolean} dismissible - Whether the alert can be dismissed (default: true)
 */
function showInlineAlert(container, message, type = 'info', dismissible = true) {
    const alertClassMap = {
        'success': 'success',
        'error': 'danger',
        'danger': 'danger',
        'warning': 'warning',
        'info': 'info'
    };
    
    const alertClass = alertClassMap[type] || 'info';
    
    // Get container element
    const containerEl = typeof container === 'string' 
        ? document.querySelector(container) 
        : container;
    
    if (!containerEl) {
        console.error('Container element not found for inline alert');
        return;
    }
    
    // Remove any existing alerts in the container
    const existingAlerts = containerEl.querySelectorAll('.alert');
    existingAlerts.forEach(function(alert) {
        alert.remove();
    });
    
    // Create alert element
    const alertHtml = `
        <div class="alert alert-${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            ${dismissible ? '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' : ''}
        </div>
    `;
    
    containerEl.insertAdjacentHTML('afterbegin', alertHtml);
    
    // Scroll to alert if needed
    containerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/**
 * Initialize alert system - call this on page load
 */
function initAlerts() {
    // Display any flash messages that were rendered on page load
    displayFlashMessages();
}

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAlerts);
} else {
    initAlerts();
}

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        displayFlashMessages,
        showToast,
        showInlineAlert,
        initAlerts
    };
}

