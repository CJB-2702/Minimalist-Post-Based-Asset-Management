/**
 * Filter storeroom dropdown options based on selected major location
 * 
 * @param {number|string} majorLocationId - The ID of the selected major location
 * @param {string} formClassName - Optional CSS class name to scope the filtering to a specific form/container
 */
function filter_storeroom_dropdowns_by_major_location_id(majorLocationId, formClassName = null) {
    // Convert to string for comparison
    const locationId = String(majorLocationId);
    
    // Determine the scope - either a specific form or the entire document
    let scope = document;
    if (formClassName) {
        const formElement = document.querySelector('.' + formClassName);
        if (formElement) {
            scope = formElement;
        }
    }
    
    // Find all storeroom dropdown items within the scope
    const storeroomItems = scope.querySelectorAll('.storeroom-dropdown-item');
    
    storeroomItems.forEach(item => {
        const itemLocationId = item.getAttribute('data-major-location-id');
        
        // Show all if no location selected, otherwise filter by matching location
        if (!locationId || locationId === '' || locationId === '0') {
            // Show all storerooms when no location is selected
            item.style.display = '';
            item.disabled = false;
        } else if (itemLocationId === locationId) {
            // Show matching storerooms
            item.style.display = '';
            item.disabled = false;
        } else {
            // Hide non-matching storerooms
            item.style.display = 'none';
            item.disabled = true;
        }
    });
    
    // Check if currently selected storeroom is still visible
    // If not, clear the selection
    const storeroomSelects = scope.querySelectorAll('select[name="storeroom_id"], select[id*="storeroom"]');
    storeroomSelects.forEach(select => {
        const selectedOption = select.options[select.selectedIndex];
        if (selectedOption && selectedOption.classList.contains('storeroom-dropdown-item')) {
            if (selectedOption.style.display === 'none' || selectedOption.disabled) {
                // Clear the selection if the selected storeroom doesn't match the location
                select.value = '';
            }
        }
    });
}

