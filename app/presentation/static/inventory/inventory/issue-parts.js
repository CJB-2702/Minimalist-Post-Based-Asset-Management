/**
 * Issue Parts Page JavaScript
 * Handles queue management and demand linking for part issuing
 */

// Global queue manager instance
let issueQueueManager;

// Track current events for demand lookups
let currentEvents = [];

// Helper functions for HTMX
function getSelectedPartId() {
    return issueQueueManager?.selectedItem?.part_id || null;
}

function getSelectedInventoryId() {
    return issueQueueManager?.selectedItem?.inventory_id || null;
}

// Show toast notification
function showToast(message, isSuccess = true) {
    const alertClass = isSuccess ? 'alert-success' : 'alert-danger';
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${alertClass} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

// Clear filter inputs
function clearFilters() {
    const filterIds = [
        'filterAssetId',
        'filterAssignedUserId',
        'filterMajorLocationId',
        'filterAssetTypeId',
        'filterMake',
        'filterModel',
        'filterCreatedFrom',
        'filterCreatedTo'
    ];
    filterIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
}

// Link demand to queue item
function linkDemandToQueueItem(demandId, requiredQuantity) {
    if (!issueQueueManager || !issueQueueManager.selectedItem) {
        showToast('Please select a queue item first', false);
        return;
    }
    
    const item = issueQueueManager.selectedItem;
    
    // Validate available stock
    if (requiredQuantity > item.available_qty) {
        showToast(`Insufficient stock! Required: ${requiredQuantity.toFixed(2)}, Available: ${item.available_qty.toFixed(2)}`, false);
        return;
    }
    
    // Link the demand
    const success = issueQueueManager.linkToDemand(item.inventory_id, demandId, requiredQuantity);
    
    if (success) {
        showToast(`Linked demand #${demandId} to queue item. Quantity set to ${requiredQuantity.toFixed(2)}`, true);
    } else {
        showToast('Error linking demand', false);
    }
}

// Update selected queue item summary
function updateSelectedQueueItemSummary() {
    const textEl = document.getElementById('selectedQueueItemText');
    const clearBtn = document.getElementById('clearSelectedQueueItemBtn');
    const selectedPartIdText = document.getElementById('selectedPartIdText');
    
    if (!issueQueueManager || !issueQueueManager.selectedItem) {
        if (textEl) {
            textEl.textContent = 'None selected. Click a queue item above to link to part demands.';
        }
        if (clearBtn) {
            clearBtn.disabled = true;
        }
        if (selectedPartIdText) {
            selectedPartIdText.textContent = 'None selected';
        }
        
        // Load events and demands with no selection
        loadMaintenanceEvents();
        loadPartDemands();
        return;
    }
    
    const item = issueQueueManager.selectedItem;
    if (textEl) {
        textEl.textContent = `${item.part_number} - Qty: ${item.quantity}`;
    }
    if (clearBtn) {
        clearBtn.disabled = false;
    }
    if (selectedPartIdText) {
        selectedPartIdText.textContent = item.part_number || item.part_id;
    }
    
    // Load events and demands for selected item
    loadMaintenanceEvents();
    loadPartDemands();
}

// Build query parameters for events API
function buildEventsQueryParams() {
    const params = new URLSearchParams();
    const selectedPartId = getSelectedPartId();
    if (selectedPartId) params.set('part_id', selectedPartId);

    const assetId = document.getElementById('filterAssetId')?.value;
    const assignedUserId = document.getElementById('filterAssignedUserId')?.value;
    const majorLocationId = document.getElementById('filterMajorLocationId')?.value;
    const assetTypeId = document.getElementById('filterAssetTypeId')?.value;
    const make = document.getElementById('filterMake')?.value;
    const model = document.getElementById('filterModel')?.value;
    const createdFrom = document.getElementById('filterCreatedFrom')?.value;
    const createdTo = document.getElementById('filterCreatedTo')?.value;

    if (assetId) params.set('asset_id', assetId);
    if (assignedUserId) params.set('assigned_user_id', assignedUserId);
    if (majorLocationId) params.set('major_location_id', majorLocationId);
    if (assetTypeId) params.set('asset_type_id', assetTypeId);
    if (make) params.set('make', make);
    if (model) params.set('model', model);
    if (createdFrom) params.set('created_from', createdFrom);
    if (createdTo) params.set('created_to', createdTo);

    return params;
}

// Load maintenance events with unlinked demands
function loadMaintenanceEvents() {
    const eventsList = document.getElementById('maintenance-events-list');
    const demandsList = document.getElementById('event-demands-list');
    const selectedPartId = getSelectedPartId();
    
    if (!selectedPartId) {
        eventsList.innerHTML = '<div class="list-group-item"><p class="text-muted mb-0"><i class="bi bi-arrow-up"></i> Select a queue item above to load matching maintenance events</p></div>';
        demandsList.innerHTML = '<div class="list-group-item"><p class="text-muted mb-0"><i class="bi bi-info-circle"></i> Select a maintenance event to view its part demands</p></div>';
        return;
    }
    
    eventsList.innerHTML = '<div class="list-group-item"><p class="text-muted mb-0"><i class="bi bi-hourglass-split"></i> Loading...</p></div>';

    const params = buildEventsQueryParams();
    fetch(`/inventory/issue-parts/api/events?${params.toString()}`)
        .then(r => r.json())
        .then(events => {
            currentEvents = events;
            
            if (events.length === 0) {
                eventsList.innerHTML = '<div class="list-group-item"><p class="text-muted mb-0">No maintenance events with unlinked demands for this part.</p></div>';
                return;
            }
            
            let html = '';
            events.forEach(ev => {
                html += `
                    <a href="#" class="list-group-item list-group-item-action event-item" data-event-id="${ev.event_id}">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">${ev.task_name}</h6>
                                <small class="text-muted">Asset: ${ev.asset_name || 'N/A'}</small><br>
                                <small class="text-muted">Start: ${ev.planned_start || 'TBD'}</small>
                            </div>
                            <div class="text-end">
                                <span class="badge bg-warning">${ev.status}</span><br>
                                <small class="text-muted">${ev.demands.length} demands</small>
                            </div>
                        </div>
                    </a>
                `;
            });
            
            eventsList.innerHTML = html;
            
            // Add click handlers
            document.querySelectorAll('.event-item').forEach(item => {
                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    const eventId = parseInt(this.dataset.eventId);
                    loadEventDemands(eventId);
                });
            });
        })
        .catch(err => {
            console.error('Failed to load events:', err);
            eventsList.innerHTML = '<div class="list-group-item"><p class="text-danger mb-0">Error loading events</p></div>';
        });
}

