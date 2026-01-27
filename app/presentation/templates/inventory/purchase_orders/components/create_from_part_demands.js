/**
 * JavaScript for Create PO from Part Demands page
 * Handles parts summary item management and form submission
 */

// Array of selected part demand IDs (injected from template)
const selectedDemandIds = window.SELECTED_DEMAND_IDS || [];

// PartsSummaryItem class to encapsulate part-related operations
class PartsSummaryItem {
  constructor(cardElement) {
    this.card = cardElement;
    this.partId = parseInt(cardElement.dataset.partId);
    this.minQuantity = parseFloat(cardElement.dataset.minQuantity) || 0;
    this.defaultUnitCost = parseFloat(cardElement.dataset.defaultUnitCost) || 0;
    
    // Flag to prevent infinite loops when programmatically updating values
    this._updatingValue = false;
    
    // Parse linked demands from data attribute (using single quotes in HTML allows double quotes in JSON)
    try {
      const linkedDemandsStr = cardElement.dataset.linkedDemands || cardElement.getAttribute('data-linked-demands') || '[]';
      if (linkedDemandsStr && linkedDemandsStr.trim()) {
        this.linkedDemands = JSON.parse(linkedDemandsStr);
      } else {
        this.linkedDemands = [];
      }
    } catch (e) {
      console.error('Error parsing linked demands:', e);
      console.error('Raw attribute value:', cardElement.getAttribute('data-linked-demands'));
      this.linkedDemands = [];
    }
    
    // Cache DOM elements
    this.quantityInput = cardElement.querySelector('.quantity-input');
    this.unitCostInput = cardElement.querySelector('.unit-cost-input');
    this.totalCostDisplay = cardElement.querySelector('[data-total-cost]');
    this.confirmCheckbox = cardElement.querySelector('[name^="confirm_price_part_"]');
    this.minQuantityHelp = cardElement.querySelector('[data-min-quantity-help]');
    
    this.init();
  }
  
  init() {
    if (!this.quantityInput || !this.unitCostInput || !this.totalCostDisplay) {
      console.error('PartsSummaryItem: Required DOM elements not found for part', this.partId);
      return;
    }
    
    // Store bound handlers for cleanup
    this._quantityInputHandler = () => this.handleQuantityChange();
    this._quantityChangeHandler = () => this.handleQuantityChange();
    this._unitCostInputHandler = () => this.updateTotalCost();
    this._unitCostChangeHandler = () => this.updateTotalCost();
    
    // For unlinked parts, minimum is 0.01, not the minQuantity
    const isUnlinked = this.card.dataset.isUnlinked === 'true';
    const effectiveMin = isUnlinked ? 0.01 : this.minQuantity;
    
    // Ensure quantity is at least minimum on initialization
    // Use flag to prevent triggering events during initialization
    const currentValue = parseFloat(this.quantityInput.value) || 0;
    if (currentValue < effectiveMin) {
      this._updatingValue = true;
      this.quantityInput.value = effectiveMin;
      this._updatingValue = false;
    }
    
    // Set up event listeners
    this.quantityInput.addEventListener('input', this._quantityInputHandler);
    this.quantityInput.addEventListener('change', this._quantityChangeHandler);
    
    this.unitCostInput.addEventListener('input', this._unitCostInputHandler);
    this.unitCostInput.addEventListener('change', this._unitCostChangeHandler);
    
    // Calculate initial total cost
    this.updateTotalCost();
  }
  
  // Cleanup method to remove event listeners
  destroy() {
    if (this.quantityInput) {
      if (this._quantityInputHandler) {
        this.quantityInput.removeEventListener('input', this._quantityInputHandler);
      }
      if (this._quantityChangeHandler) {
        this.quantityInput.removeEventListener('change', this._quantityChangeHandler);
      }
    }
    if (this.unitCostInput) {
      if (this._unitCostInputHandler) {
        this.unitCostInput.removeEventListener('input', this._unitCostInputHandler);
      }
      if (this._unitCostChangeHandler) {
        this.unitCostInput.removeEventListener('change', this._unitCostChangeHandler);
      }
    }
  }
  
