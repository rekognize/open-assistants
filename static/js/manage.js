/* Utility functions */

function compileTemplate(templateString) {
    /**
    * Compiles an ES6 template literal string into a function that accepts a data object.
    * Using `with(data)` lets you reference properties directly (e.g. assistant.id).
    */
    return new Function("data", "with(data) { return `" + templateString + "`; }");
}

function getStatusIcon(status) {
    switch(status) {
        case 'expired':
            return '<i class="bi bi-x-circle-fill text-danger"></i>'; // Danger icon for expired status
        case 'in_progress':
            return '<i class="bi bi-exclamation-triangle-fill text-warning"></i>'; // Warning icon for in_progress status
        case 'completed':
            return '<i class="bi bi-check-circle-fill text-success"></i>'; // Success icon for completed status
        default:
            return '<i class="bi bi-question-circle-fill text-secondary"></i>'; // Default icon for unknown status
    }
}

function renderFileVSList(vsList) {
    let rendered = '<div class="info-box"><span class="info-label">Vector Store(s)</span>';

    if (vsList) {
        rendered += '<p class="info-value">'
        vsList.forEach(vsId => {
            const vectorStore = vectorStores[vsId]; // Fetch the vector store from the global object
            rendered += `
                <span class="d-block">${vectorStore.name ?? 'Untitled store'}</span>
            `;
        });
        rendered += '</p>'
    } else {
        rendered += '<p class="info-value">No vector store</p>'
    }
    rendered += '</div>'

    return rendered;
}

function renderFileVSSelect(fileId) {
    let selectedVectorStoreIds = fileVectorStores[fileId] || []
    let checkBoxes = '<span class="text-muted small">Vector Store(s)</span>';
    const fileName = files[fileId].filename; // Get the file name

    // Check if the file type is supported
    if (!isSupportedFileType(fileName)) {
        checkBoxes += `
        <div class="text-muted small">Unsupported file type</div>`;  // Display unsupported file type message
        return checkBoxes
    }

    // First list the vector stores the file belongs to
    for (const vsId of selectedVectorStoreIds) {
        const vs = vectorStores[vsId];
        checkBoxes += `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${vsId}" id="vs-check-${vsId}" checked
                    onchange="toggleVectorStore('${fileId}', '${vsId}', this.checked)">
                <label class="form-check-label" for="vs-check-${vsId}">
                    ${vs.name ?? 'Untitled store'}
                </label>
            </div>
        `;
    }

    // Then list the other vector stores
    for (const [vsId, vectorStore] of Object.entries(vectorStores)) {
        if (selectedVectorStoreIds.indexOf(vsId) === -1) {
            checkBoxes += `
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" value="${vsId}" id="vs-check-${vsId}"
                        onchange="toggleVectorStore('${fileId}', '${vsId}', this.checked)">
                    <label class="form-check-label" for="vs-check-${vsId}">
                        ${vectorStore.name ?? 'Untitled store'}
                    </label>
                </div>
            `;
        }
    }

    return checkBoxes;
}

