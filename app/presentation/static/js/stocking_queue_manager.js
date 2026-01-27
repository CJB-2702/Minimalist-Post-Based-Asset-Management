/**
 * StockingQueueManager - Manages stocking queue with sessionStorage persistence
 * Extends the base QueueManager with persistence and stocking-specific functionality
 */
class StockingQueueManager {
    constructor() {
        this.storageKey = 'stocking_queue';
        this.initialize();
    }
    
    /**
     * Initialize queue from sessionStorage
     */
    initialize() {
        if (!sessionStorage.getItem(this.storageKey)) {
            sessionStorage.setItem(this.storageKey, JSON.stringify([]));
        }
    }
    
    /**
     * Add item to stocking queue
     * @param {Object} params - Item parameters
     * @param {number} params.inventoryId - ActiveInventory ID
     * @param {string} params.partNumber - Part number
     * @param {string} params.partName - Part name
     * @param {number} params.availableQty - Available quantity
     * @param {number} params.storeroomId - Storeroom ID
     * @param {string} params.storeroomName - Storeroom name
     * @param {number} params.partId - Part definition ID
     * @returns {boolean} Success status
     */
    addItem({inventoryId, partNumber, partName, availableQty, storeroomId, storeroomName, partId}) {
        const queue = this.getQueue();
        const existing = queue.find(item => item.inventoryId === inventoryId);
        
        if (existing) {
            console.warn(`Item ${inventoryId} already in queue`);
            this.showToast('Item already in queue', 'warning');
            return false;
        }
        
        const item = {
            inventoryId,
            partNumber,
            partName,
            availableQty,
            quantityToMove: availableQty, // Default to moving all available
            storeroomId,
            storeroomName,
            partId,
            addedAt: new Date().toISOString()
        };
        
        queue.push(item);
        this.saveQueue(queue);
        this.emitChange();
        this.showToast(`Added ${partNumber} to queue`, 'success');
        return true;
    }
    
    /**
     * Remove item from queue
     * @param {number} inventoryId - ActiveInventory ID
     * @returns {boolean} Success status
     */
    removeItem(inventoryId) {
        const queue = this.getQueue();
        const index = queue.findIndex(item => item.inventoryId === inventoryId);
        
        if (index === -1) {
            return false;
        }
        
        const item = queue[index];
        queue.splice(index, 1);
        this.saveQueue(queue);
        this.emitChange();
        this.showToast(`Removed ${item.partNumber} from queue`, 'info');
        return true;
    }
    
    /**
     * Update quantity to move for an item
     * @param {number} inventoryId - ActiveInventory ID
     * @param {number} newQuantity - New quantity to move
     * @returns {boolean} Success status
     */
    updateQuantity(inventoryId, newQuantity) {
        const queue = this.getQueue();
        const item = queue.find(i => i.inventoryId === inventoryId);
        
        if (!item) {
            return false;
        }
        
        // Validate quantity
        if (newQuantity <= 0) {
            this.showToast('Quantity must be positive', 'error');
            return false;
        }
        
        if (newQuantity > item.availableQty) {
            this.showToast(`Quantity cannot exceed available (${item.availableQty})`, 'error');
            return false;
        }
        
        item.quantityToMove = newQuantity;
        this.saveQueue(queue);
        this.emitChange();
        return true;
    }
    
    /**
     * Clear all items from queue
     */
    clearQueue() {
        sessionStorage.setItem(this.storageKey, JSON.stringify([]));
        this.emitChange();
        this.showToast('Queue cleared', 'info');
    }
    
    /**
     * Get all items in queue
     * @returns {Array} Queue items
     */
    getQueue() {
        try {
            return JSON.parse(sessionStorage.getItem(this.storageKey)) || [];
        } catch (e) {
            console.error('Error parsing queue from sessionStorage:', e);
            return [];
        }
    }
    
    /**
     * Get count of items in queue
     * @returns {number} Number of items
     */
    getCount() {
        return this.getQueue().length;
    }
    
    /**
     * Check if queue is empty
     * @returns {boolean} True if empty
     */
    isEmpty() {
        return this.getCount() === 0;
    }
    
    /**
     * Find item by inventory ID
     * @param {number} inventoryId - ActiveInventory ID
     * @returns {Object|null} Item or null
     */
    findItem(inventoryId) {
        return this.getQueue().find(item => item.inventoryId === inventoryId) || null;
    }
    
    /**
     * Get all inventory IDs
     * @returns {Array<number>} Array of inventory IDs
     */
    getInventoryIds() {
        return this.getQueue().map(item => item.inventoryId);
    }
    
    /**
     * Save queue to sessionStorage
     * @param {Array} queue - Queue array
     */
    saveQueue(queue) {
        sessionStorage.setItem(this.storageKey, JSON.stringify(queue));
    }
    
    /**
     * Emit change event
     */
    emitChange() {
        const event = new CustomEvent('stockingQueueChanged', {
            detail: {
                queue: this.getQueue(),
                count: this.getCount()
            }
        });
        window.dispatchEvent(event);
    }
    
    /**
     * Show toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type: success, error, warning, info
     */
    showToast(message, type = 'info') {
        // Use global showToast function from alerts.js if available
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            // Fallback to console
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }
    
    /**
     * Export queue as JSON for backend submission
     * @returns {string} JSON string
     */
    toJSON() {
        return JSON.stringify(this.getQueue());
    }
    
    /**
     * Get queue data formatted for backend
     * @returns {Object} Formatted data
     */
    getSubmissionData() {
        const queue = this.getQueue();
        return {
            inventory_ids: queue.map(item => item.inventoryId),
            quantities: queue.reduce((acc, item) => {
                acc[item.inventoryId] = item.quantityToMove;
                return acc;
            }, {}),
            items: queue
        };
    }
}