  handleQuantityChange() {
    // Prevent infinite loops from programmatic value changes
    if (this._updatingValue) {
      return;
    }
    
    const value = parseFloat(this.quantityInput.value) || 0;
    const min = parseFloat(this.quantityInput.getAttribute('min')) || 0;
    const isUnlinked = this.card.dataset.isUnlinked === 'true';
    
    // Validate minimum
    if (value < min) {
      if (isUnlinked) {
        this.quantityInput.setCustomValidity(`Quantity must be at least ${min}`);
      } else {
        this.quantityInput.setCustomValidity(`Quantity must be at least ${min} (sum of part demands)`);
      }
      
      // Enforce minimum on change - use flag to prevent recursive calls
      this._updatingValue = true;
      this.quantityInput.value = min;
      this._updatingValue = false;
    } else {
      this.quantityInput.setCustomValidity('');
    }
    
    this.updateTotalCost();
  }
  
  updateTotalCost() {
    const quantity = parseFloat(this.quantityInput.value) || 0;
    const unitCost = parseFloat(this.unitCostInput.value) || 0;
    const totalCost = quantity * unitCost;
    
    if (this.totalCostDisplay) {
      this.totalCostDisplay.textContent = '$' + totalCost.toFixed(2);
    }
  }
  
  updateQuantityMinimum(newMinimum) {
    if (!this.quantityInput) return;
    
    const currentValue = parseFloat(this.quantityInput.value) || 0;
    this.minQuantity = newMinimum;
    this.quantityInput.setAttribute('min', newMinimum);
    this.quantityInput.setAttribute('data-min-qty', newMinimum);
    this.card.setAttribute('data-min-quantity', newMinimum);
    
    // Update the help text
    if (this.minQuantityHelp) {
      this.minQuantityHelp.textContent = 'Min: ' + newMinimum;
    }
    
    // If current value is less than new minimum, update it
    if (currentValue < newMinimum) {
      this.quantityInput.value = newMinimum;
      this.quantityInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    // Recalculate total cost
    this.updateTotalCost();
  }
  
  recalculateMinimum() {
    // Find the part demands table within this card
    const details = this.card.querySelector('details');
    if (!details) return this.minQuantity;
    
    const table = details.querySelector('table');
    if (!table) return this.minQuantity;
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return this.minQuantity;
    
    // Sum all quantities from the table
    let total = 0;
    const rows = tbody.querySelectorAll('tr');
    rows.forEach(row => {
      const qtyCell = row.cells[1]; // Quantity is in the second column (index 1)
      if (qtyCell) {
        const qty = parseFloat(qtyCell.textContent.trim()) || 0;
        total += qty;
      }
    });
    
    if (total > 0) {
      this.updateQuantityMinimum(total);
    }
    
    return total;
  }
  
  validate() {
    const quantity = parseFloat(this.quantityInput.value) || 0;
    const unitCost = parseFloat(this.unitCostInput.value) || 0;
    const confirmed = this.confirmCheckbox ? this.confirmCheckbox.checked : false;
    
    const errors = [];
    
    if (quantity < this.minQuantity) {
      errors.push(`Quantity must be at least ${this.minQuantity}`);
    }
    
    if (unitCost < 0) {
      errors.push('Unit cost cannot be negative');
    }
    
    if (!confirmed) {
      errors.push('Price confirmation is required');
    }
    
    return {
      valid: errors.length === 0,
      errors: errors
    };
  }
  
  getSubmissionData() {
    const quantity = parseFloat(this.quantityInput.value) || 0;
    const unitCost = parseFloat(this.unitCostInput.value) || 0;
    const confirmed = this.confirmCheckbox ? this.confirmCheckbox.checked : false;
    const isUnlinked = this.card.dataset.isUnlinked === 'true';
    
    // Build linked demands array
    const linkedDemands = [];
    if (!isUnlinked && this.linkedDemands && this.linkedDemands.length > 0) {
      this.linkedDemands.forEach(demand => {
        // For now, allocate full quantity required (can be enhanced later for partial allocation)
        linkedDemands.push({
          part_demand_id: demand.part_demand_id,
          quantity_allocated: demand.quantity_required
        });
      });
    }
    
    // Calculate unlinked quantity
    const linkedQtySum = linkedDemands.reduce((sum, d) => sum + d.quantity_allocated, 0);
    const unlinkedQuantity = Math.max(0, quantity - linkedQtySum);
    
    return {
      part_id: this.partId,
      quantity: quantity,
      unit_cost: unitCost,
      linked_demands: linkedDemands,
      unlinked_quantity: unlinkedQuantity,
      confirmed: confirmed
    };
  }
}

// Validate PO Header fields before submission
function validatePOHeaderFields() {
  const vendorName = document.getElementById('vendor_name');
  const locationId = document.getElementById('location_id');
  
  if (!vendorName || !vendorName.value.trim()) {
    alert('Vendor Name is required');
    if (vendorName) vendorName.focus();
    return false;
  }
  
  if (!locationId || !locationId.value) {
    alert('Location is required');
    if (locationId) locationId.focus();
    return false;
  }
  
  return true;
}

// Global map to store PartsSummaryItem instances
const partsSummaryItems = new Map();

// Function to update submit button state based on whether there are parts and required fields
function updateSubmitButtonState() {
  const submitButton = document.getElementById('po-submit-button');
  if (!submitButton) return;
  
  // Find the parts summary form
  const partsSummaryForm = document.getElementById('po-submit-form');
  if (!partsSummaryForm) return;
  
  // Check if there are any part summary items (cards with data-part-id)
  const hasPartCards = partsSummaryForm.querySelectorAll('.card[data-part-id]').length > 0;
  
  // Check if the warning alert is visible (meaning no parts)
  const warningAlert = partsSummaryForm.querySelector('.alert-warning');
  const hasNoPartsWarning = warningAlert && warningAlert.offsetParent !== null;
  
  // Check required header fields
  const vendorName = document.getElementById('vendor_name');
  const locationId = document.getElementById('location_id');
  
  const hasVendorName = vendorName && vendorName.value.trim() !== '';
  const hasLocationId = locationId && locationId.value !== '';
  
  // Enable button if we have parts AND required fields are filled
  const shouldEnable = hasPartCards && !hasNoPartsWarning && hasVendorName && hasLocationId;
  submitButton.disabled = !shouldEnable;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  // Initialize PartsSummaryItem instances from card elements
  document.querySelectorAll('.card[data-part-id]').forEach(card => {
    const item = new PartsSummaryItem(card);
    partsSummaryItems.set(item.partId, item);
  });
  
  // Update submit button state on initial load
  updateSubmitButtonState();
  
  // Add event listeners to required header fields
  const vendorName = document.getElementById('vendor_name');
  const locationId = document.getElementById('location_id');
  
  if (vendorName) {
    vendorName.addEventListener('input', updateSubmitButtonState);
    vendorName.addEventListener('change', updateSubmitButtonState);
  }
  
  if (locationId) {
    locationId.addEventListener('change', updateSubmitButtonState);
  }
  
  // Watch for changes in the parts summary form using MutationObserver
  const partsSummaryForm = document.getElementById('po-submit-form');
  if (partsSummaryForm) {
    let updateTimeout = null;
    const observer = new MutationObserver(function(mutations) {
      // Check if any part cards were added or removed
      const hasNodeChanges = mutations.some(mutation => {
        return mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0;
      });
      
      if (hasNodeChanges) {
        // Clear any pending updates
        if (updateTimeout) {
          clearTimeout(updateTimeout);
        }
        
        // Debounce the reinitialization to avoid excessive calls
        updateTimeout = setTimeout(() => {
          // Clean up old instances before creating new ones
          partsSummaryItems.forEach(item => {
            if (item.destroy) {
              item.destroy();
            }
          });
          partsSummaryItems.clear();
          
          // Reinitialize parts summary items
          document.querySelectorAll('.card[data-part-id]').forEach(card => {
            const item = new PartsSummaryItem(card);
            partsSummaryItems.set(item.partId, item);
          });
          updateSubmitButtonState();
        }, 100);
      }
      // Don't call updateSubmitButtonState for attribute-only changes to avoid excessive calls
    });
    
    // Start observing the form for changes - only watch for node changes, not attributes
    observer.observe(partsSummaryForm, {
      childList: true,
      subtree: true
      // Removed attributes watching to reduce excessive calls
    });
  }
  
  // Listen for HTMX events to update button state when parts summary changes
  if (typeof htmx !== 'undefined') {
    document.body.addEventListener('htmx:afterSwap', function(event) {
      // Check if the parts summary section was updated
      const target = event.detail.target;
      if (target.id === 'parts-summary' || 
          target.id === 'po-submit-form' ||
          target.closest('#po-submit-form')) {
        // Clean up old instances before creating new ones
        partsSummaryItems.forEach(item => {
          if (item.destroy) {
            item.destroy();
          }
        });
        partsSummaryItems.clear();
        
        // Reinitialize parts summary items
        document.querySelectorAll('.card[data-part-id]').forEach(card => {
          const item = new PartsSummaryItem(card);
          partsSummaryItems.set(item.partId, item);
        });
        updateSubmitButtonState();
      }
    });
    
    // Also listen for afterSettle in case the swap doesn't trigger
    document.body.addEventListener('htmx:afterSettle', function(event) {
      const target = event.detail.target;
      if (target.id === 'parts-summary' || 
          target.id === 'po-submit-form' ||
          target.closest('#po-submit-form')) {
        updateSubmitButtonState();
      }
    });
  }
  
  // Build JSON schema from form data using PartsSummaryItem instances
  function buildSubmissionSchema() {
    // Get header data
    const header = {
      vendor_name: document.getElementById('vendor_name')?.value?.trim() || '',
      vendor_contact: document.getElementById('vendor_contact')?.value?.trim() || null,
      location_id: parseInt(document.getElementById('location_id')?.value) || null,
      storeroom_id: parseInt(document.getElementById('storeroom_id')?.value) || null,
      shipping_cost: parseFloat(document.getElementById('shipping_cost')?.value) || 0.0,
      tax_amount: parseFloat(document.getElementById('tax_amount')?.value) || 0.0,
      other_amount: parseFloat(document.getElementById('other_amount')?.value) || 0.0,
      notes: document.getElementById('notes')?.value?.trim() || null
    };
    
    // Build line items from PartsSummaryItem instances
    const lineItems = [];
    partsSummaryItems.forEach(item => {
      lineItems.push(item.getSubmissionData());
    });
    
    return {
      header: header,
      line_items: lineItems
    };
  }
  
  // Handle form submission with JSON
  const poSubmitForm = document.getElementById('po-submit-form');
  if (poSubmitForm) {
    poSubmitForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      if (!validatePOHeaderFields()) {
        return false;
      }
      
      // Build JSON schema
      const submissionData = buildSubmissionSchema();
      
      // Show loading state
      const submitButton = poSubmitForm.querySelector('button[type="submit"]');
      const originalButtonText = submitButton.innerHTML;
      submitButton.disabled = true;
      submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Submitting...';
      
      // Submit as JSON
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
      fetch(poSubmitForm.action, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(submissionData)
      })
      .then(response => {
        // Check if response is ok (status 200-299)
        if (!response.ok) {
          // Try to parse error response
          return response.json().then(data => {
            throw { status: response.status, data: data };
          }).catch(() => {
            throw { status: response.status, data: { message: `HTTP ${response.status}: ${response.statusText}` } };
          });
        }
        return response.json();
      })
      .then(data => {
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
        
        if (data.success === true) {
          // Show success message
          if (typeof showToast === 'function') {
            showToast(
              data.message || `Purchase order ${data.po_number} created successfully`,
              'success',
              'Purchase Order Created',
              5000
            );
          } else {
            alert(data.message || `Purchase order ${data.po_number} created successfully`);
          }
          
          // Redirect to PO view page
          if (data.redirect_url) {
            setTimeout(() => {
              window.location.href = data.redirect_url;
            }, 1000);
          }
        } else {
          // Show error message
          if (typeof showToast === 'function') {
            showToast(
              data.message || 'An error occurred while creating the purchase order.',
              'error',
              'Submission Error',
              8000
            );
          } else {
            alert(data.message || 'An error occurred while creating the purchase order.');
          }
        }
      })
      .catch(error => {
        console.error('Error submitting form:', error);
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
        
        const errorMessage = error.data?.message || error.message || 'An error occurred while submitting the form.';
        
        if (typeof showToast === 'function') {
          showToast(
            errorMessage,
            'error',
            'Submission Error',
            8000
          );
        } else {
          alert(errorMessage);
        }
      });
      
      return false;
    });
  }
});

// Export for potential external use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    PartsSummaryItem,
    validatePOHeaderFields,
    partsSummaryItems,
    updateSubmitButtonState
  };
}

// Make updateSubmitButtonState available globally
window.updateSubmitButtonState = updateSubmitButtonState;
