/**
 * QueueManager - Manages a client-side queue of items with CRUD operations
 * and automatic rendering/persistence
 */
class QueueManager {
    constructor(options = {}) {
        this.items = [];
        this.selectedItem = null;
        
        // Configuration
        this.config = {
            queueContainerId: options.queueContainerId || 'issue-queue',
            queueCountId: options.queueCountId || 'queue-count',
            submitButtonId: options.submitButtonId || 'submit-btn',
            hiddenInputId: options.hiddenInputId || 'queue_data',
            emptyMessage: options.emptyMessage || 'No items in queue.',
            maxQuantity: options.maxQuantity || null,
            onRender: options.onRender || null,
            onAdd: options.onAdd || null,
            onRemove: options.onRemove || null,
            onUpdate: options.onUpdate || null,
            onSelect: options.onSelect || null,
            itemTemplate: options.itemTemplate || this.defaultItemTemplate.bind(this)
        };
    }
    
    /**
     * Add item to queue
     * @param {Object} item - Item data object
     * @param {string} item.inventory_id - Unique identifier
     * @returns {boolean} Success status
     */
    add(item) {
        // Validate required fields
        if (!item.inventory_id) {
            console.error('Item must have inventory_id');
            return false;
        }
        
        // Check if already exists
        if (this.find(item.inventory_id)) {
            console.warn(`Item ${item.inventory_id} already in queue`);
            return false;
        }
        
        // Add to queue
        this.items.push(item);
        
        // Callback
        if (this.config.onAdd) {
            this.config.onAdd(item);
        }
        
        this.render();
        return true;
    }
    
    /**
     * Remove item from queue
     * @param {string} inventoryId - Item identifier
     * @returns {boolean} Success status
     */
    remove(inventoryId) {
        const index = this.items.findIndex(i => i.inventory_id === inventoryId);
        if (index === -1) return false;
        
        const item = this.items[index];
        this.items.splice(index, 1);
        
        // Deselect if selected
        if (this.selectedItem?.inventory_id === inventoryId) {
            this.selectedItem = null;
        }
        
        // Callback
        if (this.config.onRemove) {
            this.config.onRemove(item);
        }
        
        this.render();
        return true;
    }
    
    /**
     * Update item quantity
     * @param {string} inventoryId - Item identifier
     * @param {number} quantity - New quantity
     * @returns {boolean} Success status
     */
    updateQuantity(inventoryId, quantity) {
        const item = this.find(inventoryId);
        if (!item) return false;
        
        // Validate quantity
        if (quantity <= 0) {
            console.error('Quantity must be positive');
            return false;
        }
        
        if (item.available_qty && quantity > item.available_qty) {
            console.error(`Quantity exceeds available (${item.available_qty})`);
            return false;
        }
        
        const oldQuantity = item.quantity;
        item.quantity = quantity;
        
        // Callback
        if (this.config.onUpdate) {
            this.config.onUpdate(item, oldQuantity);
        }
        
        this.render();
        return true;
    }
    
    /**
     * Link item to part demand
     * @param {string} inventoryId - Item identifier
     * @param {number} demandId - Part demand ID
     * @param {number} quantity - Demand quantity
     * @returns {boolean} Success status
     */
    linkToDemand(inventoryId, demandId, quantity) {
        const item = this.find(inventoryId);
        if (!item) return false;
        
        // Validate available stock
        if (quantity > item.available_qty) {
            console.error(`Insufficient stock! Required: ${quantity}, Available: ${item.available_qty}`);
            return false;
        }
        
        item.part_demand_id = demandId;
        item.quantity = quantity;
        item.locked = true;
        
        this.render();
        return true;
    }
    
    /**
     * Select queue item
     * @param {string} inventoryId - Item identifier
     */
    select(inventoryId) {
        const item = this.find(inventoryId);
        if (!item) return;
        
        this.selectedItem = item;
        
        // Callback
        if (this.config.onSelect) {
            this.config.onSelect(item);
        }
        
        this.render();
    }
    
    /**
     * Clear selection
     */
    clearSelection() {
        this.selectedItem = null;
        if (this.config.onSelect) {
            this.config.onSelect(null);
        }
        this.render();
    }
    
    /**
     * Find item by ID
     * @param {string} inventoryId - Item identifier
     * @returns {Object|null} Item or null
     */
    find(inventoryId) {
        return this.items.find(i => i.inventory_id === inventoryId) || null;
    }
    
    /**
     * Get all items
     * @returns {Array} Copy of items array
     */
    getAll() {
        return [...this.items];
    }
    
    /**
     * Get count
     * @returns {number} Number of items
     */
    count() {
        return this.items.length;
    }
    
    /**
     * Clear all items
     */
    clear() {
        this.items = [];
        this.selectedItem = null;
        this.render();
    }
    
    /**
     * Render queue to DOM
     */
    render() {
        const container = document.getElementById(this.config.queueContainerId);
        const countEl = document.getElementById(this.config.queueCountId);
        const submitBtn = document.getElementById(this.config.submitButtonId);
        const hiddenInput = document.getElementById(this.config.hiddenInputId);
        
        // Update count
        if (countEl) {
            countEl.textContent = this.items.length;
        }
        
        // Update hidden input for form submission
        if (hiddenInput) {
            hiddenInput.value = JSON.stringify(this.items);
        }
        
        // Update submit button
        if (submitBtn) {
            submitBtn.disabled = this.items.length === 0;
        }
        
        // Render items or empty message
        if (this.items.length === 0) {
            if (container) {
                container.innerHTML = `
                    <div class="text-muted text-center py-3">
                        <i class="bi bi-inbox"></i><br>
                        ${this.config.emptyMessage}
                    </div>
                `;
            }
        } else {
            if (container) {
                container.innerHTML = this.items.map(item => 
                    this.config.itemTemplate(item, this.selectedItem)
                ).join('');
                
                // Attach event listeners
                this.attachEventListeners();
            }
        }
        
        // Custom render callback
        if (this.config.onRender) {
            this.config.onRender(this.items);
        }
    }
    
    /**
     * Default item template
     * @param {Object} item - Item data
     * @param {Object|null} selectedItem - Currently selected item
     * @returns {string} HTML string
     */
    defaultItemTemplate(item, selectedItem) {
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
    
    /**
     * Attach event listeners to rendered elements
     */
    attachEventListeners() {
        // Click handlers for item selection
        document.querySelectorAll('.clickable-queue-item').forEach(el => {
            el.addEventListener('click', () => {
                this.select(el.dataset.inventoryId);
            });
        });
        
        // Remove button handlers
        document.querySelectorAll('.queue-remove-btn').forEach(el => {
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                this.remove(el.dataset.inventoryId);
            });
        });
        
        // Quantity input handlers
        document.querySelectorAll('.queue-qty-input').forEach(el => {
            el.addEventListener('change', () => {
                const newQty = parseFloat(el.value);
                const inventoryId = el.dataset.inventoryId;
                
                if (!this.updateQuantity(inventoryId, newQty)) {
                    // Reset to current value on error
                    const item = this.find(inventoryId);
                    if (item) {
                        el.value = item.quantity.toFixed(2);
                    }
                }
            });
        });
    }
    
    /**
     * Export queue data as JSON
     * @returns {string} JSON string
     */
    toJSON() {
        return JSON.stringify(this.items);
    }
}


