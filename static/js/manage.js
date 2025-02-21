/* Utility functions */

function compileTemplate(templateString) {
    /**
    * Compiles an ES6 template literal string into a function that accepts a data object.
    * Using `with(data)` lets you reference properties directly (e.g. assistant.id).
    */
    return new Function("data", "with(data) { return `" + templateString + "`; }");
}

// Helper function that waits until a container is loaded
async function waitForContainerAndTarget(containerId, targetPrefix, targetId, callback) {
    const container = document.getElementById(containerId);
    if (container && container.dataset.loaded === "true") {
        // Container is marked as loaded. Now check for the target tab.
        const targetTabLink = document.querySelector(`#${targetPrefix}-${targetId}-tab`);
        if (targetTabLink) {
            callback(targetTabLink);
        } else {
            // The container is loaded but the target tab isn't in the DOM yet.
            // Use a MutationObserver to detect when the target tab is added.
            const observer = new MutationObserver((mutations, obs) => {
                const target = document.querySelector(`#${targetPrefix}-${targetId}-tab`);
                if (target) {
                    obs.disconnect();
                    callback(target);
                }
            });
            observer.observe(container, { childList: true, subtree: true });
        }
    } else {
        // Container isn't loaded yet; try again after a short delay.
        setTimeout(function() {
            waitForContainerAndTarget(containerId, targetPrefix, targetId, callback);
        }, 100);
    }
}

function toggleAssistantFileSearch(assistantId) {
    const fileSearchSwitch = document.getElementById(`fileSearchSwitch-${assistantId}`);
    const folderDiv = document.getElementById(`folder-div-${assistantId}`);
    if (fileSearchSwitch.checked) {
        folderDiv.style.display = 'block';
    } else {
        folderDiv.style.display = 'none';
    }
}

function renderFunctionCheckboxes(assistantId) {
    const functionsListDiv = document.getElementById(`functions-list-${assistantId}`);
    functionsListDiv.innerHTML = ''; // Clear any existing content

    functionDefinitions.forEach(funcDef => {
        const functionName = funcDef.name;

        // Create the checkbox input
        const checkbox = document.createElement('div');
        checkbox.classList.add('form-check');

        const input = document.createElement('input');
        input.classList.add('form-check-input');
        input.type = 'checkbox';
        input.value = functionName;
        input.id = `function-${functionName}-${assistantId}`;

        const label = document.createElement('label');
        label.classList.add('form-check-label');
        label.setAttribute('for', `function-${functionName}-${assistantId}`);
        label.textContent = functionName;

        // Append input and label to the checkbox div
        checkbox.appendChild(input);
        checkbox.appendChild(label);

        // Append the checkbox to the functions list div
        functionsListDiv.appendChild(checkbox);
    });
}


/* Loading components and orchestration of the flow */

// Global dicts to store the current references of objects as id: object items

let folders = {};
let assistants = {};
let functions = {};
let folderFiles = {};  // {folderId: [file1, file2, ...]}
let fileFolders = {};  // {fileId: [folder1, folder2, ...]}
let assistantFoldersMapping = {}; // { assistantId: [folderUUID, ...], ... }
let selectedFiles = [];

let assistantsLoaded = false;
let assistantsError = null;

// Global variables for sorting and filtering

let assistantSortField = 'created_at'; // default sort field
let assistantSortOrder = 'desc';       // default sort order
let assistantFilters = {
    name: '',
    startDate: null,
    endDate: null,
    folderId: '',
    model: ''
};
let folderSortField = 'created_at'; // default sort field
let folderSortOrder = 'desc';       // default sort order
let folderFilters = {
    name: '',
    startDate: null,
    endDate: null,
    status: '',
    hasExpiration: ''
};
let functionSortField = 'created_at'; // default sort field
let functionSortOrder = 'desc';       // default sort order
let functionFilters = {
    name: '',
    functionType: ''
};


async function loadAndDisplayFolders() {
    const folders = await fetchFolders();
    displayFolders(folders);
    return folders;
}

async function loadAndDisplayAssistants() {
    await fetchAssistantFoldersMapping();
    const assistants = await fetchAssistants();
    displayAssistants();
    return assistants;
}

async function loadAndDisplayFunctions() {
    const functions = await fetchFunctions();
    displayFunctions();
    return functions;
}

// Orchestrate the flow
async function initializePage() {
    // Show loading indicator initially for all
    toggleLoading('folders', true);
    toggleLoading('assistants', true);
    toggleLoading('functions', true);

    folders = await loadAndDisplayFolders();
    populateAssistantFilterOptions();
    loadAndDisplayAssistants();
    loadAndDisplayFunctions();
}

document.addEventListener('DOMContentLoaded', async function() {
    // Wait for initializePage() to finish
    await initializePage();

    setTimeout(() => {
        const isFoldersEmpty = Object.keys(folders).length === 0;
        const isAssistantsEmpty = Object.keys(assistants).length === 0;
        const isFunctionsEmpty = Object.keys(functions).length === 0;

        if (isFoldersEmpty && isAssistantsEmpty && isFunctionsEmpty) {
            const getStartedModalElement = document.getElementById('getStartedModal');
            const getStartedModal = new bootstrap.Modal(getStartedModalElement, {
                backdrop: 'static',
                keyboard: false
            });
            getStartedModal.show();
        }
    }, 1000);
});


/* List utility functions */

