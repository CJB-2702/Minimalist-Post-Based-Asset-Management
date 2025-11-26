// Asset Management System - Base JavaScript

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss removed - alerts now require manual dismissal by clicking X button
    // Users must click the close button to dismiss flash messages

    // HTMX event handlers
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        // Show loading indicator
        var target = evt.target;
        if (target.classList.contains('btn')) {
            target.disabled = true;
            target.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
        }
    });

    document.body.addEventListener('htmx:afterRequest', function(evt) {
        // Reset button state
        var target = evt.target;
        if (target.classList.contains('btn')) {
            target.disabled = false;
            // Reset button text based on original content
            var originalText = target.getAttribute('data-original-text');
            if (originalText) {
                target.innerHTML = originalText;
            }
        }
    });

    // Store original button text for HTMX requests
    document.querySelectorAll('.btn').forEach(function(btn) {
        btn.setAttribute('data-original-text', btn.innerHTML);
    });

    // Instant modal functionality - remove transitions
    var assetManagementModal = document.getElementById('assetManagementModal');
    if (assetManagementModal) {
        // Remove fade class to disable transitions
        assetManagementModal.classList.remove('fade');
        
        // Override Bootstrap modal show/hide to be instant
        assetManagementModal.addEventListener('show.bs.modal', function() {
            this.style.display = 'block';
            this.classList.add('show');
            document.body.classList.add('modal-open');
            
            // Create backdrop instantly
            var backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop show';
            backdrop.id = 'assetManagementModalBackdrop';
            document.body.appendChild(backdrop);
        });
        
        assetManagementModal.addEventListener('hide.bs.modal', function() {
            this.style.display = 'none';
            this.classList.remove('show');
            document.body.classList.remove('modal-open');
            
            // Remove backdrop instantly
            var backdrop = document.getElementById('assetManagementModalBackdrop');
            if (backdrop) {
                backdrop.remove();
            }
        });
    }

    // Instant modal functionality for Maintenance Modal
    var maintenanceModal = document.getElementById('maintenanceModal');
    if (maintenanceModal) {
        // Remove fade class to disable transitions
        maintenanceModal.classList.remove('fade');
        
        // Override Bootstrap modal show/hide to be instant
        maintenanceModal.addEventListener('show.bs.modal', function() {
            this.style.display = 'block';
            this.classList.add('show');
            document.body.classList.add('modal-open');
            
            // Create backdrop instantly
            var backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop show';
            backdrop.id = 'maintenanceModalBackdrop';
            document.body.appendChild(backdrop);
        });
        
        maintenanceModal.addEventListener('hide.bs.modal', function() {
            this.style.display = 'none';
            this.classList.remove('show');
            document.body.classList.remove('modal-open');
            
            // Remove backdrop instantly
            var backdrop = document.getElementById('maintenanceModalBackdrop');
            if (backdrop) {
                backdrop.remove();
            }
        });
    }

    // Handle maintenance search form
    const maintenanceSearchForm = document.getElementById('maintenanceSearchForm');
    if (maintenanceSearchForm) {
        maintenanceSearchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const assetId = document.getElementById('searchAssetId').value.trim();
            const location = document.getElementById('searchLocation').value.trim();
            
            // Build the URL with query parameters
            const params = new URLSearchParams();
            
            if (assetId) {
                params.append('asset_id', assetId);
            }
            
            if (location) {
                params.append('location', location);
            }
            
            // Redirect to maintenance action sets list with filters
            const url = `/maintenance/maintenance-action-sets${params.toString() ? '?' + params.toString() : ''}`;
            window.location.href = url;
        });
    }
});

// Utility functions
window.AMS = {
    // Show confirmation dialog
    confirm: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    },

    // Show loading state
    showLoading: function(element) {
        element.classList.add('loading');
    },

    // Hide loading state
    hideLoading: function(element) {
        element.classList.remove('loading');
    },

    // Format date
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString();
    },

    // Format currency
    formatCurrency: function(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    },

    // Validate form
    validateForm: function(form) {
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;

        inputs.forEach(function(input) {
            if (!input.value.trim()) {
                input.classList.add('is-invalid');
                isValid = false;
            } else {
                input.classList.remove('is-invalid');
            }
        });

        return isValid;
    },

    // Auto-save form data
    autoSave: function(form, key) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        localStorage.setItem(key, JSON.stringify(data));
    },

    // Restore form data
    restoreForm: function(form, key) {
        const saved = localStorage.getItem(key);
        if (saved) {
            const data = JSON.parse(saved);
            for (let key in data) {
                const input = form.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = data[key];
                }
            }
        }
    },

    // Clear saved form data
    clearSavedForm: function(key) {
        localStorage.removeItem(key);
    }
};

// HTMX extensions
htmx.defineExtension('loading-states', {
    onEvent: function(name, evt) {
        if (name === "htmx:beforeRequest") {
            evt.target.classList.add('htmx-request');
        } else if (name === "htmx:afterRequest") {
            evt.target.classList.remove('htmx-request');
        }
    }
});

// Alpine.js components
document.addEventListener('alpine:init', () => {
    Alpine.data('searchForm', () => ({
        query: '',
        filters: {},
        
        init() {
            // Restore search state from URL
            const urlParams = new URLSearchParams(window.location.search);
            this.query = urlParams.get('q') || '';
            
            // Restore filters
            urlParams.forEach((value, key) => {
                if (key !== 'q' && key !== 'page') {
                    this.filters[key] = value;
                }
            });
        },
        
        updateFilters() {
            // Update URL with current filters
            const url = new URL(window.location);
            url.searchParams.set('q', this.query);
            
            Object.keys(this.filters).forEach(key => {
                if (this.filters[key]) {
                    url.searchParams.set(key, this.filters[key]);
                } else {
                    url.searchParams.delete(key);
                }
            });
            
            // Reset to page 1 when filters change
            url.searchParams.delete('page');
            
            window.location.href = url.toString();
        },
        
        clearFilters() {
            this.query = '';
            this.filters = {};
            window.location.href = window.location.pathname;
        }
    }));
    
    Alpine.data('tableSort', () => ({
        sortColumn: '',
        sortDirection: 'asc',
        
        sort(column) {
            if (this.sortColumn === column) {
                this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                this.sortColumn = column;
                this.sortDirection = 'asc';
            }
            
            // Update URL with sort parameters
            const url = new URL(window.location);
            url.searchParams.set('sort', column);
            url.searchParams.set('direction', this.sortDirection);
            window.location.href = url.toString();
        }
    }));
}); 