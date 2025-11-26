// Error Suppression Script
// This script disables all error popups and notifications throughout the application

(function() {
    'use strict';
    
    // Disable browser's default error popups
    window.onerror = function(message, source, lineno, colno, error) {
        console.log('Error suppressed:', message, 'at', source, 'line', lineno);
        return true; // Prevent default error handling
    };
    
    // Disable unhandled promise rejection popups
    window.addEventListener('unhandledrejection', function(event) {
        console.log('Unhandled promise rejection suppressed:', event.reason);
        event.preventDefault(); // Prevent default error handling
    });
    
    // Override console.error to prevent error popups
    const originalConsoleError = console.error;
    console.error = function(...args) {
        // Log to console but don't show popups
        originalConsoleError.apply(console, args);
    };
    
    // Disable Bootstrap error popups
    if (typeof bootstrap !== 'undefined') {
        // Override Bootstrap's error handling
        const originalAlert = bootstrap.Alert;
        if (originalAlert) {
            bootstrap.Alert = function(element, config) {
                // Only show non-error alerts
                if (element && element.classList.contains('alert-danger')) {
                    console.log('Bootstrap error alert suppressed');
                    return null;
                }
                return new originalAlert(element, config);
            };
        }
        
        // Disable Bootstrap toast error notifications
        const originalToast = bootstrap.Toast;
        if (originalToast) {
            bootstrap.Toast = function(element, config) {
                // Only show non-error toasts
                if (element && element.classList.contains('bg-danger')) {
                    console.log('Bootstrap error toast suppressed');
                    return null;
                }
                return new originalToast(element, config);
            };
        }
    }
    
    // Disable HTMX error popups
    if (typeof htmx !== 'undefined') {
        // Override HTMX error handling
        htmx.on('htmx:responseError', function(evt) {
            console.log('HTMX response error suppressed:', evt.detail);
            evt.preventDefault();
        });
        
        htmx.on('htmx:sendError', function(evt) {
            console.log('HTMX send error suppressed:', evt.detail);
            evt.preventDefault();
        });
        
        htmx.on('htmx:validation:failed', function(evt) {
            console.log('HTMX validation error suppressed:', evt.detail);
            evt.preventDefault();
        });
    }
    
    // Disable Alpine.js error popups
    if (typeof Alpine !== 'undefined') {
        // Override Alpine.js error handling
        Alpine.onError = function(error) {
            console.log('Alpine.js error suppressed:', error);
            return false; // Prevent default error handling
        };
    }
    
    // Disable any custom error popups
    const originalAlert = window.alert;
    window.alert = function(message) {
        // Only allow non-error alerts
        if (typeof message === 'string' && 
            (message.toLowerCase().includes('error') || 
             message.toLowerCase().includes('failed') ||
             message.toLowerCase().includes('exception'))) {
            console.log('Error alert suppressed:', message);
            return;
        }
        return originalAlert.call(this, message);
    };
    
    // Disable any custom confirm dialogs for errors
    const originalConfirm = window.confirm;
    window.confirm = function(message) {
        // Only allow non-error confirms
        if (typeof message === 'string' && 
            (message.toLowerCase().includes('error') || 
             message.toLowerCase().includes('failed') ||
             message.toLowerCase().includes('exception'))) {
            console.log('Error confirm suppressed:', message);
            return false;
        }
        return originalConfirm.call(this, message);
    };
    
    // Remove any existing error popups from the DOM
    function removeErrorPopups() {
        // Remove Bootstrap error alerts
        const errorAlerts = document.querySelectorAll('.alert-danger, .alert.alert-danger');
        errorAlerts.forEach(alert => {
            console.log('Removing error alert:', alert);
            alert.remove();
        });
        
        // Remove error toasts
        const errorToasts = document.querySelectorAll('.toast.bg-danger, .toast.text-danger');
        errorToasts.forEach(toast => {
            console.log('Removing error toast:', toast);
            toast.remove();
        });
        
        // Remove any custom error popups
        const errorPopups = document.querySelectorAll('[class*="error"], [class*="Error"]');
        errorPopups.forEach(popup => {
            if (popup.style.display !== 'none' && 
                (popup.classList.contains('popup') || 
                 popup.classList.contains('modal') ||
                 popup.classList.contains('toast') ||
                 popup.classList.contains('alert'))) {
                console.log('Removing error popup:', popup);
                popup.remove();
            }
        });
    }
    
    // Run immediately
    removeErrorPopups();
    
    // Set up observer to remove error popups as they appear
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        if (node.classList && 
                            (node.classList.contains('alert-danger') ||
                             node.classList.contains('bg-danger') ||
                             node.classList.contains('text-danger'))) {
                            console.log('Removing dynamically added error element:', node);
                            node.remove();
                        }
                    }
                });
            }
        });
    });
    
    // Start observing
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    console.log('Error suppression script loaded - all error popups disabled');
    
})();