async function refreshAssistantsList() {
    const assistantsList = document.getElementById('assistants-list');

    // Dispose of existing tooltips within the assistants list
    disposeTooltips(assistantsList);

    assistantsList.innerHTML = ''; // Clear any existing assistants
    toggleLoading('assistants', true);

    // Reset to default sorting options
    assistantSortField = 'created_at';
    assistantSortOrder = 'desc';
    updateSortDropdownUI('assistantSortDropdown', assistantSortField, assistantSortOrder);

    // Close the sorting dropdown if open
    const dropdownElement = document.getElementById('assistantSortDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    // Fetch and display assistants
    loadAndDisplayAssistants();

    // Refresh collapse all button
    const btnCollapseAllAssistants = document.getElementById('collapse-all-assistants');
    const btnExpandAllAssistants = document.getElementById('expand-all-assistants');
    btnCollapseAllAssistants.classList.remove('d-none');
    btnExpandAllAssistants.classList.add('d-none');
}

async function refreshFolderList() {
    const foldersList = document.getElementById('folders-list');

    // Dispose of existing tooltips within the folders list
    disposeTooltips(foldersList);

    foldersList.innerHTML = ''; // Clear any existing folders
    toggleLoading('folders', true);

    // Reset to default sorting options
    folderSortField = 'created_at';
    folderSortOrder = 'desc';
    updateSortDropdownUI('folderSortDropdown', folderSortField, folderSortOrder);

    // Fetch and display
    await loadAndDisplayFolders();
    populateAssistantFilterOptions();

    // Refresh collapse all button
    const btnCollapseAllFolders = document.getElementById('collapse-all-folders');
    const btnExpandAllFolders = document.getElementById('expand-all-folders');
    btnCollapseAllFolders.classList.remove('d-none');
    btnExpandAllFolders.classList.add('d-none');
}

async function refreshFunctionsList() {
    const functionsList = document.getElementById('functions-list');

    // Dispose of existing tooltips within the functions list
    disposeTooltips(functionsList);

    functionsList.innerHTML = ''; // Clear any existing functions
    toggleLoading('functions', true);

    // Reset to default sorting options
    functionSortField = 'created_at';
    functionSortOrder = 'desc';
    updateSortDropdownUI('functionSortDropdown', functionSortField, functionSortOrder);

    // Close the sorting dropdown if open
    const dropdownElement = document.getElementById('functionSortDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    loadAndDisplayFunctions();

    // Refresh collapse all button
    const btnCollapseAllFunctions = document.getElementById('collapse-all-functions');
    const btnExpandAllFunctions = document.getElementById('expand-all-functions');
    btnCollapseAllFunctions.classList.remove('d-none');
    btnExpandAllFunctions.classList.add('d-none');
}

function toggleAllAssistants(action) {
    const btnCollapseAllAssistants = document.getElementById('collapse-all-assistants');
    const btnExpandAllAssistants = document.getElementById('expand-all-assistants');
    const collapsibleItems = document.querySelectorAll('#assistants-list .collapse');
    collapsibleItems.forEach(item => {
        const bsCollapse = new bootstrap.Collapse(item, {
            toggle: false
        });
        if (action === 'collapse') bsCollapse.hide();
        else bsCollapse.show();
    });
    if (action === 'collapse') {
        btnCollapseAllAssistants.classList.add('d-none');
        btnExpandAllAssistants.classList.remove('d-none');
    } else {  // expand
        btnCollapseAllAssistants.classList.remove('d-none');
        btnExpandAllAssistants.classList.add('d-none');
    }
}

function toggleAllFolders(action) {
    const btnCollapseAllFolders = document.getElementById('collapse-all-folders');
    const btnExpandAllFolders = document.getElementById('expand-all-folders');
    const collapsibleItems = document.querySelectorAll('#folders-list .collapse');
    collapsibleItems.forEach(item => {
        const bsCollapse = new bootstrap.Collapse(item, {
            toggle: false
        });
        if (action === 'collapse') bsCollapse.hide();
        else bsCollapse.show();
    });
    if (action === 'collapse') {
        btnCollapseAllFolders.classList.add('d-none');
        btnExpandAllFolders.classList.remove('d-none');
    } else {  // expand
        btnCollapseAllFolders.classList.remove('d-none');
        btnExpandAllFolders.classList.add('d-none');
    }
}

function toggleAllFunctions(action) {
    const btnCollapseAllFunctions = document.getElementById('collapse-all-functions');
    const btnExpandAllFunctions = document.getElementById('expand-all-functions');
    const collapsibleItems = document.querySelectorAll('#functions-list .collapse');
    collapsibleItems.forEach(item => {
        const bsCollapse = new bootstrap.Collapse(item, {
            toggle: false
        });
        if (action === 'collapse') bsCollapse.hide();
        else bsCollapse.show();
    });
    if (action === 'collapse') {
        btnCollapseAllFunctions.classList.add('d-none');
        btnExpandAllFunctions.classList.remove('d-none');
    } else {  // expand
        btnCollapseAllFunctions.classList.remove('d-none');
        btnExpandAllFunctions.classList.add('d-none');
    }
}

function setAssistantSort(field, order, event) {
    if (event) event.preventDefault(); // Prevent default anchor behavior

    assistantSortField = field;
    assistantSortOrder = order;

    // Update the active class on the dropdown menu items
    updateSortDropdownUI('assistantSortDropdown', field, order);

    displayAssistants(); // Re-display assistants with new sort order

    // Close the dropdown menu
    const dropdownElement = document.getElementById('assistantSortDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();

    // Refresh collapse all button
    const btnCollapseAllAssistants = document.getElementById('collapse-all-assistants');
    const btnExpandAllAssistants = document.getElementById('expand-all-assistants');
    btnCollapseAllAssistants.classList.remove('d-none');
    btnExpandAllAssistants.classList.add('d-none');
    }
}

function setFolderSort(field, order, event) {
    if (event) event.preventDefault();

    folderSortField = field;
    folderSortOrder = order;

    updateSortDropdownUI('folderSortDropdown', field, order);

    displayFolders();

    const dropdownElement = document.getElementById('folderSortDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    // Refresh collapse all button
    const btnCollapseAllFolders = document.getElementById('collapse-all-folders');
    const btnExpandAllFolders = document.getElementById('expand-all-folders');
    btnCollapseAllFolders.classList.remove('d-none');
    btnExpandAllFolders.classList.add('d-none');
}

function setFunctionSort(field, order, event) {
    if (event) event.preventDefault();

    functionSortField = field;
    functionSortOrder = order;

    // Update the active class on the dropdown menu items
    updateSortDropdownUI('functionSortDropdown', field, order);

    displayFunctions(); // Re-display functions with new sort order

    // Close the dropdown menu
    const dropdownElement = document.getElementById('functionSortDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    // Refresh collapse all button
    const btnCollapseAllFunctions = document.getElementById('collapse-all-functions');
    const btnExpandAllFunctions = document.getElementById('expand-all-functions');
    btnCollapseAllFunctions.classList.remove('d-none');
    btnExpandAllFunctions.classList.add('d-none');
}

function applyAssistantFilters() {
    assistantFilters.name = document.getElementById('filterName').value.toLowerCase();
    assistantFilters.startDate = document.getElementById('filterStartDate').value
        ? new Date(document.getElementById('filterStartDate').value)
        : null;
    assistantFilters.endDate = document.getElementById('filterEndDate').value
        ? new Date(document.getElementById('filterEndDate').value)
        : null;

    // Adjust dates
    if (assistantFilters.startDate) {
        assistantFilters.startDate.setHours(0, 0, 0, 0);
    }
    if (assistantFilters.endDate) {
        assistantFilters.endDate.setHours(23, 59, 59, 999);
    }

    assistantFilters.folderId = document.getElementById('filterFolder').value;
    assistantFilters.model = document.getElementById('filterModel').value;

    displayAssistants(); // Re-display assistants with filters applied

    // Close the dropdown menu
    const dropdownElement = document.getElementById('assistantFilterDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    // Update the filter icon based on active filters
    updateFilterIcon('assistantFilterDropdown', assistantFilters);
}

function resetAssistantFilters() {
    document.getElementById('assistantFilterForm').reset();
    assistantFilters = {
        name: '',
        startDate: null,
        endDate: null,
        folderId: '',
        model: ''
    };
    displayAssistants();

    // Close the dropdown menu
    const dropdownElement = document.getElementById('assistantFilterDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    // Update the filter icon to reflect no active filters
    updateFilterIcon('assistantFilterDropdown', assistantFilters);
}

function applyFolderFilters() {
    folderFilters.name = document.getElementById('folderFilterName').value.toLowerCase();

    folderFilters.status = document.getElementById('vsFilterStatus').value;
    folderFilters.hasExpiration = document.getElementById('vsFilterHasExpiration').value;

    displayFolders();

    const dropdownElement = document.getElementById('folderFilterDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    updateFilterIcon('folderFilterDropdown', folderFilters);
}

function resetFolderFilters() {
    document.getElementById('folderFilterForm').reset();
    folderFilters = {
        name: '',
        startDate: null,
        endDate: null,
        status: '',
        hasExpiration: ''
    };
    displayFolders();

    const dropdownElement = document.getElementById('folderFilterDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    updateFilterIcon('folderFilterDropdown', folderFilters);
}

function applyFunctionFilters() {
    // Read filter values
    functionFilters.name = document.getElementById('functionFilterName').value.toLowerCase();
    functionFilters.startDate = document.getElementById('functionFilterStartDate').value
        ? new Date(document.getElementById('functionFilterStartDate').value)
        : null;
    functionFilters.endDate = document.getElementById('functionFilterEndDate').value
        ? new Date(document.getElementById('functionFilterEndDate').value)
        : null;

    // Adjust dates
    if (functionFilters.startDate) {
        functionFilters.startDate.setHours(0, 0, 0, 0);
    }
    if (functionFilters.endDate) {
        functionFilters.endDate.setHours(23, 59, 59, 999);
    }

    functionFilters.folderId = document.getElementById('functionFilterFolder').value;
    functionFilters.functionType = document.getElementById('functionFilterType').value;

    displayFunctions();

    // Update button styles and icons
    updateFolderFilesButtonStyles();

    // Update the filter icon
    updateFilterIcon('functionFilterDropdown', functionFilters);

    // Close the dropdown menu
    const dropdownElement = document.getElementById('functionFilterDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }
}

function resetFunctionFilters() {
    document.getElementById('functionFilterForm').reset();
    functionFilters = {
        name: '',
        functionType: ''
    };

    displayFunctions();

    // Update button styles and icons
    updateFolderFilesButtonStyles();

    // Update the filter icon
    updateFilterIcon('functionFilterDropdown', functionFilters);

    // Close the dropdown menu
    const dropdownElement = document.getElementById('functionFilterDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }
}

function populateAssistantFilterOptions() {
    const filterFolder = document.getElementById('filterFolder');
    filterFolder.innerHTML = '<option value="">All</option>'; // Reset options

    // Add option for "None" (assistants without any folders)
    const noneOption = document.createElement('option');
    noneOption.value = "none";
    noneOption.textContent = "None";
    filterFolder.appendChild(noneOption);

    for (const [folderId, folder] of Object.entries(folders)) {
        const option = document.createElement('option');
        option.value = folderId;
        option.textContent = folder.name;
        filterFolder.appendChild(option);
    }
}

function populateFunctionFilterOptions() {
    const filterAssistant = document.getElementById('functionFilterAssistant');
    filterAssistant.innerHTML = '<option value="">All</option>'; // Reset options

    for (const [assistantId, assistant] of Object.entries(assistants)) {
        const option = document.createElement('option');
        option.value = assistantId;
        option.textContent = assistant.name ?? 'Untitled assistant';
        filterAssistant.appendChild(option);
    }
}

function updateSortDropdownUI(dropdownId, field, order) {
    // Remove 'active' class from all dropdown items
    const dropdownItems = document.querySelectorAll(`#${dropdownId} + .dropdown-menu .dropdown-item`);
    dropdownItems.forEach(item => item.classList.remove('active'));

    // Add 'active' class to the selected item
    const selectedItem = document.querySelector(`#${dropdownId} + .dropdown-menu .dropdown-item[href*="${field}"][href*="${order}"]`);
    if (selectedItem) {
        selectedItem.classList.add('active');
    }

    // Update the sort icon
    const sortIcon = document.getElementById(dropdownId);
    sortIcon.className = 'text-light-emphasis bi ms-2';
    if (field === 'name') {
        sortIcon.classList.add(order === 'asc' ? 'bi-sort-alpha-down' : 'bi-sort-alpha-down-alt');
    } else if (field === 'created_at') {
        sortIcon.classList.add(order === 'asc' ? 'bi-sort-down-alt' : 'bi-sort-down');
    } else if (field === 'size' || field === 'bytes') {
        sortIcon.classList.add(order === 'asc' ? 'bi-sort-numeric-down' : 'bi-sort-numeric-down-alt');
    } else if (field === 'last_active_at') {
        sortIcon.classList.add(order === 'asc' ? 'bi-clock-history' : 'bi-clock');
    }
}

function updateFilterIcon(dropdownId, filters) {
    const dropdownElement = document.getElementById(dropdownId);
    const filtersActive = areFiltersActive(filters);

    if (filtersActive) {
        dropdownElement.classList.remove('bi-funnel');
        dropdownElement.classList.add('bi-funnel-fill');
    } else {
        dropdownElement.classList.remove('bi-funnel-fill');
        dropdownElement.classList.add('bi-funnel');
    }
}

function areFiltersActive(filters) {
    return Object.values(filters).some(value => {
        if (value instanceof Date) {
            return true;
        } else {
            return value !== '' && value !== null && value !== undefined;
        }
    });
}


/* Folders */

async function fetchFolders() {
    try {
        const response = await fetch(listFoldersUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (data.folders) {

            // Clear the global folders object
            folders = {};

            // Populate the global folders object
            data.folders.forEach(folder => {
                folders[folder.uuid] = folder;
            });

            // Return the global folders object
            return folders;
        } else {
            const parsedError = parseErrorText(data.error);
            showToast("Failed to fetch folders!", parsedError.errorMessage);
            console.error('Failed to fetch folders!', parsedError);
            return {};
        }
    } catch (error) {
        showToast("Error fetching folders:", error);
        console.error('Error fetching folders:', error);
        return {};
    } finally {
        toggleLoading('folders', false);
    }
}

async function updateFoldersByIds(folderIds) {
    const fetchPromises = folderIds.map(async (folderId) => {
        const retrieveFolderUrl = retrieveFolderUrlTemplate.replace('VS_ID_PLACEHOLDER', folderId);
        try {
            const response = await fetch(retrieveFolderUrl, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${API_KEY}`,
                    'Content-Type': 'application/json',
                }
            });
            if (response.ok) {
                const data = await response.json();
                folders[folderId] = data;
            } else {
                console.error(`Failed to fetch folder with ID ${folderId}`);
            }
        } catch (error) {
            console.error(`Error fetching folder with ID ${folderId}:`, error);
        }
    });

    await Promise.all(fetchPromises);
}

const folderItemTemplate = document.getElementById("folder-item-template").innerHTML;

function renderFolder(folder) {
    const folderItem = document.createElement('div');
    folderItem.className = 'folder-item';
    folderItem.id = `folder-${folder.uuid}`;

    // Grab the raw template string from the DOM
    const data = {
        folder: folder
    };

    // Compile the template into a function
    const renderTemplate = compileTemplate(folderItemTemplate);
    folderItem.innerHTML = renderTemplate(data);

    return folderItem;
}

function displayFolders() {
    const foldersList = document.getElementById('folders-list');

    // Dispose of existing tooltips within the folders list
    disposeTooltips(foldersList);

    foldersList.innerHTML = '';

    const totalFolders = Object.values(folders).length;

    // Convert to array
    let foldersArray = Object.values(folders);

    // Apply filters
    foldersArray = foldersArray.filter(folder => {
        // Name filter
        if (folderFilters.name && ! folder.name.toLowerCase().includes(folderFilters.name)) {
            return false;
        }
        // Creation date filter
        const createdAt = new Date(folder.created_at * 1000);
        if (folderFilters.startDate && createdAt < folderFilters.startDate) {
            return false;
        }
        if (folderFilters.endDate && createdAt > folderFilters.endDate) {
            return false;
        }
        return true;
    });

    const filteredFoldersCount = foldersArray.length;

    // Update the folder count display only if filters are active
    const folderCountElement = document.getElementById('folders-count');
    if (areFiltersActive(folderFilters)) {
        folderCountElement.textContent = `${filteredFoldersCount} results (${totalFolders} total)`;
        folderCountElement.style.display = 'inline';
    } else {
        folderCountElement.style.display = 'none';
    }

    // Handle different cases based on total folders and filtered folders
    if (totalFolders === 0) {
        // No folders exist at all
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4 no-folders-message';
        messageDiv.innerHTML = `
            <p class="text-secondary">No folders found.</p>
            <span class="text-secondary">
                <a href="#" class="text-decoration-none"><i class="bi bi-plus-lg"></i>Add a folder.</a>
            </span>
        `;
        foldersList.appendChild(messageDiv);
        return;
    } else if (foldersArray.length === 0) {
        // Folders exist, but none match the filters
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4';
        messageDiv.innerHTML = `
            <p class="text-secondary">No folders match your filters.</p>
            <span class="text-secondary">You can
            <a href="#" class="text-decoration-none" onclick="resetFolderFilters()">reset the filters</a>
            to see all folders.</span>
        `;
        foldersList.appendChild(messageDiv);
        return;
    }

    // Sort
    foldersArray.sort((a, b) => {
        let compareResult = 0;

        if (folderSortField === 'name') {
            compareResult = (a.name || 'Untitled folder').localeCompare(b.name || 'Untitled folder');
        } else if (folderSortField === 'created_at') {
            compareResult = a.created_at - b.created_at;
        } else if (folderSortField === 'last_active_at') {
            compareResult = a.last_active_at - b.last_active_at;
        }

        return folderSortOrder === 'asc' ? compareResult : -compareResult;
    });

    // Display
    for (const folder of foldersArray) {
        const folderItem = renderFolder(folder);
        foldersList.appendChild(folderItem);
    }

    initializeTooltips();
}

// Redirect to Knowledge tab
async function editFolder(folderId) {
    console.log("Editing folder:", folderId);
    const foldersTabTrigger = document.getElementById('foldersTab');
    if (foldersTabTrigger && !foldersTabTrigger.classList.contains('active')) {
        foldersTabTrigger.click();
    }
    await waitForContainerAndTarget('folders-tab-container', 'folders-tab', folderId, function(targetTabLink) {
        let tabInstance = bootstrap.Tab.getInstance(targetTabLink);
        if (!tabInstance) {
            tabInstance = new bootstrap.Tab(targetTabLink);
        }
        tabInstance.show();
    });
}

function updateFolderFilesButtonStyles() {
    const buttons = document.querySelectorAll('.folder-files-button');
    buttons.forEach(button => {
        const folderId = button.getAttribute('data-folder-uuid');
        const iconElement = button.querySelector('i');

        if (functionFilters.folderId === folderId && functionFilters.folderId !== '') {
            // The filter is active for this store
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-secondary');
            iconElement.classList.remove('bi-archive');
            iconElement.classList.add('bi-archive-fill');
        } else {
            // The filter is not active
            button.classList.remove('btn-secondary');
            button.classList.add('btn-outline-secondary');
            iconElement.classList.remove('bi-archive-fill');
            iconElement.classList.add('bi-archive');
        }
    });
}


/* Assistants */

async function fetchAssistants() {
    try {
        const response = await fetch(listAssistantsUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        console.log('fetchAssistants:', data);

        if (data.assistants) {
            // Clear the global assistants object
            assistants = {};

            // Populate the global assistants object
            data.assistants.forEach(assistant => {
                assistants[assistant.id] = assistant;
            });

            // Set the global data as loaded
            assistantsLoaded = true;

            // Return the global assistants object
            return assistants;
        } else {
            const parsedError = parseErrorText(data.error);
            assistantsError = parsedError.errorMessage;
            showToast("Failed to fetch assistants!", parsedError.errorMessage);
            console.error('Failed to fetch assistants!', parsedError);
            return {};
        }
    } catch (error) {
        showToast("Error fetching assistants:", error);
        console.error('Error fetching assistants:', error);
        assistantsError = error;
        return {};
    } finally {
        toggleLoading('assistants', false);
    }
}

async function fetchAssistantFoldersMapping() {
    try {
        const response = await fetch(listAssistantFoldersUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
            }
        });
        const data = await response.json();

        if (data.assistant_folders) {
            assistantFoldersMapping = data.assistant_folders;
        } else {
            showToast("Failed to fetch assistant folders!", 'No assistant_folders key in response.');
            console.error("No assistant_folders key in response:", data);
        }
    } catch (error) {
        showToast("Failed to fetch assistant folders:", error);
        console.error('Error fetching assistant folders mapping:', error);
    }
}

const assistantItemTemplate = document.getElementById("assistant-item-template").innerHTML;

function renderAssistant(assistant) {
    const assistantItem = document.createElement('div');
    assistantItem.className = 'assistant-item';
    assistantItem.id = `assistant-${assistant.id}`;

    // Get the assistant name
    const assistantName = assistant.name || 'Untitled assistant';

    // Prepare folder names string using the global mapping and folders dict
    let folderNames = 'No folders assigned';
    if (assistantFoldersMapping && assistantFoldersMapping[assistant.id]) {
        const matchingFolders = assistantFoldersMapping[assistant.id]
            .map(folderUUID => folders[folderUUID])
            .filter(folder => folder !== undefined);
        if (matchingFolders.length > 0) {
            folderNames = matchingFolders.map(folder => folder.name).join(', ');
        }
    }

    // The template context
    const data = {
        assistant: assistant,
        assistantName: assistantName,
        folderNames: folderNames
    };

    // Compile the template into a function
    const renderTemplate = compileTemplate(assistantItemTemplate);

    // Create the inner HTML for the assistant item
    assistantItem.innerHTML = renderTemplate(data);

    return assistantItem;
}

function displayAssistants() {
    const assistantsList = document.getElementById('assistants-list');

    // Dispose of existing tooltips within the assistants list
    disposeTooltips(assistantsList);

    assistantsList.innerHTML = ''; // Clear any existing assistants

    const totalAssistants = Object.values(assistants).length;

    // Convert the assistants object into an array
    let assistantsArray = Object.values(assistants);

    // Apply filters
    assistantsArray = assistantsArray.filter(assistant => {
        // Filter by name
        if (assistantFilters.name && !(assistant.name || 'Untitled assistant').toLowerCase().includes(assistantFilters.name)) {
            return false;
        }
        // Filter by creation date
        const assistantDate = new Date(assistant.created_at * 1000);
        if (assistantFilters.startDate && assistantDate < assistantFilters.startDate) {
            return false;
        }
        if (assistantFilters.endDate && assistantDate > assistantFilters.endDate) {
            return false;
        }
        // Filter by folder
        if (assistantFilters.folderId) {
            const folderUUIDs = (assistantFoldersMapping && assistantFoldersMapping[assistant.id]) || [];
            if (assistantFilters.folderId === "none") {
                if (folderUUIDs.length > 0) {
                    return false;
                }
            } else {
                if (!folderUUIDs.includes(assistantFilters.folderId)) {
                    return false;
                }
            }
        }
        // Filter by model
        if (assistantFilters.model && assistant.model !== assistantFilters.model) {
            return false;
        }
        return true;
    });

    const filteredAssistantsCount = assistantsArray.length;

    // Update the assistants count display only if filters are active
    const assistantsCountElement = document.getElementById('assistants-count');
    if (areFiltersActive(assistantFilters)) {
        assistantsCountElement.textContent = `${filteredAssistantsCount} results (${totalAssistants} total)`;
        assistantsCountElement.style.display = 'inline';
    } else {
        assistantsCountElement.style.display = 'none';
    }

    // Handle different cases based on total assistants and filtered assistants
    if (totalAssistants === 0) {
        // No assistants exist at all
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4 no-assistants-message';
        messageDiv.innerHTML = `
            <p class="text-secondary">No assistants found.</p>
            <span class="text-secondary">
                <a href="#" class="text-decoration-none"><i class="bi bi-plus-lg"></i>Add your first assistant.</a>
            </span>
        `;
        assistantsList.appendChild(messageDiv);
        return;
    } else if (assistantsArray.length === 0) {
        // Assistants exist, but none match the filters
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4';
        messageDiv.innerHTML = `
            <p class="text-secondary">No assistants match your filters.</p>
            <span class="text-secondary">You can
            <a href="#" class="text-decoration-none" onclick="resetAssistantFilters()">reset the filters</a>
            to see all assistants.</span>
        `;
        assistantsList.appendChild(messageDiv);
        return;
    }

    // Sort the array according to the selected sort options
    assistantsArray.sort((a, b) => {
        let compareResult = 0;

        if (assistantSortField === 'name') {
            compareResult = (a.name || 'Untitled assistant').localeCompare(b.name || 'Untitled assistant');
        } else if (assistantSortField === 'created_at') {
            compareResult = a.created_at - b.created_at;
        }

        return assistantSortOrder === 'asc' ? compareResult : -compareResult;
    });

    // Iterate over the sorted and filtered array and append each item
    for (const assistant of assistantsArray) {
        const assistantItem = renderAssistant(assistant);
        assistantsList.appendChild(assistantItem);
    }

    // Re-initialize tooltips after updating the DOM
    initializeTooltips();
}

// Redirect to Assistants tab
async function editAssistant(assistantId) {
    console.log("Editing assistant:", assistantId);
    const assistantsTabTrigger = document.getElementById('assistantsTab');
    if (assistantsTabTrigger && !assistantsTabTrigger.classList.contains('active')) {
        assistantsTabTrigger.click();
    }
    await waitForContainerAndTarget('assistants-tab-container', 'assistants-tab', assistantId, function(targetTabLink) {
        let tabInstance = bootstrap.Tab.getInstance(targetTabLink);
        if (!tabInstance) {
            tabInstance = new bootstrap.Tab(targetTabLink);
        }
        tabInstance.show();
    });
}


/* Tools */

async function fetchFunctions() {
    try {
        const response = await fetch(listFunctionsUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (data.functions) {
            // Clear the global functions object
            functions = {};

            // Populate the global functions object
            data.functions.forEach(func => {
                functions[func.uuid] = func;
            });

            // Return the global functions object
            return functions;
        } else {
            const parsedError = parseErrorText(data.error);
            showToast("Failed to fetch functions!", parsedError.errorMessage);
            console.error('Failed to fetch functions!', parsedError);
            return {};
        }
    } catch (error) {
        showToast("Error fetching functions:", error);
        console.error('Error fetching functions:', error);
        return {};
    } finally {
        toggleLoading('functions', false);
    }
}

const functionItemTemplate = document.getElementById("function-item-template").innerHTML;

function renderFunction(func) {
    const functionItem = document.createElement('div');
    functionItem.className = 'function-item';
    functionItem.id = `function-${func.id}`;

    // The template context
    const data = {
        func: func,
    };

    // Compile the template into a function
    const renderTemplate = compileTemplate(functionItemTemplate);

    // Create the inner HTML for the assistant item
    functionItem.innerHTML = renderTemplate(data);

    return functionItem;
}

function displayFunctions() {
    const functionsList = document.getElementById('functions-list');

    // Dispose of existing tooltips within the functions list
    disposeTooltips(functionsList);

    functionsList.innerHTML = '';  // Clear any existing functions

    const totalFunctions = Object.values(functions).length;

    // Convert the functions object into an array
    let functionsArray = Object.values(functions);

    // Apply filters
    functionsArray = functionsArray.filter(func => {
        // Filter by name
        if (functionFilters.name && !func.name.toLowerCase().includes(functionFilters.name)) {
            return false;
        }
        // Filter by function type
        if (functionFilters.type !== functionFilters.type) {
            return false;
        }
        return true;
    });

    const filteredFunctionsCount = functionsArray.length;

    // Handle different cases based on total functions and filtered functions
    if (totalFunctions === 0) {
        // No functions exist at all
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4';
        messageDiv.innerHTML = `
            <p class="text-secondary">No functions found.</p>
            <span class="text-secondary">
                <a href="#" class="text-decoration-none"><i class="bi bi-plus-lg"></i>Add your first function.</a>
            </span>
        `;
        functionsList.appendChild(messageDiv);
        return;
    } else if (functionsArray.length === 0) {
        // Functions exist, but none match the filters
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4';
        messageDiv.innerHTML = `
            <p class="text-secondary">No functions match your filters.</p>
            <span class="text-secondary">You can
            <a href="#" class="text-decoration-none" onclick="resetFunctionFilters()">reset the filters</a>
            to see all functions.</span>
        `;
        functionsList.appendChild(messageDiv);
        return;
    }

    // Sort the array according to the selected sort options
    functionsArray.sort((a, b) => {
        let compareResult = 0;

        if (functionSortField === 'name') {
            compareResult = a.name.localeCompare(b.name);
        } else if (functionSortField === 'created_at') {
            compareResult = a.created_at - b.created_at;
        }

        return functionSortField === 'asc' ? compareResult : -compareResult;
    });

    // Iterate over the sorted and filtered array and append each item
    for (const func of functionsArray) {
        const functionsItem = renderFunction(func);
        functionsList.appendChild(functionsItem);
    }

    // Re-initialize tooltips after updating the DOM
    initializeTooltips();
}

// Redirect to Tools tab
async function editFunction(funcId) {
    console.log("Editing function:", funcId);
    const functionsTabTrigger = document.getElementById('toolsTab');
    if (functionsTabTrigger && !functionsTabTrigger.classList.contains('active')) {
        functionsTabTrigger.click();
    }
    await waitForContainerAndTarget('tools-tab-container', 'functions-tab', funcId, function(targetTabLink) {
        let tabInstance = bootstrap.Tab.getInstance(targetTabLink);
        if (!tabInstance) {
            tabInstance = new bootstrap.Tab(targetTabLink);
        }
        tabInstance.show();
    });
}


/* File Uploads */

async function showUploadFileModal() {
    const folderCheckboxes = document.getElementById('folderCheckboxes');
    folderCheckboxes.innerHTML = ''; // Clear previous checkboxes

    if (Object.keys(folders).length === 0) {
        folderCheckboxes.innerHTML = '<p class="text-muted small">No folder available</p>';
    } else {
        // Dynamically generate checkboxes for each folder
        for (const [folderId, folder] of Object.entries(folders)) {
            const checkbox = document.createElement('div');
            checkbox.classList.add('form-check');

            const input = document.createElement('input');
            input.classList.add('form-check-input');
            input.type = 'checkbox';
            input.value = folderId;
            input.id = `folder-${folderId}`;

            const label = document.createElement('label');
            label.classList.add('form-check-label');
            label.setAttribute('for', `folder-${folderId}`);
            label.textContent = folder.name ?? 'Untitled folder';

            checkbox.appendChild(input);
            checkbox.appendChild(label);
            folderCheckboxes.appendChild(checkbox);
        }
    }

    // Disable the upload button if no files are selected
    const uploadBtn = document.getElementById('uploadBtn');
    if (selectedFiles.length === 0) {
        uploadBtn.disabled = true;
    } else {
        uploadBtn.disabled = false;
    }

    const uploadFileModal = new bootstrap.Modal(document.getElementById('uploadFileModal'));
    uploadFileModal.show();
}

// Handle file selection when the user clicks the input
function handleFileSelect(event) {
    const files = event.target.files;
    addFilesToList(files);
}

// Handle drop event
function handleDrop(event) {
    event.preventDefault();
    event.target.classList.remove('hover');
    const files = event.dataTransfer.files;
    addFilesToList(files);
}

// Handle dragover event
function handleDragOver(event) {
    event.preventDefault();
    event.target.classList.add('hover');
}

// Handle dragleave event
function handleDragLeave(event) {
    event.target.classList.remove('hover');
}

// Add selected or dropped files to the list
function addFilesToList(files) {
    const uploadedFilesList = document.getElementById('uploaded-files-list');
    const uploadedFilesSection = document.getElementById('uploaded-files-section');
    const uploadBtn = document.getElementById('uploadBtn');

    // Show "Selected Files" section if files are selected
    uploadedFilesSection.classList.remove('d-none');

    // Add each selected file to the list and the selectedFiles array
    for (const file of files) {
        selectedFiles.push(file);

        // Create a list item for each file
        const li = document.createElement('li');
        li.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center');

        // Create a container for filename and file size
        const fileInfoDiv = document.createElement('div');
        fileInfoDiv.classList.add('d-flex', 'align-items-center');

        // Check if the file type is supported
        const isSupported = isSupportedFileType(file.name);

        // Add an icon for unsupported files
        const icon = document.createElement('i');
        if (!isSupported) {
            // For unsupported files, add "x-circle" icon
            icon.classList.add('bi', 'bi-x-circle-fill', 'text-danger', 'me-2', 'ms-2');
        } else {
            // For supported files, add spacing classes (no icon)
            icon.classList.add('me-2', 'ms-2');
        }
        fileInfoDiv.appendChild(icon);

        // Truncate filename if it's too long
        const maxLength = 30;
        let displayedName = file.name;
        if (file.name.length > maxLength) {
            displayedName = file.name.substring(0, maxLength) + '...';
        }

        // Create a span to display the filename with tooltip for the full name
        const filenameSpan = document.createElement('span');
        filenameSpan.classList.add('filename', 'small');
        filenameSpan.textContent = displayedName;
        filenameSpan.setAttribute('title', file.name);  // Tooltip with the full filename

        // Add the filename to the div
        fileInfoDiv.appendChild(filenameSpan);

        // Create a span to display the file size
        const fileSizeSpan = document.createElement('span');
        fileSizeSpan.classList.add('small', 'ms-2');
        fileSizeSpan.textContent = bytesToSize(file.size);

        // Add the file size span to the file info div
        fileInfoDiv.appendChild(fileSizeSpan);

        // Append the file info div to the list item
        li.appendChild(fileInfoDiv);

        // Create a remove icon on the right side
        const removeIcon = document.createElement('i');
        removeIcon.classList.add('bi', 'bi-x', 'text-muted', 'me-2', 'ms-2');
        removeIcon.style.cursor = 'pointer';
        li.appendChild(removeIcon);

        // Add click event listener to remove the file
        removeIcon.addEventListener('click', function() {
            // Find the index of the file in the selectedFiles array and remove it
            const fileIndex = selectedFiles.indexOf(file);
            if (fileIndex > -1) {
                selectedFiles.splice(fileIndex, 1);
            }

            // Remove the list item from the DOM
            li.remove();

            // If no files are left, hide the "Selected Files" section
            if (selectedFiles.length === 0) {
                uploadedFilesSection.classList.add('d-none');
                // Disable the upload button
                uploadBtn.disabled = true;
            }

            // Update the hidden file input with the updated list of selected files
            const fileInput = document.getElementById('fileUploadInput');
            fileInput.files = new FileListItems(selectedFiles);
        });

        // Append the list item to the uploaded files list
        uploadedFilesList.appendChild(li);

        // Initialize the tooltip for this file
        new bootstrap.Tooltip(filenameSpan);
    }

    // Enable the upload button since files are selected
    uploadBtn.disabled = false;

    // Update hidden file input with selected files
    const fileInput = document.getElementById('fileUploadInput');
    fileInput.files = new FileListItems(selectedFiles);
}

// Create a FileList object from array
function FileListItems(files) {
    const b = new ClipboardEvent("").clipboardData || new DataTransfer();
    for (let i = 0, len = files.length; i < len; i++) b.items.add(files[i]);
    return b.files;
}

// Handle the actual upload when the "Upload Files" button is clicked
async function uploadFiles() {
    const fileInput = document.getElementById('fileUploadInput');
    const folderCheckboxes = document.querySelectorAll('#folderCheckboxes .form-check-input');
    const selectedFolders = Array.from(folderCheckboxes)
        .filter(checkbox => checkbox.checked)
        .map(checkbox => checkbox.value);
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadSpinner = document.getElementById('upload-spinner');
    const dropZone = document.getElementById('dropZone');

    if (fileInput.files.length === 0) {
        showToast('No file selected!', 'Please select at least one file.');
        return;
    }

    const formData = new FormData();

    // Append files to the FormData object
    for (let i = 0; i < fileInput.files.length; i++) {
        formData.append('files', fileInput.files[i]);
    }

    // Append selected folders
    selectedFolders.forEach(folderId => {
        formData.append('folder_ids', folderId);
    });

    // Show spinner and disable button/dropzone
    uploadSpinner.classList.remove('d-none');
    uploadBtn.disabled = true;
    dropZone.classList.add('disabled');

    try {
        const response = await fetch(uploadFilesUrl, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: formData
        });

        if (response.ok) {
            const result = await response.json();

            console.log(result);

            // Extract filenames
            const uploadedFilenames = result.uploaded_files.map(file => file.filename).join(', ');
            const failedFilenames = result.failed_files.map(file => file.filename).join(', ');

            // Update the global files and folder relation states
            result.uploaded_files.forEach(file => {
                // Add the uploaded files to the global files dict
                files[file.id] = file;

                // Only update folders for supported_files
                if (isSupportedFileType(file.filename)) {
                    // Update fileFolders
                    fileFolders[file.id] = selectedFolders;  // Set the selected folders for the uploaded file

                    // Update folderFiles
                    selectedFolders.forEach(folderId => {
                        if (!folderFiles[folderId]) {
                            folderFiles[folderId] = [];
                        }
                        folderFiles[folderId].push(file.id);  // Add the file to the folder
                    });
                }
            });

            console.log('fileFolders:', fileFolders);
            console.log('folderFiles:', folderFiles);

            // Re-display the files list
            displayFiles();

            displayFolders(); // Re-render folder cards to reflect updated files
            populateFunctionFilterOptions(); // Update file filters to reflect new files

            // Hide the modal after successful upload
            const modal = bootstrap.Modal.getInstance(document.getElementById('uploadFileModal'));
            modal.hide();

            if (uploadedFilenames) {
                showToast("Files uploaded!", uploadedFilenames, "success");
            }
            if (failedFilenames) {
                showToast("Failed to upload!", failedFilenames, "danger");
            }

            // Clear the file input and reset the form
            selectedFiles = [];
            document.getElementById('uploaded-files-list').innerHTML = "";
            document.getElementById('fileUploadInput').value = "";
            document.getElementById('dropzone-text').textContent = 'Drop your files here';
            document.getElementById('uploaded-files-section').classList.add('d-none');
        } else {
            const errorData = await response.json();
            const parsedError = parseErrorText(errorData.error);
            showToast("Failed to upload files!", parsedError.errorMessage);
            console.error('Failed to upload files!', parsedError);
        }
    } catch (error) {
        showToast("Unexpected error:", error);
        console.error('Unexpected error:', error);
    } finally {
        // Hide spinner and re-enable button/dropzone
        uploadSpinner.classList.add('d-none');
        uploadBtn.disabled = false;
        dropZone.classList.remove('disabled');
    }
}

// Trigger the file selection dialog when the dropzone is clicked
document.getElementById('dropZone').addEventListener('click', () => {
    document.getElementById('fileUploadInput').click();
});


document.addEventListener('DOMContentLoaded', function() {
    // Call initializeTooltips on page load
    initializeTooltips();

    // Initialize sorting dropdowns
    new bootstrap.Dropdown(document.getElementById('assistantSortDropdown'));
    new bootstrap.Dropdown(document.getElementById('folderSortDropdown'));
    new bootstrap.Dropdown(document.getElementById('functionSortDropdown'));

    // Initialize filter icons
    updateFilterIcon('assistantFilterDropdown', assistantFilters);
    updateFilterIcon('folderFilterDropdown', folderFilters);
    updateFilterIcon('functionFilterDropdown', functionFilters);
});