// Load demands for selected event
function loadEventDemands(eventId) {
    const demandsList = document.getElementById('event-demands-list');
    const event = currentEvents.find(e => e.event_id === eventId);
    
    if (!event || event.demands.length === 0) {
        demandsList.innerHTML = '<div class="list-group-item"><p class="text-muted mb-0">No demands found for this event</p></div>';
        return;
    }
    
    let html = '';
    event.demands.forEach(d => {
        html += `
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${d.part_number} - ${d.part_name}</h6>
                        <small class="text-muted">Action: ${d.action_name}</small><br>
                        <small class="text-muted">Required: ${d.quantity_required}</small>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-${d.status === 'Approved' ? 'warning' : 'secondary'}">${d.status}</span><br>
                        <span class="badge bg-info">${d.priority}</span>
                    </div>
                </div>
                <div class="mt-2">
                    <button class="btn btn-sm btn-success tool-link-btn" data-demand-id="${d.id}" data-qty="${d.quantity_required}">
                        <i class="bi bi-link-45deg"></i> Link to queue item
                    </button>
                </div>
            </div>
        `;
    });
    
    demandsList.innerHTML = html;
    
    // Add click handlers
    document.querySelectorAll('.tool-link-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const demandId = parseInt(this.dataset.demandId);
            const qty = parseFloat(this.dataset.qty);
            linkDemandToQueueItem(demandId, qty);
        });
    });
}

