/**
 * Edit Maintenance Event - Object-Oriented JavaScript Module
 * Handles inline editing for blockers, limitations, part demands, and tools
 * Uses data attributes for configuration
 */

class EditPanelManager {
    constructor(panelType) {
        this.panelType = panelType;
        this.init();
    }

    init() {
        this.attachEventListeners();
    }

    attachEventListeners() {
        // Edit buttons
        document.querySelectorAll(`.edit-${this.panelType}-btn`).forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const id = btn.dataset[`${this.camelize(this.panelType)}Id`];
                this.toggleEditPanel(id);
            });
        });

        // Cancel buttons
        document.querySelectorAll('.cancel-edit-btn').forEach(btn => {
            const id = btn.dataset[`${this.camelize(this.panelType)}Id`];
            if (id) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.toggleEditPanel(id);
                });
            }
        });
    }

    toggleEditPanel(id) {
        const panel = document.querySelector(`[data-edit-panel="${this.panelType}-${id}"]`);
        if (panel) {
            const isHidden = panel.style.display === 'none' || !panel.style.display;
            panel.style.display = isHidden ? 'block' : 'none';
        }
    }

    camelize(str) {
        return str.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
    }
}

// Blocker Manager
class BlockerManager extends EditPanelManager {
    constructor() {
        super('blocker');
    }
}

// Limitation Manager
class LimitationManager extends EditPanelManager {
    constructor() {
        super('limitation');
    }
}

// Part Demand Manager
class PartDemandManager extends EditPanelManager {
    constructor() {
        super('part-demand');
    }
}

// Tool Manager
class ToolManager extends EditPanelManager {
    constructor() {
        super('tool');
    }
}

// Modal Manager for setting default times
class ModalManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupModalEventListeners();
    }

    setupModalEventListeners() {
        // Set current time when blocker modal opens
        const blockerModal = document.getElementById('createBlockerModal');
        if (blockerModal) {
            blockerModal.addEventListener('show.bs.modal', () => {
                this.setCurrentTime('blockerStartTime');
            });
        }

        // Set current time when limitation modal opens
        const limitationModal = document.getElementById('createLimitationModal');
        if (limitationModal) {
            limitationModal.addEventListener('show.bs.modal', () => {
                this.setCurrentTime('editLimitationStartTime');
                this.setupLimitationStatusWatcher();
            });
        }
    }

    setCurrentTime(inputId) {
        const input = document.getElementById(inputId);
        if (input && !input.value) {
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            input.value = `${year}-${month}-${day}T${hours}:${minutes}`;
        }
    }

    setupLimitationStatusWatcher() {
        const statusSelect = document.getElementById('editLimitationStatus');
        const compensationSection = document.getElementById('editTemporaryModificationsSection');
        const compensationTextarea = document.getElementById('editTemporaryModifications');

        if (statusSelect && compensationSection && compensationTextarea) {
            const updateCompensationVisibility = () => {
                const selectedStatus = statusSelect.value;
                const requiresCompensation = selectedStatus.toLowerCase().includes('compensation');
                
                compensationSection.style.display = requiresCompensation ? 'block' : 'none';
                compensationTextarea.required = requiresCompensation;
            };

            statusSelect.addEventListener('change', updateCompensationVisibility);
            updateCompensationVisibility(); // Initial check
        }
    }
}

// Action Selection Handler
class ActionSelector {
    selectAction(actionId) {
        const url = new URL(window.location.href);
        url.searchParams.set('action_id', actionId);
        window.location.href = url.toString();
    }
}

// Action Delete Handler
class ActionDeleter {
    deleteAction(actionId) {
        const message = 'Are you sure you want to delete this action? This cannot be undone.\n\n' +
                       'If you are a technician doing work, always prefer to use the work portal. ' +
                       'It\'s preferred to mark an action as skipped for analytics purposes.';
        
        if (confirm(message)) {
            const form = document.getElementById(`deleteActionForm${actionId}`);
            if (form) {
                form.submit();
            }
        }
    }
}