function toggleAssistantFileSearch(assistantId) {
    const fileSearchSwitch = document.getElementById(`fileSearchSwitch-${assistantId}`);
    const vectorStoreDiv = document.getElementById(`vector-store-div-${assistantId}`);
    if (fileSearchSwitch.checked) {
        vectorStoreDiv.style.display = 'block';
    } else {
        vectorStoreDiv.style.display = 'none';
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

function toggleEditMode(id, type) {
    const cardBody = document.getElementById(`${id}`);
    const card = cardBody.closest('.card');
    const cardFooter = card.querySelector('.card-footer');

    // Toggle brief-info and edit-mode in the card body
    const briefInfoBody = cardBody.querySelector('.brief-info');
    const editModeBody = cardBody.querySelector('.edit-mode');
    briefInfoBody.classList.toggle('d-none');
    editModeBody.classList.toggle('d-none');

    // Toggle brief-info and edit-mode in the card footer
    const briefInfoFooter = cardFooter.querySelectorAll('.brief-info');
    const editModeFooter = cardFooter.querySelectorAll('.edit-mode');
    briefInfoFooter.forEach(element => element.classList.toggle('d-none'));
    editModeFooter.forEach(element => element.classList.toggle('d-none'));

    if (!briefInfoBody.classList.contains('d-none')) {
        // Exiting edit mode
        card.classList.remove('border-warning');
    } else {
        // Entering edit mode
        card.classList.add('border-warning');

        // Reset the form fields
        if (type === 'assistant') {
            const assistant = assistants[id];
            document.getElementById(`name-${id}`).value = assistant.name || '';
            document.getElementById(`description-${id}`).value = assistant.description || '';
            document.getElementById(`instructions-${id}`).value = assistant.instructions || '';
            document.getElementById(`model-${id}`).value = assistant.model || 'gpt-4o';

            // Initialize switches
            const fileSearchSwitch = document.getElementById(`fileSearchSwitch-${id}`);
            const codeInterpreterSwitch = document.getElementById(`codeInterpreterSwitch-${id}`);

            if (fileSearchSwitch) {
                const hasFileSearch = assistant.tools.some(tool => tool.type === 'file_search');
                fileSearchSwitch.checked = hasFileSearch;

                // Initialize vector store visibility
                toggleAssistantFileSearch(id);
            }

            if (codeInterpreterSwitch) {
                codeInterpreterSwitch.checked = assistant.tools.some(tool => tool.type === 'code_interpreter');
            }

            // Reset the vector store dropdown to original value
            const vsDropdownContainer = document.getElementById(`vector-store-div-${id}`);
            if (vsDropdownContainer) {
                const selectHtml = renderAssistantVSSelect(id);  // Re-render dropdown with original data
                vsDropdownContainer.innerHTML = `
                    ${selectHtml}
                    <label for="vs-${id}">Vector store</label>
                `;  // Update the dropdown HTML and re-add the label
            }

            // Initialize functions checkboxes
            renderFunctionCheckboxes(id);

            // Check the functions that are already selected
            const functionTools = assistant.tools.filter(tool => tool.type === 'function');
            functionTools.forEach(funcTool => {
                const functionName = funcTool.function.name;
                const checkbox = document.getElementById(`function-${functionName}-${id}`);
                if (checkbox) {
                    checkbox.checked = true;
                }
            });

            // Initialize metadata fields
            initializeMetadataFields(id, assistant.metadata);

            // Scroll to the assistant's card
            const assistantCard = document.getElementById(`assistant-${id}`);
            if (assistantCard) {
                assistantCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        } else if (type === 'vectorStore') {
            const vectorStore = vectorStores[id];
            document.getElementById(`name-${id}`).value = vectorStore.name || '';
            document.getElementById(`expiration-days-${id}`).value = vectorStore.expires_after?.days || '';
            // Initialize metadata fields
            initializeMetadataFields(id, vectorStore.metadata);

            // Scroll to the vector store's card
            const vectorStoreCard = document.getElementById(`vector-store-${id}`);
            if (vectorStoreCard) {
                vectorStoreCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        } else if (type === 'file') {
            const file = files[id];
            const checkboxes = cardBody.querySelectorAll('.form-check-input');
            checkboxes.forEach(checkbox => {
                const vectorStoreId = checkbox.value;
                const isSelected = fileVectorStores[file.id]?.includes(vectorStoreId);
                checkbox.checked = isSelected;
            });

            // Scroll to the file's card
            const fileCard = document.getElementById(`file-${id}`);
            if (fileCard) {
                fileCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    }
}

function initializeMetadataFields(id, metadata) {
    const metadataFieldsContainer = document.getElementById(`metadata-fields-${id}`);
    metadataFieldsContainer.innerHTML = ''; // Clear existing fields

    if (metadata) {
        Object.entries(metadata).forEach(([key, value]) => {
            addMetadataField(id);
            const index = metadataFieldsContainer.children.length - 1;
            document.getElementById(`metadata-key-${id}-${index}`).value = key;
            document.getElementById(`metadata-value-${id}-${index}`).value = value;
        });
    }
}

function addMetadataField(id) {
    const metadataFieldsContainer = document.getElementById(`metadata-fields-${id}`);

    // Create a unique index for each metadata entry
    const index = metadataFieldsContainer.children.length;

    const metadataRow = document.createElement('div');
    metadataRow.classList.add('row', 'mb-2', 'metadata-row');
    metadataRow.setAttribute('data-index', index);

    metadataRow.innerHTML = `
        <div class="col-5">
            <input type="text" class="form-control form-control-sm" id="metadata-key-${id}-${index}" placeholder="Name">
        </div>
        <div class="col-5">
            <input type="text" class="form-control form-control-sm" id="metadata-value-${id}-${index}" placeholder="Value">
        </div>
        <div class="col-2 text-end">
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="removeMetadataField('${id}', ${index})">
                <i class="bi bi-x-lg"></i>
            </button>
        </div>
    `;

    metadataFieldsContainer.appendChild(metadataRow);
}

function removeMetadataField(id, index) {
    const metadataFieldsContainer = document.getElementById(`metadata-fields-${id}`);
    const metadataRow = metadataFieldsContainer.querySelector(`.metadata-row[data-index="${index}"]`);
    if (metadataRow) {
        metadataFieldsContainer.removeChild(metadataRow);
    }
}

function collectMetadata(id) {
    const metadataFieldsContainer = document.getElementById(`metadata-fields-${id}`);
    const metadataRows = metadataFieldsContainer.querySelectorAll('.metadata-row');
    const metadata = {};

    metadataRows.forEach(row => {
        const index = row.getAttribute('data-index');
        const key = document.getElementById(`metadata-key-${id}-${index}`).value.trim();
        const value = document.getElementById(`metadata-value-${id}-${index}`).value.trim();
        if (key && value) {
            metadata[key] = value;
        }
    });

    return metadata;  // Always return an object
}


/* Loading components and orchestration of the flow */

// Global dicts to store the current references of objects as id: object items

let vectorStores = {};
let assistants = {};
let files = {};
let vectorStoreFiles = {};  // {vsId: [file1, file2, ...]}
let fileVectorStores = {};  // {fileId: [vs1, vs2, ...]}
let selectedFiles = [];

// Global variables for sorting and filtering

let assistantSortField = 'created_at'; // default sort field
let assistantSortOrder = 'desc';       // default sort order
let assistantFilters = {
    name: '',
    startDate: null,
    endDate: null,
    vectorStoreId: '',
    model: ''
};
let vectorStoreSortField = 'created_at'; // default sort field
let vectorStoreSortOrder = 'desc';       // default sort order
let vectorStoreFilters = {
    name: '',
    startDate: null,
    endDate: null,
    status: '',
    hasExpiration: ''
};
let fileSortField = 'created_at'; // default sort field
let fileSortOrder = 'desc';       // default sort order
let fileFilters = {
    name: '',
    startDate: null,
    endDate: null,
    vectorStoreId: '',
    fileType: ''
};


async function loadAndDisplayVectorStores() {
    const vectorStores = await fetchVectorStores();
    displayVectorStores(vectorStores);
    return vectorStores;
}

async function loadAndDisplayAssistants() {
    const assistants = await fetchAssistants();
    displayAssistants();
    return assistants;
}

async function loadAllVectorStoreFiles() {
    // Reset related objects
    vectorStoreFiles = {};
    fileVectorStores = {};

    const fetchPromises = Object.keys(vectorStores).map(vectorStoreId => fetchVectorStoreFiles(vectorStoreId));
    await Promise.all(fetchPromises);
}

async function loadAndDisplayFiles() {
    const files = await fetchFiles();
    displayFiles();
    populateFileFilterOptions();
}

// Orchestrate the flow
async function initializePage() {
    // Show loading indicator initially for all
    toggleLoading('vector-stores', true);
    toggleLoading('assistants', true);
    toggleLoading('files', true);

    vectorStores = await loadAndDisplayVectorStores();
    populateAssistantFilterOptions();
    loadAndDisplayAssistants();  // Runs in parallel with loadAllVectorStoreFiles
    await loadAllVectorStoreFiles();
    loadAndDisplayFiles();
}

document.addEventListener('DOMContentLoaded', async function() {
    // Wait for initializePage() to finish
    await initializePage();

    setTimeout(() => {
        const isVectorStoresEmpty = Object.keys(vectorStores).length === 0;
        const isAssistantsEmpty = Object.keys(assistants).length === 0;
        const isFilesEmpty = Object.keys(files).length === 0;

        if (isVectorStoresEmpty && isAssistantsEmpty && isFilesEmpty) {
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

async function refreshVSList() {
    const vectorStoresList = document.getElementById('vector-stores-list');

    // Dispose of existing tooltips within the vector stores list
    disposeTooltips(vectorStoresList);

    vectorStoresList.innerHTML = ''; // Clear any existing vector stores
    toggleLoading('vector-stores', true);

    // Reset to default sorting options
    vectorStoreSortField = 'created_at';
    vectorStoreSortOrder = 'desc';
    updateSortDropdownUI('vectorStoreSortDropdown', vectorStoreSortField, vectorStoreSortOrder);

    // Fetch and display
    await loadAndDisplayVectorStores();
    populateAssistantFilterOptions();

    // Refresh collapse all button
    const btnCollapseAllStores = document.getElementById('collapse-all-stores');
    const btnExpandAllStores = document.getElementById('expand-all-stores');
    btnCollapseAllStores.classList.remove('d-none');
    btnExpandAllStores.classList.add('d-none');

    loadAllVectorStoreFiles(); // Also refresh vector store files
}

async function refreshFilesList() {
    const filesList = document.getElementById('files-list');

    // Dispose of existing tooltips within the files list
    disposeTooltips(filesList);

    filesList.innerHTML = ''; // Clear any existing files
    toggleLoading('files', true);

    // Reset to default sorting options
    fileSortField = 'created_at';
    fileSortOrder = 'desc';
    updateSortDropdownUI('fileSortDropdown', fileSortField, fileSortOrder);

    // Close the sorting dropdown if open
    const dropdownElement = document.getElementById('fileSortDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    loadAndDisplayFiles();

    // Refresh collapse all button
    const btnCollapseAllFiles = document.getElementById('collapse-all-files');
    const btnExpandAllFiles = document.getElementById('expand-all-files');
    btnCollapseAllFiles.classList.remove('d-none');
    btnExpandAllFiles.classList.add('d-none');
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

function toggleAllStores(action) {
    const btnCollapseAllStores = document.getElementById('collapse-all-stores');
    const btnExpandAllStores = document.getElementById('expand-all-stores');
    const collapsibleItems = document.querySelectorAll('#vector-stores-list .collapse');
    collapsibleItems.forEach(item => {
        const bsCollapse = new bootstrap.Collapse(item, {
            toggle: false
        });
        if (action === 'collapse') bsCollapse.hide();
        else bsCollapse.show();
    });
    if (action === 'collapse') {
        btnCollapseAllStores.classList.add('d-none');
        btnExpandAllStores.classList.remove('d-none');
    } else {  // expand
        btnCollapseAllStores.classList.remove('d-none');
        btnExpandAllStores.classList.add('d-none');
    }
}

function toggleAllFiles(action) {
    const btnCollapseAllFiles = document.getElementById('collapse-all-files');
    const btnExpandAllFiles = document.getElementById('expand-all-files');
    const collapsibleItems = document.querySelectorAll('#files-list .collapse');
    collapsibleItems.forEach(item => {
        const bsCollapse = new bootstrap.Collapse(item, {
            toggle: false
        });
        if (action === 'collapse') bsCollapse.hide();
        else bsCollapse.show();
    });
    if (action === 'collapse') {
        btnCollapseAllFiles.classList.add('d-none');
        btnExpandAllFiles.classList.remove('d-none');
    } else {  // expand
        btnCollapseAllFiles.classList.remove('d-none');
        btnExpandAllFiles.classList.add('d-none');
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

function setVectorStoreSort(field, order, event) {
    if (event) event.preventDefault();

    vectorStoreSortField = field;
    vectorStoreSortOrder = order;

    updateSortDropdownUI('vectorStoreSortDropdown', field, order);

    displayVectorStores();

    const dropdownElement = document.getElementById('vectorStoreSortDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    // Refresh collapse all button
    const btnCollapseAllStores = document.getElementById('collapse-all-stores');
    const btnExpandAllStores = document.getElementById('expand-all-stores');
    btnCollapseAllStores.classList.remove('d-none');
    btnExpandAllStores.classList.add('d-none');
}

function setFileSort(field, order, event) {
    if (event) event.preventDefault();

    fileSortField = field;
    fileSortOrder = order;

    // Update the active class on the dropdown menu items
    updateSortDropdownUI('fileSortDropdown', field, order);

    displayFiles(); // Re-display files with new sort order

    // Close the dropdown menu
    const dropdownElement = document.getElementById('fileSortDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    // Refresh collapse all button
    const btnCollapseAllFiles = document.getElementById('collapse-all-files');
    const btnExpandAllFiles = document.getElementById('expand-all-files');
    btnCollapseAllFiles.classList.remove('d-none');
    btnExpandAllFiles.classList.add('d-none');
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

    assistantFilters.vectorStoreId = document.getElementById('filterVectorStore').value;
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
        vectorStoreId: '',
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

function applyVectorStoreFilters() {
    vectorStoreFilters.name = document.getElementById('vsFilterName').value.toLowerCase();
    vectorStoreFilters.startDate = document.getElementById('vsFilterStartDate').value
        ? new Date(document.getElementById('vsFilterStartDate').value)
        : null;
    vectorStoreFilters.endDate = document.getElementById('vsFilterEndDate').value
        ? new Date(document.getElementById('vsFilterEndDate').value)
        : null;

    // Adjust dates
    if (vectorStoreFilters.startDate) {
        vectorStoreFilters.startDate.setHours(0, 0, 0, 0);
    }
    if (vectorStoreFilters.endDate) {
        vectorStoreFilters.endDate.setHours(23, 59, 59, 999);
    }

    vectorStoreFilters.status = document.getElementById('vsFilterStatus').value;
    vectorStoreFilters.hasExpiration = document.getElementById('vsFilterHasExpiration').value;

    displayVectorStores();

    const dropdownElement = document.getElementById('vectorStoreFilterDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    updateFilterIcon('vectorStoreFilterDropdown', vectorStoreFilters);
}

function resetVectorStoreFilters() {
    document.getElementById('vectorStoreFilterForm').reset();
    vectorStoreFilters = {
        name: '',
        startDate: null,
        endDate: null,
        status: '',
        hasExpiration: ''
    };
    displayVectorStores();

    const dropdownElement = document.getElementById('vectorStoreFilterDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }

    updateFilterIcon('vectorStoreFilterDropdown', vectorStoreFilters);
}

function applyFileFilters() {
    // Read filter values
    fileFilters.name = document.getElementById('fileFilterName').value.toLowerCase();
    fileFilters.startDate = document.getElementById('fileFilterStartDate').value
        ? new Date(document.getElementById('fileFilterStartDate').value)
        : null;
    fileFilters.endDate = document.getElementById('fileFilterEndDate').value
        ? new Date(document.getElementById('fileFilterEndDate').value)
        : null;

    // Adjust dates
    if (fileFilters.startDate) {
        fileFilters.startDate.setHours(0, 0, 0, 0);
    }
    if (fileFilters.endDate) {
        fileFilters.endDate.setHours(23, 59, 59, 999);
    }

    fileFilters.vectorStoreId = document.getElementById('fileFilterVectorStore').value;
    fileFilters.fileType = document.getElementById('fileFilterType').value;

    displayFiles();

    // Update button styles and icons
    updateVectorStoreFilesButtonStyles();

    // Update the filter icon
    updateFilterIcon('fileFilterDropdown', fileFilters);

    // Close the dropdown menu
    const dropdownElement = document.getElementById('fileFilterDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }
}

function resetFileFilters() {
    document.getElementById('fileFilterForm').reset();
    fileFilters = {
        name: '',
        startDate: null,
        endDate: null,
        vectorStoreId: '',
        fileType: ''
    };

    displayFiles();

    // Update button styles and icons
    updateVectorStoreFilesButtonStyles();

    // Update the filter icon
    updateFilterIcon('fileFilterDropdown', fileFilters);

    // Close the dropdown menu
    const dropdownElement = document.getElementById('fileFilterDropdown');
    const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownElement);
    if (dropdownInstance) {
        dropdownInstance.hide();
    }
}

function populateAssistantFilterOptions() {
    const filterVectorStore = document.getElementById('filterVectorStore');
    filterVectorStore.innerHTML = '<option value="">All</option>'; // Reset options

    for (const [vsId, vectorStore] of Object.entries(vectorStores)) {
        const option = document.createElement('option');
        option.value = vsId;
        option.textContent = vectorStore.name ?? 'Untitled store';
        filterVectorStore.appendChild(option);
    }
}

function populateFileFilterOptions() {
    const filterVectorStore = document.getElementById('fileFilterVectorStore');
    filterVectorStore.innerHTML = '<option value="">All</option>'; // Reset options

    for (const [vsId, vectorStore] of Object.entries(vectorStores)) {
        const option = document.createElement('option');
        option.value = vsId;
        option.textContent = vectorStore.name ?? 'Untitled store';
        filterVectorStore.appendChild(option);
    }

    // Populate file types
    const filterFileType = document.getElementById('fileFilterType');
    filterFileType.innerHTML = '<option value="">All</option>'; // Reset options

    const fileTypes = new Set();
    for (const file of Object.values(files)) {
        fileTypes.add(getFileType(file.filename));
    }
    for (const fileType of fileTypes) {
        const option = document.createElement('option');
        option.value = fileType;
        option.textContent = fileType.toUpperCase();
        filterFileType.appendChild(option);
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
    if (field === 'name' || field === 'filename') {
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

function getFileType(filename) {
    const extension = filename.split('.').pop().toLowerCase();
    return extension;
}


/* Vector stores */

async function fetchVectorStores() {
    try {
        const response = await fetch(listVectorStoresUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (data.vector_stores) {
            // Clear the global vectorStores object
            vectorStores = {};

            // Populate the global vectorStores object
            data.vector_stores.forEach(store => {
                vectorStores[store.id] = store;

            });

            // Return the global vectorStores object
            return vectorStores;
        } else {
            const parsedError = parseErrorText(data.error);
            showToast("Failed to fetch vector stores!", parsedError.errorMessage);
            console.error('Failed to fetch vector stores!', parsedError);
            return {};
        }
    } catch (error) {
        showToast("Error fetching vector stores:", error);
        console.error('Error fetching vector stores:', error);
        return {};
    } finally {
        toggleLoading('vector-stores', false);
    }
}

async function updateVectorStoresByIds(vectorStoreIds) {
    const fetchPromises = vectorStoreIds.map(async (vsId) => {
        const retrieveVectorStoreUrl = retrieveVectorStoreUrlTemplate.replace('VS_ID_PLACEHOLDER', vsId);
        try {
            const response = await fetch(retrieveVectorStoreUrl, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${API_KEY}`,
                    'Content-Type': 'application/json',
                }
            });
            if (response.ok) {
                const data = await response.json();
                vectorStores[vsId] = data;
            } else {
                console.error(`Failed to fetch vector store with ID ${vsId}`);
            }
        } catch (error) {
            console.error(`Error fetching vector store with ID ${vsId}:`, error);
        }
    });

    await Promise.all(fetchPromises);
}

const vsItemTemplate = document.getElementById("vector-store-item-template").innerHTML;

function renderVectorStore(store) {
    const vectorStoreItem = document.createElement('div');
    vectorStoreItem.className = 'vector-store-item';
    vectorStoreItem.id = `vector-store-${store.id}`;

    const storeName = store.name || 'Untitled store';

    // Grab the raw template string from the DOM
    const data = {
        store: store,
        storeName: storeName
    };

    // Compile the template into a function
    const renderTemplate = compileTemplate(vsItemTemplate);
    vectorStoreItem.innerHTML = renderTemplate(data);

    return vectorStoreItem;
}

function displayVectorStores() {
    const vectorStoresList = document.getElementById('vector-stores-list');

    // Dispose of existing tooltips within the vector stores list
    disposeTooltips(vectorStoresList);

    vectorStoresList.innerHTML = '';

    const totalStores = Object.values(vectorStores).length;

    // Convert to array
    let vectorStoresArray = Object.values(vectorStores);

    // Apply filters
    vectorStoresArray = vectorStoresArray.filter(store => {
        // Name filter
        if (vectorStoreFilters.name && !(store.name || 'Untitled store').toLowerCase().includes(vectorStoreFilters.name)) {
            return false;
        }
        // Creation date filter
        const createdAt = new Date(store.created_at * 1000);
        if (vectorStoreFilters.startDate && createdAt < vectorStoreFilters.startDate) {
            return false;
        }
        if (vectorStoreFilters.endDate && createdAt > vectorStoreFilters.endDate) {
            return false;
        }
        // Status filter
        if (vectorStoreFilters.status && store.status !== vectorStoreFilters.status) {
            return false;
        }
        // Has expiration filter
        const hasExpiration = store.expires_at ? 'true' : 'false';
        if (vectorStoreFilters.hasExpiration && hasExpiration !== vectorStoreFilters.hasExpiration) {
            return false;
        }
        return true;
    });

    const filteredStoresCount = vectorStoresArray.length;

    // Update the stores count display only if filters are active
    const storesCountElement = document.getElementById('stores-count');
    if (areFiltersActive(vectorStoreFilters)) {
        storesCountElement.textContent = `${filteredStoresCount} results (${totalStores} total)`;
        storesCountElement.style.display = 'inline';
    } else {
        storesCountElement.style.display = 'none';
    }

    // Handle different cases based on total stores and filtered stores
    if (totalStores === 0) {
        // No vector stores exist at all
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4 no-vector-stores-message';
        messageDiv.innerHTML = `
            <p class="text-secondary">No vector stores found.</p>
            <span class="text-secondary">
                <a href="#" class="text-decoration-none" onclick="hideTooltip(this); addVectorStore()"><i class="bi bi-plus-lg"></i>Add your first vector store.</a>
            </span>
        `;
        vectorStoresList.appendChild(messageDiv);
        return;
    } else if (vectorStoresArray.length === 0) {
        // Vector stores exist, but none match the filters
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4';
        messageDiv.innerHTML = `
            <p class="text-secondary">No vector stores match your filters.</p>
            <span class="text-secondary">You can
            <a href="#" class="text-decoration-none" onclick="resetVectorStoreFilters()">reset the filters</a>
            to see all vector stores.</span>
        `;
        vectorStoresList.appendChild(messageDiv);
        return;
    }

    // Sort
    vectorStoresArray.sort((a, b) => {
        let compareResult = 0;

        if (vectorStoreSortField === 'name') {
            compareResult = (a.name || 'Untitled store').localeCompare(b.name || 'Untitled store');
        } else if (vectorStoreSortField === 'created_at') {
            compareResult = a.created_at - b.created_at;
        } else if (vectorStoreSortField === 'last_active_at') {
            compareResult = a.last_active_at - b.last_active_at;
        }

        return vectorStoreSortOrder === 'asc' ? compareResult : -compareResult;
    });

    // Display
    for (const store of vectorStoresArray) {
        const vectorStoreItem = renderVectorStore(store);
        vectorStoresList.appendChild(vectorStoreItem);
    }

    initializeTooltips();
}

async function fetchVectorStoreFiles(vectorStoreId) {
    // Fetch the files of a vectorStore and update vectorStoreFiles and fileVectorStores objects

    const url = listVSFilesUrlTemplate.replace('VS_ID_PLACEHOLDER', vectorStoreId);

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
            }
        });
        const data = await response.json();

        if (data.files) {

            // Update the global files object
            data.files.forEach(vsFile => {

                if (!vectorStoreFiles[vectorStoreId]) {
                    vectorStoreFiles[vectorStoreId] = [];
                }
                vectorStoreFiles[vectorStoreId].push(vsFile.id);

                if (!fileVectorStores[vsFile.id]) {
                    fileVectorStores[vsFile.id] = [];
                }
                fileVectorStores[vsFile.id].push(vectorStoreId);

            });

        } else {
            const parsedError = parseErrorText(data.error);
            showToast("Failed to fetch files!", parsedError.errorMessage);
            console.error('Failed to fetch files!', parsedError);
            return {};
        }
    } catch (error) {
        showToast("Error fetching files:", error);
        console.error('Error fetching files:', error);
        return {};
    }
}

function addVectorStore() {
    // Check if there is already a vector store item with an ID starting with 'temp-card-'
    const existingTempCard = document.querySelector('.vector-store-item[id^="temp-card-"]');
    if (existingTempCard) {
        // An empty card is already present, do not add another
        return;
    }

    const tempId = `temp_${Date.now()}`; // Temporary ID based on timestamp for uniqueness

    // Remove the "No vector stores found." message if present
    const vectorStoresList = document.getElementById('vector-stores-list');
    const noVectorStoresMessage = vectorStoresList.querySelector('.no-vector-stores-message');
    if (noVectorStoresMessage) {
        noVectorStoresMessage.remove();
    }

    // Create a new vector store item element
    const vectorStoreItem = document.createElement('div');
    vectorStoreItem.className = 'vector-store-item';
    vectorStoreItem.id = `temp-card-${tempId}`;

    // Create the inner HTML for the vector store item (in edit mode)
    vectorStoreItem.innerHTML = document.getElementById("vector-store-form-template").innerHTML;

    // Append the new vector store item to the vector stores list
    if (vectorStoresList.firstChild) {
        vectorStoresList.insertBefore(vectorStoreItem, vectorStoresList.firstChild);
    } else {
        vectorStoresList.appendChild(vectorStoreItem);
    }

    // Scroll to the top of vector-stores-list
    const vectorStoresListSection = document.getElementById('vector-stores-list');
    if (vectorStoresListSection) {
        vectorStoresListSection.scrollIntoView({ behavior: 'smooth' });
    }
}

function removeVectorStoreCard(vectorStoreId) {
    // Remove the vector store card
    const vsCard = document.getElementById(`temp-card-${vectorStoreId}`) || document.getElementById(`vs-${vectorStoreId}`).closest('.vector-store-item');
    if (vsCard) {
        vsCard.remove();
    }

    // Check if the vector stores list is empty
    const vectorStoresList = document.getElementById('vector-stores-list');
    const vectorStoreItems = vectorStoresList.querySelectorAll('.vector-store-item');
    if (vectorStoreItems.length === 0) {
        // Display the "No vector stores found." message
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4 no-vector-stores-message';
        messageDiv.innerHTML = `
            <p class="text-secondary">No vector stores found.</p>
            <span class="text-secondary">
                <a href="#" class="text-decoration-none" onclick="hideTooltip(this); addVectorStore()"><i class="bi bi-plus-lg"></i>Add your first vector store.</a>
            </span>
        `;
        vectorStoresList.appendChild(messageDiv);
    }
}

async function saveNewVectorStore(vectorStoreId) {
    const button = document.querySelector(`.btnModifyVectorStore[data-vector-store-id="${vectorStoreId}"]`);
    const buttonText = button.querySelector('.button-text');
    const spinner = button.querySelector('.spinner-border');

    // Show spinner and disable button
    buttonText.classList.add('d-none');
    spinner.classList.remove('d-none');
    button.disabled = true;

    const metadata = collectMetadata(vectorStoreId);

    const payload = {
        name: document.getElementById(`name-${vectorStoreId}`).value,
        expiration_days: document.getElementById(`expiration-days-${vectorStoreId}`).value,
        metadata: metadata
    };

    try {
        const response = await fetch(createVectorStoreUrl, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const data = await response.json();

            // Update the global vectorStores object
            vectorStores[data.id] = data;

            // Remove the form card and prepend the new vector store to the list
            const tempCard = document.getElementById(`temp-card-${vectorStoreId}`);
            if (tempCard) {
                tempCard.remove();
            }

            // Re-display the vector stores list
            displayVectorStores();

            // Update related UI elements
            updateVectorStoreRelatedUI();

            // Scroll to the newly added vector store's card
            const newVectorStoreId = data.id;
            const vectorStoreCard = document.getElementById(`vector-store-${newVectorStoreId}`);
            if (vectorStoreCard) {
                vectorStoreCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }

        } else {
            const errorData = await response.json();
            let errorMessage = '';

            if (errorData.error) {
                const parsedError = parseErrorText(errorData.error);
                errorMessage = parsedError.errorMessage;
            } else if (errorData.detail) {
                // Handle server errors
                if (Array.isArray(errorData.detail)) {
                    // Extract the message from the first error detail
                    errorMessage = errorData.detail[0].msg || 'Unknown error occurred.';
                } else if (typeof errorData.detail === 'string') {
                    errorMessage = errorData.detail;
                } else {
                    errorMessage = 'Unknown error occurred.';
                }
            } else {
                errorMessage = 'Unknown error occurred.';
            }

            showToast("Failed to save new vector store!", errorMessage);
            console.error('Failed to save new vector store!', errorMessage);
        }
    } catch (error) {
        showToast("Unexpected error:", error);
        console.error('Unexpected error:', error);
    } finally {
        // Hide spinner and enable button
        spinner.classList.add('d-none');
        buttonText.classList.remove('d-none');
        button.disabled = false;
    }
}

async function modifyVectorStore(vectorStoreId) {
    const button = document.querySelector(`.btnModifyVectorStore[data-store-id="${vectorStoreId}"]`);
    const buttonText = button.querySelector('.button-text');
    const spinner = button.querySelector('.spinner-border');

    // Show spinner and disable button
    buttonText.classList.add('d-none');
    spinner.classList.remove('d-none');
    button.disabled = true;

    const url = modifyVectorStoreUrlTemplate.replace('VS_ID_PLACEHOLDER', vectorStoreId);

    const metadata = collectMetadata(vectorStoreId);

    const payload = {
        name: document.getElementById(`name-${vectorStoreId}`).value,
        expiration_days: document.getElementById(`expiration-days-${vectorStoreId}`).value,
        metadata: metadata
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const data = await response.json();

            // Update the global vectorStores object
            vectorStores[vectorStoreId] = data;

            // Re-display the vector stores list
            displayVectorStores();

            // Update related UI elements
            updateVectorStoreRelatedUI();

            // Scroll to the updated vector store's card
            const vectorStoreCard = document.getElementById(`vector-store-${vectorStoreId}`);
            if (vectorStoreCard) {
                vectorStoreCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }

        } else {
            const errorData = await response.json();
            let errorMessage = '';

            if (errorData.error) {
                const parsedError = parseErrorText(errorData.error);
                errorMessage = parsedError.errorMessage;
            } else if (errorData.detail) {
                // Handle server errors
                if (Array.isArray(errorData.detail)) {
                    // Extract the message from the first error detail
                    errorMessage = errorData.detail[0].msg || 'Unknown error occurred.';
                } else if (typeof errorData.detail === 'string') {
                    errorMessage = errorData.detail;
                } else {
                    errorMessage = 'Unknown error occurred.';
                }
            } else {
                errorMessage = 'Unknown error occurred.';
            }

            showToast("Failed to update vector store!", errorMessage);
            console.error('Failed to update vector store!', errorMessage);
        }
    } catch (error) {
        showToast("Unexpected error:", error);
        console.error('Unexpected error:', error);
    } finally {
        // Hide spinner and enable button
        spinner.classList.add('d-none');
        buttonText.classList.remove('d-none');
        button.disabled = false;
    }
}

let vectorStoreToDeleteId = null; // To store the ID of the vector store to delete

async function deleteVectorStore(vectorStoreId) {
    vectorStoreToDeleteId = vectorStoreId; // Store the vector store ID for use in the confirm deletion function

    // Collect assistants using this vector store
    const assistantsUsingVS = [];
    for (const [assistantId, assistant] of Object.entries(assistants)) {
        const assignedVsId = assistant.tool_resources?.file_search?.vector_store_ids?.[0] || null;
        if (assignedVsId === vectorStoreId) {
            assistantsUsingVS.push(assistant.name || 'Untitled assistant');
        }
    }

    // Update the modal content
    const assistantsListElement = document.getElementById('assistantNamesList');
    const assistantsUsingVectorStoreDiv = document.getElementById('assistantsUsingVectorStore');
    const vectorStoreInfo = document.getElementById('vectorStoreInfo');

    // Clear previous list
    assistantsListElement.innerHTML = '';

    // Add vector store info
    vectorStoreInfo.textContent = '';
    vectorStoreInfo.textContent = vectorStores[vectorStoreId] && vectorStores[vectorStoreId].name && vectorStores[vectorStoreId].name.trim() !== '' ? vectorStores[vectorStoreId].name : 'Untitled store';

    if (assistantsUsingVS.length > 0) {
        // Show the list of assistants
        assistantsUsingVectorStoreDiv.classList.remove('d-none');
        assistantsUsingVS.forEach(name => {
            const li = document.createElement('li');
            li.textContent = name;
            assistantsListElement.appendChild(li);
        });
    } else {
        assistantsUsingVectorStoreDiv.classList.add('d-none');
    }

    // Show the modal
    const deleteModal = new bootstrap.Modal(document.getElementById('vectorStoreDeleteModal'));
    deleteModal.show();

    // Attach event listener to the confirm delete button
    const confirmDeleteBtn = document.getElementById('confirmDeleteVectorStoreBtn');
    confirmDeleteBtn.onclick = confirmDeleteVectorStore;
}

async function confirmDeleteVectorStore() {
    const vectorStoreId = vectorStoreToDeleteId;
    const deleteVectorStoreUrl = deleteVectorStoreUrlTemplate.replace('VS_ID_PLACEHOLDER', vectorStoreId);
    const vectorStoreName = vectorStores[vectorStoreId] && vectorStores[vectorStoreId].name && vectorStores[vectorStoreId].name.trim() !== '' ? vectorStores[vectorStoreId].name : 'Untitled store';

    // Hide the modal
    const deleteModal = bootstrap.Modal.getInstance(document.getElementById('vectorStoreDeleteModal'));
    deleteModal.hide();

    try {
        const response = await fetch(deleteVectorStoreUrl, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            }
        });

        if (response.ok) {
            // Remove the vector store from the global vectorStores object
            delete vectorStores[vectorStoreId];

            // Update file-vector store associations
            const associatedFiles = vectorStoreFiles[vectorStoreId] || [];
            associatedFiles.forEach(fileId => {
                // Remove vectorStoreId from fileVectorStores[fileId]
                if (fileVectorStores[fileId]) {
                    fileVectorStores[fileId] = fileVectorStores[fileId].filter(id => id !== vectorStoreId);
                }
            });

            // Remove the vector store from vectorStoreFiles
            delete vectorStoreFiles[vectorStoreId];

            // Re-display the vector stores list
            displayVectorStores();

            // Update related UI elements
            updateVectorStoreRelatedUI();

            showToast("Vector store deleted!", vectorStoreName, "success");
            console.log(`Vector Store with ID ${vectorStoreId} deleted successfully.`);
        } else {
            const errorData = await response.json();
            const parsedError = parseErrorText(errorData.error);
            showToast("Failed to delete vector store!", parsedError.errorMessage);
            console.error('Failed to delete vector store!', parsedError);
        }
    } catch (error) {
        showToast("Unexpected error:", error);
        console.error('Unexpected error:', error);
    }
}

function updateVectorStoreRelatedUI() {
    // Update the assistant filter dropdown
    populateAssistantFilterOptions();

    // Update the file filter dropdown
    populateFileFilterOptions();

    // Re-display assistants to reflect the new vector store
    displayAssistants();

    // Update all file cards to reflect the updated list of vector stores
    displayFiles();

    // Re-initialize tooltips if necessary
    initializeTooltips();
}

function toggleFileFilterByVectorStore(storeId, buttonElement) {
    hideTooltip(buttonElement);

    if (fileFilters.vectorStoreId === storeId) {
        // Remove the vector store filter
        fileFilters.vectorStoreId = '';
    } else {
        // Set the vector store filter to this storeId
        fileFilters.vectorStoreId = storeId;
    }

    // Update the file filter dropdown to reflect the selected vector store
    document.getElementById('fileFilterVectorStore').value = fileFilters.vectorStoreId;

    // Update the styles and icons of all vector store 'Files' buttons
    updateVectorStoreFilesButtonStyles();

    // Display the files with the updated filters
    displayFiles();

    // Update the file filter icon based on active filters
    updateFilterIcon('fileFilterDropdown', fileFilters);
}

function updateVectorStoreFilesButtonStyles() {
    const buttons = document.querySelectorAll('.vector-store-files-button');
    buttons.forEach(button => {
        const storeId = button.getAttribute('data-store-id');
        const iconElement = button.querySelector('i');

        if (fileFilters.vectorStoreId === storeId && fileFilters.vectorStoreId !== '') {
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

        if (data.assistants) {
            // Clear the global assistants object
            assistants = {};

            // Populate the global assistants object
            data.assistants.forEach(assistant => {
                assistants[assistant.id] = assistant;
            });

            // Return the global assistants object
            return assistants;
        } else {
            const parsedError = parseErrorText(data.error);
            showToast("Failed to fetch assistants!", parsedError.errorMessage);
            console.error('Failed to fetch assistants!', parsedError);
            return {};
        }
    } catch (error) {
        showToast("Error fetching assistants:", error);
        console.error('Error fetching assistants:', error);
        return {};
    } finally {
        toggleLoading('assistants', false);
    }
}

function renderAssistantVSSelect(assistantId) {
    let selectedVectorStoreId = null;
    if (assistantId && assistants[assistantId])
        selectedVectorStoreId = assistants[assistantId].tool_resources?.file_search?.vector_store_ids?.[0] || null;

    // Start building the HTML for the select element
    let selectHtml = `<select class="form-select vector-store" id="vs-${assistantId}">`;

    // Add the null option
    selectHtml += '<option value="">No vector store assigned</option>';

    // Iterate over the global vectorStores object to create options
    for (const [vsId, vectorStore] of Object.entries(vectorStores)) {
        const isSelected = vsId === selectedVectorStoreId ? 'selected' : '';
        selectHtml += `<option value="${vsId}" ${isSelected}>${vectorStore.name ?? 'Untitled store'}</option>`;
    }

    // Close the select element
    selectHtml += '</select>';

    return selectHtml;
}

const assistantItemTemplate = document.getElementById("assistant-item-template").innerHTML;

function renderAssistant(assistant) {
    const assistantItem = document.createElement('div');
    assistantItem.className = 'assistant-item';
    assistantItem.id = `assistant-${assistant.id}`;

    // Get the assistant name
    const assistantName = assistant.name || 'Untitled assistant';

    // Get the vector store name
    let vs_name = 'No vector store assigned';  // Default if not assigned
    const vs_id = assistant.tool_resources?.file_search?.vector_store_ids?.[0] || null;

    if (vs_id && vectorStores[vs_id]) {
        vs_name = vectorStores[vs_id].name ?? 'Untitled store';
    }

    const selectVectorStore = renderAssistantVSSelect(assistant.id);

    // The template context
    const data = {
        assistant: assistant,
        assistantName: assistantName,
        vs_id: vs_id,
        vs_name: vs_name,
        selectVectorStore: selectVectorStore
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
        // Filter by vector store
        const assignedVsId = assistant.tool_resources?.file_search?.vector_store_ids?.[0] || null;
        if (assistantFilters.vectorStoreId && assignedVsId !== assistantFilters.vectorStoreId) {
            return false;
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
                <a href="#" class="text-decoration-none" onclick="hideTooltip(this); addAssistant()"><i class="bi bi-plus-lg"></i>Add your first assistant.</a>
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

function addAssistant() {
    // Check if there is already an assistant item with an ID starting with 'temp-card-'
    const existingTempCard = document.querySelector('.assistant-item[id^="temp-card-"]');
    if (existingTempCard) {
        // An empty card is already present, do not add another
        return;
    }

    const tempId = `temp_${Date.now()}`; // Temporary ID based on timestamp for uniqueness

    // Remove the "No assistants found." message if present
    const assistantsList = document.getElementById('assistants-list');
    const noAssistantsMessage = assistantsList.querySelector('.no-assistants-message');
    if (noAssistantsMessage) {
        noAssistantsMessage.remove();
    }

    // Create a new assistant item element
    const assistantItem = document.createElement('div');
    assistantItem.className = 'assistant-item';
    assistantItem.id = `temp-card-${tempId}`;

    // Render the vector store select element for the new assistant
    const selectVectorStore = renderAssistantVSSelect(tempId);

    // Create the inner HTML for the assistant item (in edit mode)
    assistantItem.innerHTML = document.getElementById("assistant-form-template").innerHTML;

    // Append the new assistant item to the assistants list
    if (assistantsList.firstChild) {
        assistantsList.insertBefore(assistantItem, assistantsList.firstChild);
    } else {
        assistantsList.appendChild(assistantItem);
    }
    renderFunctionCheckboxes(tempId);

    // Scroll to the top of assistants-list
    const assistantsListSection = document.getElementById('assistants-list');
    if (assistantsListSection) {
        assistantsListSection.scrollIntoView({ behavior: 'smooth' });
    }
}

function removeAssistantCard(assistantId) {
    // Remove the assistant card
    const assistantCard = document.getElementById(`temp-card-${assistantId}`) || document.getElementById(`assistant-${assistantId}`).closest('.assistant-item');
    if (assistantCard) {
        assistantCard.remove();
    }

    // Check if the assistants list is empty
    const assistantsList = document.getElementById('assistants-list');
    const assistantItems = assistantsList.querySelectorAll('.assistant-item');
    if (assistantItems.length === 0) {
        // Display the "No assistants found." message
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4 no-assistants-message';
        messageDiv.innerHTML = `
            <p class="text-secondary">No assistants found.</p>
            <span class="text-secondary">
                <a href="#" class="text-decoration-none" onclick="hideTooltip(this); addAssistant()"><i class="bi bi-plus-lg"></i>Add your first assistant.</a>
            </span>
        `;
        assistantsList.appendChild(messageDiv);
    }
}

async function saveNewAssistant(assistantId) {
    const button = document.querySelector(`.btnModifyAssistant[data-assistant-id="${assistantId}"]`);
    const buttonText = button.querySelector('.button-text');
    const spinner = button.querySelector('.spinner-border');

    // Show spinner and disable button
    buttonText.classList.add('d-none');
    spinner.classList.remove('d-none');
    button.disabled = true;

    const fileSearchSwitch = document.getElementById(`fileSearchSwitch-${assistantId}`);
    const fileSearchEnabled = fileSearchSwitch ? fileSearchSwitch.checked : false;
    const codeInterpreterSwitch = document.getElementById(`codeInterpreterSwitch-${assistantId}`);
    const codeInterpreterEnabled = codeInterpreterSwitch ? codeInterpreterSwitch.checked : false;
    const vectorStoreId = fileSearchEnabled ? document.getElementById(`vs-${assistantId}`).value : null;

    // Collect selected functions
    const selectedFunctionNames = [];
    const functionCheckboxes = document.querySelectorAll(`input[id^="function-"][id$="-${assistantId}"]:checked`);
    functionCheckboxes.forEach(checkbox => {
        selectedFunctionNames.push(checkbox.value);
    });

    // For each selected function name, find the function definition
    const selectedFunctions = functionDefinitions.filter(funcDef => selectedFunctionNames.includes(funcDef.name));

    // Build tools array based on switches
    const tools = [];
    if (codeInterpreterEnabled) {
        tools.push({ "type": "code_interpreter" });
    }
    if (fileSearchEnabled) {
        tools.push({ "type": "file_search" });
    }
    // Add selected functions to tools
    selectedFunctions.forEach(funcDef => {
        tools.push({
            "type": "function",
            "function": funcDef
        });
    });

    // Build tool_resources
    const tool_resources = {};
    if (fileSearchEnabled && vectorStoreId) {
        tool_resources["file_search"] = {
            "vector_store_ids": [vectorStoreId]
        };
    }

    const metadata = collectMetadata(assistantId);

    const payload = {
        name: document.getElementById(`name-${assistantId}`).value,
        description: document.getElementById(`description-${assistantId}`).value,
        instructions: document.getElementById(`instructions-${assistantId}`).value,
        model: document.getElementById(`model-${assistantId}`).value,
        tools: tools,
        tool_resources: tool_resources,
        metadata: metadata
    };

    try {
        const response = await fetch(createAssistantUrl, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const data = await response.json();

            // Update the global assistants object
            assistants[data.id] = data;

            // Remove the form card and prepend the new assistant to the list
            const tempCard = document.getElementById(`temp-card-${assistantId}`);
            if (tempCard) {
                tempCard.remove();
            }

            // Re-display the assistants list
            displayAssistants();

            // Scroll to the newly added assistant's card
            const newAssistantId = data.id;
            const assistantCard = document.getElementById(`assistant-${newAssistantId}`);
            if (assistantCard) {
                assistantCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }

        } else {
            const errorData = await response.json();
            let errorMessage = '';

            if (errorData.error) {
                const parsedError = parseErrorText(errorData.error);
                errorMessage = parsedError.errorMessage;
            } else if (errorData.detail) {
                // Handle server errors
                if (Array.isArray(errorData.detail)) {
                    // Extract the message from the first error detail
                    errorMessage = errorData.detail[0].msg || 'Unknown error occurred.';
                } else if (typeof errorData.detail === 'string') {
                    errorMessage = errorData.detail;
                } else {
                    errorMessage = 'Unknown error occurred.';
                }
            } else {
                errorMessage = 'Unknown error occurred.';
            }

            showToast("Failed to save new assistant!", errorMessage);
            console.error('Failed to save new assistant!', errorMessage);
        }
    } catch (error) {
        showToast("Unexpected error:", error);
        console.error('Unexpected error:', error);
    } finally {
        // Hide spinner and enable button
        spinner.classList.add('d-none');
        buttonText.classList.remove('d-none');
        button.disabled = false;
    }
}

async function modifyAssistant(assistantId) {
    const button = document.querySelector(`.btnModifyAssistant[data-assistant-id="${assistantId}"]`);
    const buttonText = button.querySelector('.button-text');
    const spinner = button.querySelector('.spinner-border');

    // Show spinner and disable button
    buttonText.classList.add('d-none');
    spinner.classList.remove('d-none');
    button.disabled = true;

    const url = modifyAssistantUrlTemplate.replace('ASSISTANT_ID_PLACEHOLDER', assistantId);

    const fileSearchSwitch = document.getElementById(`fileSearchSwitch-${assistantId}`);
    const fileSearchEnabled = fileSearchSwitch ? fileSearchSwitch.checked : false;
    const codeInterpreterSwitch = document.getElementById(`codeInterpreterSwitch-${assistantId}`);
    const codeInterpreterEnabled = codeInterpreterSwitch ? codeInterpreterSwitch.checked : false;
    const vectorStoreId = fileSearchEnabled ? document.getElementById(`vs-${assistantId}`).value : null;

    // Collect selected functions
    const selectedFunctionNames = [];
    const functionCheckboxes = document.querySelectorAll(`input[id^="function-"][id$="-${assistantId}"]:checked`);
    functionCheckboxes.forEach(checkbox => {
        selectedFunctionNames.push(checkbox.value);
    });

    // For each selected function name, find the function definition
    const selectedFunctions = functionDefinitions.filter(funcDef => selectedFunctionNames.includes(funcDef.name));

    // Build tools array based on switches
    const tools = [];
    if (codeInterpreterEnabled) {
        tools.push({ "type": "code_interpreter" });
    }
    if (fileSearchEnabled) {
        tools.push({ "type": "file_search" });
    }
    // Add selected functions to tools
    selectedFunctions.forEach(funcDef => {
        tools.push({
            "type": "function",
            "function": funcDef
        });
    });

    // Build tool_resources
    const tool_resources = {};
    if (fileSearchEnabled) {
        if (vectorStoreId) {
            tool_resources["file_search"] = {
                "vector_store_ids": [vectorStoreId]
            };
        } else {
            // Clear the vector_store_ids when "No vector store assigned" is selected
            tool_resources["file_search"] = {
                "vector_store_ids": []
            };
        }
    }

    const metadata = collectMetadata(assistantId);

    const payload = {
        name: document.getElementById(`name-${assistantId}`).value,
        description: document.getElementById(`description-${assistantId}`).value,
        instructions: document.getElementById(`instructions-${assistantId}`).value,
        model: document.getElementById(`model-${assistantId}`).value,
        tools: tools,
        tool_resources: tool_resources,
        metadata: metadata
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const data = await response.json();

            // Update the global assistants object
            assistants[assistantId] = data;

            // Re-display the assistants list
            displayAssistants();

            // Scroll to the updated assistant's card
            const assistantCard = document.getElementById(`assistant-${assistantId}`);
            if (assistantCard) {
                assistantCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }

        } else {
            const errorData = await response.json();
            let errorMessage = '';

            if (errorData.error) {
                const parsedError = parseErrorText(errorData.error);
                errorMessage = parsedError.errorMessage;
            } else if (errorData.detail) {
                // Handle server errors
                if (Array.isArray(errorData.detail)) {
                    // Extract the message from the first error detail
                    errorMessage = errorData.detail[0].msg || 'Unknown error occurred.';
                } else if (typeof errorData.detail === 'string') {
                    errorMessage = errorData.detail;
                } else {
                    errorMessage = 'Unknown error occurred.';
                }
            } else {
                errorMessage = 'Unknown error occurred.';
            }

            showToast("Failed to update assistant!", errorMessage);
            console.error('Failed to update assistant!', errorMessage);
        }
    } catch (error) {
        showToast("Unexpected error:", error);
        console.error('Unexpected error:', error);
    } finally {
        // Hide spinner and enable button
        spinner.classList.add('d-none');
        buttonText.classList.remove('d-none');
        button.disabled = false;
    }
}

let assistantToDeleteId = null; // To store the ID of the assistant to delete

async function deleteAssistant(assistantId) {
    assistantToDeleteId = assistantId; // Store the assistant ID for use in the confirm deletion function

    const assistantInfo = document.getElementById('assistantInfo');

    // Add assistant info
    assistantInfo.textContent = '';
    assistantInfo.textContent = assistants[assistantId] && assistants[assistantId].name && assistants[assistantId].name.trim() !== '' ? assistants[assistantId].name : 'Untitled assistant';

    // Show the modal
    const deleteModal = new bootstrap.Modal(document.getElementById('assistantDeleteModal'));
    deleteModal.show();

    // Attach event listener to the confirm delete button
    const confirmDeleteBtn = document.getElementById('confirmDeleteAssistantBtn');
    confirmDeleteBtn.onclick = confirmDeleteAssistant;
}

async function confirmDeleteAssistant() {
    const assistantId = assistantToDeleteId;
    const deleteAssistantUrl = deleteAssistantUrlTemplate.replace('ASSISTANT_ID_PLACEHOLDER', assistantId);
    const assistantName = assistants[assistantId] && assistants[assistantId].name && assistants[assistantId].name.trim() !== '' ? assistants[assistantId].name : 'Untitled assistant';

    // Hide the modal
    const deleteModal = bootstrap.Modal.getInstance(document.getElementById('assistantDeleteModal'));
    deleteModal.hide();

    try {
        const response = await fetch(deleteAssistantUrl, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            }
        });

        if (response.ok) {
            // Remove the assistant from the global assistants object
            delete assistants[assistantId];

            // Re-display the assistants list
            displayAssistants();

            showToast("Assistant deleted!", assistantName, "success");
            console.log(`Assistant with ID ${assistantId} deleted successfully.`);
        } else {
            const errorData = await response.json();
            const parsedError = parseErrorText(errorData.error);
            showToast("Failed to delete assistant!", parsedError.errorMessage);
            console.error('Failed to delete assistant!', parsedError);
        }
    } catch (error) {
        showToast("Unexpected error:", error);
        console.error('Unexpected error:', error);
    }
}


/* Files */

async function fetchFiles() {
    try {
        const response = await fetch(listFilesUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (data.files) {
            // Clear the global files object
            files = {};

            // Populate the global files object
            data.files.forEach(file => {
                files[file.id] = file;
            });

            // Return the global files object
            return files;
        } else {
            const parsedError = parseErrorText(data.error);
            showToast("Failed to fetch files!", parsedError.errorMessage);
            console.error('Failed to fetch files!', parsedError);
            return {};
        }
    } catch (error) {
        showToast("Error fetching files:", error);
        console.error('Error fetching files:', error);
        return {};
    } finally {
        toggleLoading('files', false);
    }
}

function renderFile(file) {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.id = `file-${file.id}`;

    // File's vector stores
    const vectorStoresHtml = renderFileVSList(fileVectorStores[file.id]);

    // All vector stores to be displayed in the edit mode
    const vectorStoresForm = renderFileVSSelect(file.id);

    // Create the inner HTML for the file item
    fileItem.innerHTML = document.getElementById("file-item-template").innerHTML;

    return fileItem;
}

function displayFiles() {
    const filesList = document.getElementById('files-list');

    // Dispose of existing tooltips within the files list
    disposeTooltips(filesList);

    filesList.innerHTML = ''; // Clear any existing files

    const totalFiles = Object.values(files).length;

    // Convert the files object into an array
    let filesArray = Object.values(files);

    // Apply filters
    filesArray = filesArray.filter(file => {
        // Filter by name
        if (fileFilters.name && !file.filename.toLowerCase().includes(fileFilters.name)) {
            return false;
        }
        // Filter by creation date
        const fileDate = new Date(file.created_at * 1000);
        if (fileFilters.startDate && fileDate < fileFilters.startDate) {
            return false;
        }
        if (fileFilters.endDate && fileDate > fileFilters.endDate) {
            return false;
        }
        // Filter by vector store
        const assignedVsIds = fileVectorStores[file.id] || [];
        if (fileFilters.vectorStoreId && !assignedVsIds.includes(fileFilters.vectorStoreId)) {
            return false;
        }
        // Filter by file type
        const fileType = getFileType(file.filename);
        if (fileFilters.fileType && fileType !== fileFilters.fileType) {
            return false;
        }
        return true;
    });

    const filteredFilesCount = filesArray.length;

    // Update the files count display only if filters are active
    const filesCountElement = document.getElementById('files-count');
    if (areFiltersActive(fileFilters)) {
        filesCountElement.textContent = `${filteredFilesCount} results (${totalFiles} total)`;
        filesCountElement.style.display = 'inline';
    } else {
        filesCountElement.style.display = 'none';
    }

    // Handle different cases based on total files and filtered files
    if (totalFiles === 0) {
        // No files exist at all
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4';
        messageDiv.innerHTML = `
            <p class="text-secondary">No files found.</p>
            <span class="text-secondary">
                <a href="#" class="text-decoration-none" onclick="hideTooltip(this); showUploadFileModal()"><i class="bi bi-plus-lg"></i>Add your first file.</a>
            </span>
        `;
        filesList.appendChild(messageDiv);
        return;
    } else if (filesArray.length === 0) {
        // Files exist, but none match the filters
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center mt-4';
        messageDiv.innerHTML = `
            <p class="text-secondary">No files match your filters.</p>
            <span class="text-secondary">You can
            <a href="#" class="text-decoration-none" onclick="resetFileFilters()">reset the filters</a>
            to see all files.</span>
        `;
        filesList.appendChild(messageDiv);
        return;
    }

    // Sort the array according to the selected sort options
    filesArray.sort((a, b) => {
        let compareResult = 0;

        if (fileSortField === 'filename') {
            compareResult = a.filename.localeCompare(b.filename);
        } else if (fileSortField === 'created_at') {
            compareResult = a.created_at - b.created_at;
        } else if (fileSortField === 'bytes') {
            compareResult = a.bytes - b.bytes;
        }

        return fileSortOrder === 'asc' ? compareResult : -compareResult;
    });

    // Iterate over the sorted and filtered array and append each item
    for (const file of filesArray) {
        const fileItem = renderFile(file);
        filesList.appendChild(fileItem);
    }

    // Re-initialize tooltips after updating the DOM
    initializeTooltips();
}

let fileVectorStoreChanges = {};

function toggleVectorStore(fileId, vectorStoreId, isSelected) {
    // Updates the state of the file vector store changes

    // Initialize if not already initialized
    if (!fileVectorStoreChanges[fileId]) {
        fileVectorStoreChanges[fileId] = {
            toAdd: [],
            toRemove: []
        };
    }

    const { toAdd, toRemove } = fileVectorStoreChanges[fileId];
    const initialVectorStoreIds = fileVectorStores[fileId] || [];

    if (isSelected) {
        // If it's checked and was in `toRemove`, remove it from `toRemove`
        if (toRemove.includes(vectorStoreId)) {
            fileVectorStoreChanges[fileId].toRemove = toRemove.filter(id => id !== vectorStoreId);
        }
        // If it's checked and not in `initialVectorStoreIds`, add it to `toAdd`
        else if (!initialVectorStoreIds.includes(vectorStoreId)) {
            fileVectorStoreChanges[fileId].toAdd.push(vectorStoreId);
        }
    } else {
        // If it's unchecked and was in `toAdd`, remove it from `toAdd`
        if (toAdd.includes(vectorStoreId)) {
            fileVectorStoreChanges[fileId].toAdd = toAdd.filter(id => id !== vectorStoreId);
        }
        // If it's unchecked and is in `initialVectorStoreIds`, add it to `toRemove`
        else if (initialVectorStoreIds.includes(vectorStoreId)) {
            fileVectorStoreChanges[fileId].toRemove.push(vectorStoreId);
        }
    }
}

async function modifyFileVectorStores(fileId) {
    const button = document.querySelector(`.btnModifyFile[data-file-id="${fileId}"]`);
    const buttonText = button.querySelector('.button-text');
    const spinner = button.querySelector('.spinner-border');

    // Show spinner and disable button
    buttonText.classList.add('d-none');
    spinner.classList.remove('d-none');
    button.disabled = true;

    const changes = fileVectorStoreChanges[fileId]; // Get changes for the file

    console.log('Changes:', changes); // Log changes

    const affectedVectorStoreIds = new Set();

    if (changes && changes.toAdd.length > 0) {
        // Assign the file to the given vector stores

        const url = addFileVectorStoreUrlTemplate.replace('FILE_ID_PLACEHOLDER', fileId);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${API_KEY}`,
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({
                    vector_store_ids: changes.toAdd
                })
            });

            if (response.ok) {
                const addStatus = await response.json();
                console.log('Add Status:', addStatus);

                console.log('changes.toAdd before reset:', changes.toAdd); // Log changes.toAdd before resetting

                // Update client-side state
                changes.toAdd.forEach(vectorStoreId => {
                    affectedVectorStoreIds.add(vectorStoreId);

                    // Update `fileVectorStores`
                    if (!fileVectorStores[fileId]) {
                        fileVectorStores[fileId] = [];
                    }
                    if (!fileVectorStores[fileId].includes(vectorStoreId)) {
                        fileVectorStores[fileId].push(vectorStoreId);
                    }

                    // Update `vectorStoreFiles`
                    if (!vectorStoreFiles[vectorStoreId]) {
                        vectorStoreFiles[vectorStoreId] = [];
                    }
                    if (!vectorStoreFiles[vectorStoreId].includes(fileId)) {
                        vectorStoreFiles[vectorStoreId].push(fileId);
                    }
                });

                fileVectorStoreChanges[fileId].toAdd = []; // Reset `toAdd` list

            } else {
                const errorData = await response.json();
                const parsedError = parseErrorText(errorData.error);
                showToast("Failed to update vector store!", parsedError.errorMessage);
                console.error('Failed to update vector store!', parsedError);
            }

        } catch (error) {
            showToast("Unexpected error:", error);
            console.error('Unexpected error:', error);
        }
    }

    if (changes && changes.toRemove.length > 0) {
        // Remove the file from the given vector stores
        const url = removeFileVectorStoreUrlTemplate.replace('FILE_ID_PLACEHOLDER', fileId);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${API_KEY}`,
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({
                    vector_store_ids: changes.toRemove
                })
            });

            if (response.ok) {
                const removeStatus = await response.json();
                console.log('Remove Status:', removeStatus);

                console.log('changes.toRemove before reset:', changes.toRemove); // Log changes.toRemove before resetting

                // Update client-side state
                changes.toRemove.forEach(vectorStoreId => {
                    affectedVectorStoreIds.add(vectorStoreId);

                    // Update `fileVectorStores`
                    if (fileVectorStores[fileId]) {
                        fileVectorStores[fileId] = fileVectorStores[fileId].filter(id => id !== vectorStoreId);
                    }

                    // Update `vectorStoreFiles`
                    if (vectorStoreFiles[vectorStoreId]) {
                        vectorStoreFiles[vectorStoreId] = vectorStoreFiles[vectorStoreId].filter(id => id !== fileId);
                    }
                });

                fileVectorStoreChanges[fileId].toRemove = []; // Reset `toRemove` list

            } else {
                const errorData = await response.json();
                const parsedError = parseErrorText(errorData.error);
                showToast("Failed to update vector store!", parsedError.errorMessage);
                console.error('Failed to update vector store!', parsedError);
            }

        } catch (error) {
            showToast("Unexpected error:", error);
            console.error('Unexpected error:', error);
        }
    }

    // Fetch updated vector stores
    await updateVectorStoresByIds(Array.from(affectedVectorStoreIds));

    // Re-display the files list
    displayFiles();

    displayVectorStores(); // Re-render vector store cards
    populateFileFilterOptions(); // Update file filters

    // Hide spinner and enable button
    spinner.classList.add('d-none');
    buttonText.classList.remove('d-none');
    button.disabled = false;

    // Scroll to the updated file's card
    const fileCard = document.getElementById(`file-${fileId}`);
    if (fileCard) {
        fileCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

let fileToDeleteId = null; // To store the ID of the file to delete

async function deleteFile(fileId) {
    fileToDeleteId = fileId; // Store the file ID for use in the confirm deletion function

    // Collect vector stores associated with this file
    const vectorStoresUsingFile = fileVectorStores[fileId] || [];

    // Update the modal content
    const vectorStoreNamesListElement = document.getElementById('vectorStoreNamesList');
    const vectorStoresUsingFileDiv = document.getElementById('vectorStoresUsingFile');
    const fileInfo = document.getElementById('fileInfo');

    // Clear previous list
    vectorStoreNamesListElement.innerHTML = '';

    // Add file info
    fileInfo.textContent = '';
    fileInfo.textContent = files[fileId].filename;

    if (vectorStoresUsingFile.length > 0) {
        // Show the list of vector stores
        vectorStoresUsingFileDiv.classList.remove('d-none');
        vectorStoresUsingFile.forEach(vsId => {
            const vsName = vectorStores[vsId] && vectorStores[vsId].name && vectorStores[vsId].name.trim() !== '' ? vectorStores[vsId].name : 'Untitled store';
            const li = document.createElement('li');
            li.textContent = vsName;
            vectorStoreNamesListElement.appendChild(li);
        });
    } else {
        vectorStoresUsingFileDiv.classList.add('d-none');
    }

    // Show the modal
    const deleteModal = new bootstrap.Modal(document.getElementById('fileDeleteModal'));
    deleteModal.show();

    // Attach event listener to the confirm delete button
    const confirmDeleteBtn = document.getElementById('confirmDeleteFileBtn');
    confirmDeleteBtn.onclick = confirmDeleteFile;
}

async function confirmDeleteFile() {
    const fileId = fileToDeleteId;
    const deleteFileUrl = deleteFileUrlTemplate.replace('FILE_ID_PLACEHOLDER', fileId);
    const fileName = files[fileId].filename;

    // Hide the modal
    const deleteModal = bootstrap.Modal.getInstance(document.getElementById('fileDeleteModal'));
    deleteModal.hide();

    try {
        const response = await fetch(deleteFileUrl, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            }
        });

        if (response.ok) {
            // Update file-vector store associations
            const associatedVectorStores = fileVectorStores[fileId] || [];

            // Remove the file from the global files object
            delete files[fileId];

            associatedVectorStores.forEach(vsId => {
                // Remove fileId from vectorStoreFiles[vsId]
                if (vectorStoreFiles[vsId]) {
                    vectorStoreFiles[vsId] = vectorStoreFiles[vsId].filter(id => id !== fileId);
                }
            });

            // Remove the file from fileVectorStores
            delete fileVectorStores[fileId];

            // Fetch updated vector stores
            await updateVectorStoresByIds(associatedVectorStores);

            // Re-display the files list
            displayFiles();

            displayVectorStores(); // Re-render vector store cards
            populateFileFilterOptions(); // Update file filters

            showToast("File deleted!", fileName, "success");
            console.log(`File with ID ${fileId} deleted successfully.`);
        } else {
            const errorData = await response.json();
            const parsedError = parseErrorText(errorData.error);
            showToast("Failed to delete file!", parsedError.errorMessage);
            console.error('Failed to delete file!', parsedError);
        }
    } catch (error) {
        showToast("Unexpected error:", error);
        console.error('Unexpected error:', error);
    }
}


/* File Uploads */

async function showUploadFileModal() {
    const vectorStoreCheckboxes = document.getElementById('vectorStoreCheckboxes');
    vectorStoreCheckboxes.innerHTML = ''; // Clear previous checkboxes

    if (Object.keys(vectorStores).length === 0) {
        vectorStoreCheckboxes.innerHTML = '<p class="text-muted small">No vector store available</p>';
    } else {
        // Dynamically generate checkboxes for each vector store
        for (const [vsId, vectorStore] of Object.entries(vectorStores)) {
            const checkbox = document.createElement('div');
            checkbox.classList.add('form-check');

            const input = document.createElement('input');
            input.classList.add('form-check-input');
            input.type = 'checkbox';
            input.value = vsId;
            input.id = `vs-${vsId}`;

            const label = document.createElement('label');
            label.classList.add('form-check-label');
            label.setAttribute('for', `vs-${vsId}`);
            label.textContent = vectorStore.name ?? 'Untitled store';

            checkbox.appendChild(input);
            checkbox.appendChild(label);
            vectorStoreCheckboxes.appendChild(checkbox);
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
    const vectorStoreCheckboxes = document.querySelectorAll('#vectorStoreCheckboxes .form-check-input');
    const selectedVectorStores = Array.from(vectorStoreCheckboxes)
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

    // Append selected vector stores
    selectedVectorStores.forEach(vsId => {
        formData.append('vector_store_ids', vsId);
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

            // Update the global files and vector store relation states
            result.uploaded_files.forEach(file => {
                // Add the uploaded files to the global files dict
                files[file.id] = file;

                // Only update vector stores for supported_files
                if (isSupportedFileType(file.filename)) {
                    // Update fileVectorStores
                    fileVectorStores[file.id] = selectedVectorStores;  // Set the selected vector stores for the uploaded file

                    // Update vectorStoreFiles
                    selectedVectorStores.forEach(vsId => {
                        if (!vectorStoreFiles[vsId]) {
                            vectorStoreFiles[vsId] = [];
                        }
                        vectorStoreFiles[vsId].push(file.id);  // Add the file to the vector store
                    });
                }
            });

            console.log('fileVectorStores:', fileVectorStores);
            console.log('vectorStoreFiles:', vectorStoreFiles);

            // Fetch updated vector stores
            await updateVectorStoresByIds(result.vector_store_ids);

            // Re-display the files list
            displayFiles();

            displayVectorStores(); // Re-render vector store cards to reflect updated files
            populateFileFilterOptions(); // Update file filters to reflect new files

            // Hide the modal after successful upload
            const modal = bootstrap.Modal.getInstance(document.getElementById('uploadFileModal'));
            modal.hide();

            // Scroll to the top of files-list
            const filesListSection = document.getElementById('files-list');
            if (filesListSection) {
                filesListSection.scrollIntoView({ behavior: 'smooth' });
            }

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
    new bootstrap.Dropdown(document.getElementById('vectorStoreSortDropdown'));
    new bootstrap.Dropdown(document.getElementById('fileSortDropdown'));

    // Initialize filter icons
    updateFilterIcon('assistantFilterDropdown', assistantFilters);
    updateFilterIcon('vectorStoreFilterDropdown', vectorStoreFilters);
    updateFilterIcon('fileFilterDropdown', fileFilters);
});