// Load all demands for selected part (tab 2)
function loadPartDemands() {
    const demandsList = document.getElementById('part-demands-list');
    const partTextEl = document.getElementById('selectedPartIdText');
    const selectedPartId = getSelectedPartId();
    
    if (!selectedPartId) {
        demandsList.innerHTML = '<div class="list-group-item"><p class="text-muted mb-0"><i class="bi bi-arrow-up"></i> Select a queue item above to view unlinked demands for that part</p></div>';
        if (partTextEl) partTextEl.textContent = 'None selected';
        return;
    }
    
    demandsList.innerHTML = '<div class="list-group-item"><p class="text-muted mb-0"><i class="bi bi-hourglass-split"></i> Loading...</p></div>';

    fetch(`/inventory/issue-parts/api/demands?part_id=${selectedPartId}`)
        .then(r => r.json())
        .then(demands => {
            if (demands.length === 0) {
                demandsList.innerHTML = '<div class="list-group-item"><p class="text-muted mb-0">No unlinked demands for this part.</p></div>';
                return;
            }
            
            let html = '';
            demands.forEach(d => {
                html += `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">Demand #${d.id} - ${d.event_name}</h6>
                                <small class="text-muted">Action: ${d.action_name}</small><br>
                                <small class="text-muted">Required: ${d.quantity_required}</small>
                            </div>
                            <span class="badge bg-${d.status === 'Approved' ? 'warning' : 'secondary'}">${d.status}</span>
                        </div>
                        <div class="mt-2">
                            <button class="btn btn-sm btn-success tool-link-btn" data-demand-id="${d.id}" data-qty="${d.quantity_required}">
                                <i class="bi bi-link-45deg"></i> Link to queue item
                            </button>
                        </div>
                    </div>
                `;
            });
            
            demandsList.innerHTML = html;
            
            // Add click handlers
            document.querySelectorAll('.tool-link-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const demandId = parseInt(this.dataset.demandId);
                    const qty = parseFloat(this.dataset.qty);
                    linkDemandToQueueItem(demandId, qty);
                });
            });
        })
        .catch(err => {
            console.error('Failed to load demands:', err);
            demandsList.innerHTML = '<div class="list-group-item"><p class="text-danger mb-0">Error loading demands</p></div>';
        });
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    // Set default date issued to now
    const dateIssuedInput = document.getElementById('date_issued');
    if (dateIssuedInput) {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        dateIssuedInput.value = `${year}-${month}-${day}T${hours}:${minutes}`;
    }
    
    // Initialize QueueManager
    issueQueueManager = new QueueManager({
        queueContainerId: 'issue-queue',
        queueCountId: 'queue-count',
        submitButtonId: 'submit-btn',
        hiddenInputId: 'queue_data',
        emptyMessage: 'No items in queue. Check boxes to add items.',
        onSelect: function(item) {
            updateSelectedQueueItemSummary();
        },
        onRemove: function(item) {
            // Uncheck the checkbox when item is removed (unless already unchecked)
            const checkbox = document.querySelector(`.inventory-checkbox[data-inventory-id="${item.inventory_id}"]`);
            if (checkbox && checkbox.checked) {
                checkbox.checked = false;
            }
        },
        onUpdate: function(item, oldQuantity) {
            // Show toast if quantity was updated
            showToast(`Updated quantity for ${item.part_number} to ${item.quantity.toFixed(2)}`, true);
        },
        itemTemplate: function(item, selectedItem) {
            const isSelected = selectedItem?.inventory_id === item.inventory_id;
            const hasLinkedDemand = item.part_demand_id ? 'linked-demand' : '';
            const selectedClass = isSelected ? 'selected-item' : '';
            
            return `
                <div class="queue-item clickable-queue-item ${selectedClass} ${hasLinkedDemand}" 
                     data-inventory-id="${item.inventory_id}" 
                     data-part-id="${item.part_id}"
                     data-part-number="${item.part_number}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <strong>${item.part_number}</strong><br>
                            <small class="text-muted">${item.part_name || ''}</small><br>
                            <small class="text-muted">${item.storeroom_name || ''}</small>
                            <div class="mt-2 d-flex align-items-center gap-2">
                                <label class="form-label small mb-0">Quantity:</label>
                                <input type="number" 
                                       class="form-control form-control-sm queue-qty-input" 
                                       data-inventory-id="${item.inventory_id}"
                                       min="0.01" 
                                       max="${item.available_qty}" 
                                       step="0.01" 
                                       value="${item.quantity.toFixed(2)}"
                                       ${item.locked ? 'readonly' : ''}
                                       style="width: 100px;"
                                       onclick="event.stopPropagation();">
                                <small class="text-muted">(Available: ${item.available_qty.toFixed(2)})</small>
                                ${item.locked ? '<small class="text-success"><i class="bi bi-lock"></i> Locked to demand</small>' : ''}
                            </div>
                            ${item.part_demand_id ? `<br><span class="badge bg-success mt-1"><i class="bi bi-link-45deg"></i> Linked to Demand #${item.part_demand_id}</span>` : ''}
                        </div>
                        <button type="button" class="btn btn-sm btn-danger queue-remove-btn" 
                                data-inventory-id="${item.inventory_id}"
                                onclick="event.stopPropagation();">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                </div>
            `;
        }
    });
    
    // Handle inventory checkbox changes
    document.querySelectorAll('.inventory-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const inventoryId = this.dataset.inventoryId;
            
            if (this.checked) {
                // Add to queue
                const item = {
                    inventory_id: inventoryId,
                    part_id: this.dataset.partId,
                    part_number: this.dataset.partNumber,
                    part_name: this.dataset.partName,
                    quantity: 1.00,
                    available_qty: parseFloat(this.dataset.availableQty),
                    storeroom_id: this.dataset.storeroomId,
                    storeroom_name: this.dataset.storeroomName,
                    major_location_id: this.dataset.majorLocationId,
                    location_id: this.dataset.locationId || null,
                    bin_id: this.dataset.binId || null
                };
                issueQueueManager.add(item);
            } else {
                // Remove from queue
                issueQueueManager.remove(inventoryId);
            }
        });
    });
    
    // Handle clear selection button
    const clearSelectedBtn = document.getElementById('clearSelectedQueueItemBtn');
    if (clearSelectedBtn) {
        clearSelectedBtn.addEventListener('click', function() {
            issueQueueManager.clearSelection();
            updateSelectedQueueItemSummary();
        });
    }
    
    // Handle filter buttons
    const applyFiltersBtn = document.getElementById('applyEventFiltersBtn');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', function() {
            loadMaintenanceEvents();
            loadPartDemands();
        });
    }
    
    // Handle clear filters button
    const clearFiltersBtn = document.getElementById('clearEventFiltersBtn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            clearFilters();
            loadMaintenanceEvents();
            loadPartDemands();
        });
    }
    
    // Form validation
    const issueForm = document.getElementById('issue-form');
    if (issueForm) {
        issueForm.addEventListener('submit', function(e) {
            if (!issueQueueManager || issueQueueManager.count() === 0) {
                e.preventDefault();
                showToast('Please add at least one item to the issue queue.', false);
                return false;
            }
        });
    }
    
    // Initial render
    issueQueueManager.render();
    updateSelectedQueueItemSummary();
});

