/**
 * JavaScript for Create Arrival from PO Lines page
 * Simplified with HTMX - only handles HX-Trigger events for toasts
 */

// Handle form response for redirect timing (HTMX handles most of the work)
function handleFormResponse(event) {
  // HTMX will handle the redirect via HX-Redirect header
  // This function is mainly for any additional cleanup if needed
  if (event.detail.xhr && event.detail.xhr.status >= 400) {
    // Error responses are handled by backend returning error HTML in target
    // HTMX will automatically swap it into #form-messages
    // Also show a toast alert for better visibility
    
    let errorMessage = 'An error occurred while creating the arrival.';
    
    // First, try to get the error message from the swapped content in #form-messages
    // (HTMX will have already swapped the error HTML there)
    const formMessages = document.getElementById('form-messages');
    if (formMessages) {
      const alertElement = formMessages.querySelector('.alert-danger, .alert');
      if (alertElement) {
        // Extract text content, removing the icon and close button text
        // Clone to avoid modifying the original
        const clone = alertElement.cloneNode(true);
        // Remove the close button
        const closeBtn = clone.querySelector('.btn-close');
        if (closeBtn) closeBtn.remove();
        // Remove any icons
        const icons = clone.querySelectorAll('i.bi');
        icons.forEach(icon => icon.remove());
        errorMessage = clone.textContent.trim();
      }
    }
    
    // Fallback: try to extract from response if not found in DOM
    if (errorMessage === 'An error occurred while creating the arrival.') {
      const responseText = event.detail.xhr.responseText || '';
      
      // Check if response is HTML with an alert message
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = responseText;
      const alertElement = tempDiv.querySelector('.alert-danger, .alert');
      if (alertElement) {
        // Extract text content
        const clone = alertElement.cloneNode(true);
        const closeBtn = clone.querySelector('.btn-close');
        if (closeBtn) closeBtn.remove();
        const icons = clone.querySelectorAll('i.bi');
        icons.forEach(icon => icon.remove());
        errorMessage = clone.textContent.trim();
      } else {
        // Try to parse as JSON if it's a JSON response
        try {
          const jsonResponse = JSON.parse(responseText);
          if (jsonResponse.message) {
            errorMessage = jsonResponse.message;
          }
        } catch (e) {
          // Not JSON, use default message
        }
      }
    }
    
    // Show toast alert using alerts.js
    if (typeof showToast === 'function') {
      showToast(errorMessage, 'error', 'Arrival Creation Failed', 8000);
    }
  }
}

// Listen for showToast events from HX-Trigger
document.addEventListener('showToast', function(event) {
  if (typeof showToast === 'function') {
    const detail = event.detail || {};
    showToast(
      detail.message || 'Operation completed',
      detail.type || 'info',
      detail.title || null,
      detail.delay || 5000
    );
  }
});


// Export for potential external use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    handleFormResponse
  };
}