// Action Creator Portal Handlers
class ActionCreatorPortal {
    selectTemplateActionSet(templateSetId, maintenanceActionSetId) {
        // Remove selected class from all items
        document.querySelectorAll('[data-template-set-id]').forEach(item => {
            item.classList.remove('selected');
            item.style.backgroundColor = '';
        });
        
        // Add selected class
        const selectedItem = document.querySelector(`[data-template-set-id="${templateSetId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
            selectedItem.style.backgroundColor = '#cfe2ff';
        }
        
        // Load template action items via HTMX
        const container = document.getElementById('template-action-items-container');
        const list = document.getElementById('template-action-items-list');
        
        if (container && list && typeof htmx !== 'undefined') {
            const url = `/maintenance/action-creator-portal/list-template-action-items/${templateSetId}?maintenance_action_set_id=${maintenanceActionSetId}`;
            htmx.ajax('GET', url, {
                target: list,
                swap: 'innerHTML'
            }).then(() => {
                container.style.display = 'block';
            });
        }
    }

    selectTemplateAction(templateActionId) {
        this.showModal(`templateActionModal${templateActionId}`);
    }

    selectProtoAction(protoActionId) {
        this.showModal(`protoActionModal${protoActionId}`);
    }

    selectCurrentAction(sourceActionId) {
        this.showModal(`currentActionModal${sourceActionId}`);
    }

    selectBlankAction() {
        this.showModal('blankActionModal');
    }

    showModal(modalId) {
        const modalElement = document.getElementById(modalId);
        if (modalElement && typeof bootstrap !== 'undefined') {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        }
    }

    filterCurrentActions(searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        const items = document.querySelectorAll('.current-action-item');
        let visibleCount = 0;
        
        items.forEach(item => {
            const actionName = (item.getAttribute('data-action-name') || '').toLowerCase();
            const actionDescription = (item.getAttribute('data-action-description') || '').toLowerCase();
            
            if (!searchTerm || actionName.includes(searchLower) || actionDescription.includes(searchLower)) {
                item.style.display = '';
                visibleCount++;
            } else {
                item.style.display = 'none';
            }
        });
        
        // Show/hide "no results" message
        const listContainer = document.getElementById('current-actions-list');
        if (listContainer) {
            let noResultsMsg = listContainer.querySelector('.no-results-message');
            if (visibleCount === 0 && searchTerm) {
                if (!noResultsMsg) {
                    noResultsMsg = document.createElement('div');
                    noResultsMsg.className = 'list-group-item text-muted no-results-message';
                    noResultsMsg.textContent = 'No actions match your search.';
                    listContainer.appendChild(noResultsMsg);
                }
            } else if (noResultsMsg) {
                noResultsMsg.remove();
            }
        }
    }

    updateInsertPosition(actionId, value, prefix = '') {
        const insertPositionEl = document.getElementById(`insertPosition${prefix}${actionId}`);
        const afterSelect = document.getElementById(`afterActionSelect${prefix}${actionId}`);
        
        if (insertPositionEl) {
            insertPositionEl.value = value;
        }
        if (afterSelect) {
            afterSelect.style.display = (value === 'after') ? 'block' : 'none';
        }
    }

    updateInsertPositionProto(actionId, value) {
        this.updateInsertPosition(actionId, value, 'Proto');
    }

    updateInsertPositionCurrent(actionId, value) {
        this.updateInsertPosition(actionId, value, 'Current');
    }

    updateInsertPositionBlank(value) {
        const insertPositionEl = document.getElementById('insertPositionBlank');
        const afterSelect = document.getElementById('afterActionSelectBlank');
        
        if (insertPositionEl) {
            insertPositionEl.value = value;
        }
        if (afterSelect) {
            afterSelect.style.display = (value === 'after') ? 'block' : 'none';
        }
    }
}

// Initialize all managers when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize edit panel managers
    window.blockerManager = new BlockerManager();
    window.limitationManager = new LimitationManager();
    window.partDemandManager = new PartDemandManager();
    window.toolManager = new ToolManager();
    
    // Initialize modal manager
    window.modalManager = new ModalManager();
    
    // Initialize action handlers
    window.actionSelector = new ActionSelector();
    window.actionDeleter = new ActionDeleter();
    window.actionCreatorPortal = new ActionCreatorPortal();
});

// Global functions for backwards compatibility and inline onclick handlers
function selectAction(actionId) {
    if (window.actionSelector) {
        window.actionSelector.selectAction(actionId);
    }
}

function deleteAction(actionId) {
    if (window.actionDeleter) {
        window.actionDeleter.deleteAction(actionId);
    }
}

function selectTemplateActionSet(templateSetId, maintenanceActionSetId) {
    if (window.actionCreatorPortal) {
        window.actionCreatorPortal.selectTemplateActionSet(templateSetId, maintenanceActionSetId);
    }
}

function selectTemplateAction(templateActionId, maintenanceActionSetId) {
    if (window.actionCreatorPortal) {
        window.actionCreatorPortal.selectTemplateAction(templateActionId);
    }
}

function selectProtoAction(protoActionId, maintenanceActionSetId) {
    if (window.actionCreatorPortal) {
        window.actionCreatorPortal.selectProtoAction(protoActionId);
    }
}

function selectCurrentAction(sourceActionId, maintenanceActionSetId) {
    if (window.actionCreatorPortal) {
        window.actionCreatorPortal.selectCurrentAction(sourceActionId);
    }
}

function selectBlankAction() {
    if (window.actionCreatorPortal) {
        window.actionCreatorPortal.selectBlankAction();
    }
}

function filterCurrentActions(searchTerm) {
    if (window.actionCreatorPortal) {
        window.actionCreatorPortal.filterCurrentActions(searchTerm);
    }
}

function updateInsertPosition(actionId, value) {
    if (window.actionCreatorPortal) {
        window.actionCreatorPortal.updateInsertPosition(actionId, value);
    }
}

function updateInsertPositionProto(actionId, value) {
    if (window.actionCreatorPortal) {
        window.actionCreatorPortal.updateInsertPositionProto(actionId, value);
    }
}

function updateInsertPositionCurrent(actionId, value) {
    if (window.actionCreatorPortal) {
        window.actionCreatorPortal.updateInsertPositionCurrent(actionId, value);
    }
}

function updateInsertPositionBlank(value) {
    if (window.actionCreatorPortal) {
        window.actionCreatorPortal.updateInsertPositionBlank(value);
    }
}
