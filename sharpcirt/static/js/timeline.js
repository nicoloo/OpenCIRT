// Get modal and button elements
const actionAddModal = document.getElementById('actionAddModal');
const actionAddButton = document.querySelector('.ActionAddButton');
const closeActionModal = document.getElementById('closeActionModal');
const cancelActionForm = document.getElementById('cancelActionForm');
const actionForm = document.getElementById('actionForm');
const actionEditForm = document.getElementById('actionEditForm');
const incidentId = document.getElementById('incident-id')?.value || document.querySelector('[incident-id]')?.getAttribute('incident-id');

const formContainer = document.getElementById('formContainer');
const mainFrame = document.querySelector('.main-frame');

const modalEditActionId = document.getElementById('modalEditActionId');
const modalEditAction = document.getElementById('editActionModal');
const modalEditType = document.getElementById('modal-action-type');
const modalEditTitle = document.getElementById('modal-action-title');
const modalEditDescription = document.getElementById('modal-action-description');
const modalEditCreatedBy = document.getElementById('modal-action-createdby');
const modalEditCreatedAt = document.getElementById('modal-action-createdat');
const modalEditTags = document.getElementById('modal-action-tags');
const modalEditIocs = document.getElementById('modal-action-iocs');
const closeBtnEdit = document.querySelector('.close.action-modal');

// Evidence toggle button
const toggleEvidenceSection = document.getElementById('toggleEvidenceSection');
const evidenceSection = document.getElementById('evidenceSection');

// Open the modal/form panel
actionAddButton.addEventListener('click', function () {
    if (actionAddModal) {
        actionAddModal.style.display = 'block';
    } else if (formContainer) {
        formContainer.style.display = 'block';
        if (mainFrame) {
            mainFrame.style.gridTemplateColumns = '1fr 1fr';
        }
    }
});

// Close the modal
closeActionModal.addEventListener('click', function () {
    if (actionAddModal) {
        actionAddModal.style.display = 'none';
    }
});

// Cancel button - hide form panel
if (cancelActionForm) {
    cancelActionForm.addEventListener('click', function () {
        if (actionAddModal) {
            actionAddModal.style.display = 'none';
        } else if (formContainer) {
            formContainer.style.display = 'none';
            if (mainFrame) {
                mainFrame.style.gridTemplateColumns = '1fr';
            }
        }
    });
}

// Toggle Evidence Section
if (toggleEvidenceSection && evidenceSection) {
    toggleEvidenceSection.addEventListener('click', function (e) {
        e.preventDefault();
        const isHidden = evidenceSection.style.display === 'none';
        evidenceSection.style.display = isHidden ? 'block' : 'none';
        
        const toggleIcon = this.querySelector('.toggle-icon');
        if (toggleIcon) {
            toggleIcon.textContent = isHidden ? '−' : '+';
        }
    });
}

// Close Modal Edit
if (closeBtnEdit) {
    closeBtnEdit.addEventListener('click', function () {
        modalEditAction.style.display = 'none';
    });
}

if (modalEditAction) {
    window.addEventListener('click', function (event) {
        if (event.target === modalEditAction) {
            modalEditAction.style.display = 'none';
        }
    });
}

if (actionAddModal) {
    window.addEventListener('click', function (event) {
        if (event.target === actionAddModal) {
            actionAddModal.style.display = 'none';
        }
    });
}

// Store selected IOCs and all IOCs
let selectedIocIds = [];
let allAvailableIocs = [];

// Load and display IOCs
async function loadAndDisplayIocs(linkedIocs) {
    try {
        // Fetch all IOCs for the incident
        const response = await fetch(`/api/incident/${incidentId}/iocs/`);
        
        if (!response.ok) {
            console.error('API response not ok:', response.status);
            return;
        }
        
        const data = await response.json();
        
        console.log('IOCs loaded:', data);
        
        if (!data.iocs) {
            console.error('Could not fetch IOCs');
            return;
        }
        
        allAvailableIocs = data.iocs;
        const linkedIocIds = linkedIocs.map(ioc => ioc.id);
        selectedIocIds = [...linkedIocIds];
        
        // Display linked IOCs
        displayLinkedIocs(linkedIocs);
        
        // Display available IOCs (not yet linked)
        const availableIocs = allAvailableIocs.filter(ioc => !linkedIocIds.includes(ioc.id));
        displayAvailableIocs(availableIocs);
        
    } catch (error) {
        console.error('Error loading IOCs:', error);
    }
}

function displayLinkedIocs(linkedIocs) {
    const linkedContainer = document.getElementById('linkedIocs');
    
    if (linkedIocs.length === 0) {
        linkedContainer.innerHTML = '<p style="margin: 0; color: #9ca3af; font-size: 12px;">No evidence linked yet</p>';
        return;
    }
    
    linkedContainer.innerHTML = '';
    linkedIocs.forEach(ioc => {
        const iocElement = document.createElement('div');
        iocElement.className = 'ioc-badge-linked';
        iocElement.style.cssText = 'display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; background-color: #dbeafe; border: 1px solid #7dd3fc; border-radius: 4px; font-size: 12px; color: #0369a1; font-weight: 500;';
        iocElement.innerHTML = `
            <span>${ioc.type} - ${ioc.value}</span>
            <button type="button" class="unlink-ioc" data-ioc-id="${ioc.id}" style="background: none; border: none; color: #0369a1; cursor: pointer; padding: 0; font-size: 14px; font-weight: bold;">×</button>
        `;
        linkedContainer.appendChild(iocElement);
    });
    
    // Add event listeners for unlink buttons
    document.querySelectorAll('.unlink-ioc').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const iocId = parseInt(this.getAttribute('data-ioc-id'));
            selectedIocIds = selectedIocIds.filter(id => id !== iocId);
            
            // Reload display
            const linkedIocsList = linkedIocs.filter(ioc => selectedIocIds.includes(ioc.id));
            const availableIocs = allAvailableIocs.filter(ioc => !selectedIocIds.includes(ioc.id));
            displayLinkedIocs(linkedIocsList);
            displayAvailableIocs(availableIocs);
        });
    });
}

function displayAvailableIocs(availableIocs) {
    const availableContainer = document.getElementById('availableIocs');
    
    if (availableIocs.length === 0) {
        availableContainer.innerHTML = '<p style="margin: 0; color: #9ca3af; font-size: 12px;">All evidence is linked</p>';
        return;
    }
    
    availableContainer.innerHTML = '';
    availableIocs.forEach(ioc => {
        const iocElement = document.createElement('button');
        iocElement.type = 'button';
        iocElement.className = 'ioc-selectable';
        iocElement.style.cssText = 'display: flex; align-items: center; gap: 8px; padding: 8px 10px; background-color: #f3f4f6; border: 1px solid #e5e5e5; border-radius: 4px; cursor: pointer; transition: all 0.2s; text-align: left; width: 100%;';
        iocElement.innerHTML = `
            <span style="flex: 1; font-size: 12px; color: #374151;"><strong>${ioc.type}</strong>: ${ioc.value}</span>
            <span style="color: #9ca3af; font-size: 14px;">+</span>
        `;
        
        iocElement.addEventListener('mouseover', () => {
            iocElement.style.backgroundColor = '#e5e7eb';
            iocElement.style.borderColor = '#d1d5db';
        });
        iocElement.addEventListener('mouseout', () => {
            iocElement.style.backgroundColor = '#f3f4f6';
            iocElement.style.borderColor = '#e5e5e5';
        });
        
        iocElement.addEventListener('click', (e) => {
            e.preventDefault();
            selectedIocIds.push(ioc.id);
            
            // Reload display
            const linked = allAvailableIocs.filter(i => selectedIocIds.includes(i.id));
            const available = allAvailableIocs.filter(i => !selectedIocIds.includes(i.id));
            displayLinkedIocs(linked);
            displayAvailableIocs(available);
        });
        
        availableContainer.appendChild(iocElement);
    });
}


// Handle form submission
actionForm.addEventListener('submit', async function (e) {
    e.preventDefault();

    const actionId = this.dataset.actionId;
    const url = actionId 
        ? `/api/incident/${incidentId}/update-action/`
        : `/api/incident/${incidentId}/add-action/`;

    const observedAt = document.getElementById('actionObservedAt').value;
    const startingTime = document.getElementById('actionStartingTime').value;
    const endingTime = document.getElementById('actionEndingTime').value;

    const data = {
        id: actionId,
        title: document.getElementById('actionTitle').value,
        type: document.getElementById('actionType').value,
        description: document.getElementById('actionDescription').value,
        observed_at: observedAt || null,
        starting_time: startingTime || null,
        ending_time: endingTime || null,
        tags: [],
        iocs: selectedIocIds,
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify(data),
        });

        if (response.ok) {
            const result = await response.json();
            // Reset form and hide modal
            actionForm.reset();
            delete actionForm.dataset.actionId;
            actionAddModal.style.display = 'none';
            // Reload the page to see updated timeline
            location.reload();
        } else {
            const errorData = await response.json();
            alert(`Error: ${errorData.message || 'Failed to save action'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while saving the action.');
    }
});

// Utility function to get CSRF token (Django-specific)
function getCsrfToken() {
    return document.cookie.split('; ').find(row => row.startsWith('csrftoken=')).split('=')[1];
}


document.querySelectorAll('.delete-action').forEach(button => {
    button.addEventListener('click', async function(event) {
        event.stopPropagation();

        const actionElement = this.closest('.timeline-card');
        const actionId = actionElement.getAttribute('data-action-id');
        try {
            const response = await fetch(`/api/incident/${incidentId}/delete-action/`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ id: actionId }),
            });

            if (response.ok) {
                actionElement.remove(); // Remove the task element from the DOM
            } else {
                const errorData = await response.json();
                alert(`Failed to delete action: ${errorData.error}`);
            }
        } catch (error) {
            console.error('Error deleting action:', error);
            alert('An error occurred while deleting the action.');
        }
        
    });
    });

    // Handle edit-action button click
    document.querySelectorAll('.edit-action').forEach(button => {
        button.addEventListener('click', async function(event) {
            event.stopPropagation();
            
            const actionElement = this.closest('.timeline-card');
            const actionId = actionElement.getAttribute('data-action-id');
            
            console.log('Edit button clicked for action:', actionId);
            
            if (!actionId) {
                console.error('No action ID found');
                return;
            }
            
            try {
                const response = await fetch(`/api/incident/${incidentId}/get-action/${actionId}/`);
                const data = await response.json();
                
                console.log('Action data:', data);
                
                if (data.status === "success") {
                    const action = data.data;
                    
                    // Populate modal form with action data
                    document.getElementById('actionTitle').value = action.title || '';
                    document.getElementById('actionType').value = action.type || '';
                    document.getElementById('actionDescription').value = action.description || '';
                    
                    // Handle timing fields - show the appropriate one based on data
                    const observedAtField = document.getElementById('observedAtField');
                    const startingEndingFields = document.getElementById('startingEndingTimeFields');
                    
                    if (action.observed_at) {
                        document.getElementById('actionObservedAt').value = action.observed_at;
                        observedAtField.style.display = 'block';
                        startingEndingFields.style.display = 'none';
                        document.getElementById('actionStartingTime').value = '';
                        document.getElementById('actionEndingTime').value = '';
                    } else if (action.starting_time && action.ending_time) {
                        document.getElementById('actionStartingTime').value = action.starting_time;
                        document.getElementById('actionEndingTime').value = action.ending_time;
                        observedAtField.style.display = 'none';
                        startingEndingFields.style.display = 'block';
                        document.getElementById('actionObservedAt').value = '';
                    } else {
                        // Reset to default (observed_at visible)
                        observedAtField.style.display = 'block';
                        startingEndingFields.style.display = 'none';
                        document.getElementById('actionObservedAt').value = '';
                        document.getElementById('actionStartingTime').value = '';
                        document.getElementById('actionEndingTime').value = '';
                    }
                    
                    // Load and display IOCs/Evidence
                    loadAndDisplayIocs(action.iocs || []);
                    
                    // Store action ID in form for submission
                    actionForm.dataset.actionId = actionId;
                    
                    // Show modal
                    if (actionAddModal) {
                        actionAddModal.style.display = 'block';
                    }
                    
                    console.log('Modal populated with action data');
                    
                } else {
                    console.error('Error:', data.error);
                    alert('Error loading action: ' + data.error);
                }
            } catch (error) {
                console.error('Error fetching Action details:', error);
                alert('Error loading action');
            }
        });
    });

    document.getElementById('toggleTimingFields').addEventListener('click', function () {
        const observedAtField = document.getElementById('observedAtField');
        const startingEndingFields = document.getElementById('startingEndingTimeFields');
        const toggleButton = document.getElementById('toggleTimingFields');
    
        if (observedAtField.style.display === 'none') {
            observedAtField.style.display = 'block';
            startingEndingFields.style.display = 'none';
            toggleButton.textContent = 'Switch to Starting/Ending Time';
        } else {
            observedAtField.style.display = 'none';
            startingEndingFields.style.display = 'block';
            toggleButton.textContent = 'Switch to Observed At';
        }
    });
    document.getElementById('toggleTimingFieldsEdit').addEventListener('click', function () {
        const observedAtFieldEdit = document.getElementById('observedAtFieldEdit');
        const startingEndingFieldsEdit = document.getElementById('startingEndingTimeFieldsEdit');
        const toggleButtonEdit = document.getElementById('toggleTimingFieldsEdit');
    
        if (observedAtFieldEdit.style.display === 'none') {
            observedAtFieldEdit.style.display = 'block';
            startingEndingFieldsEdit.style.display = 'none';
            toggleButtonEdit.textContent = 'Switch to Starting/Ending Time';
        } else {
            observedAtFieldEdit.style.display = 'none';
            startingEndingFieldsEdit.style.display = 'block';
            toggleButtonEdit.textContent = 'Switch to Observed At';
        }
    });

let currentActionId = null;    
// Handle Action Details Display
document.querySelectorAll('.timeline-item').forEach(item => {
    item.addEventListener('click', function () {
        const actionId = this.dataset.actionId;
        const incidentId = document.querySelector('.main-content').getAttribute('incident-id');

        currentActionId = actionId; // Save the current Action ID for editing

        fetch(`/api/incident/${incidentId}/get-action/${actionId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    const action = data.data;
                    modalEditActionId.value = actionId;
                    modalEditType.value = action.type;
                    modalEditTitle.value = action.title;
                    document.getElementById('actionObservedAtEdit').value = action.observed_at;
                    modalEditDescription.value = action.description;
                    modalEditCreatedBy.textContent = action.created_by;
                    modalEditCreatedAt.textContent = action.created_at;
                    // modalEditObservedAt.textContent = action.observed_at;

                    modalEditTags.innerHTML = '';
                    action.tags.forEach(tag => {
                        const tagElement = document.createElement('div');
                        tagElement.className = 'tag';
                        tagElement.style.backgroundColor = tag.color;
                        tagElement.innerHTML = `<span class="tag-item-value">#${tag.name}</span>`;
                        modalEditTags.appendChild(tagElement);
                    });

                    modalEditIocs.innerHTML = '';
                    action.iocs.forEach(ioc => {
                        const actionElement = document.createElement('div');
                        actionElement.className = 'action';
                        actionElement.innerHTML = `<span>${ioc.type} - ${ioc.value} </span>`;
                        modalEditIocs.appendChild(actionElement);
                    });

                    modalEditAction.style.display = 'block';
                } else {
                    console.error('Error:', data.error);
                }
            })
            .catch(error => {
                console.error('Error fetching Action details:', error);
            });
               
    });
});


// Handle edit form submission
actionEditForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    const actionId = this.dataset.actionId;
    const incidentId = document.querySelector('.main-content').getAttribute('incident-id');
    const url = `/api/incident/${incidentId}/update-action/`;

    const data = {
    id: document.getElementById('modalEditActionId').value,
    title: document.getElementById('modal-action-title').value,
    type: document.getElementById('modal-action-type').value,
    description: document.getElementById('modal-action-description').value,
    observed_at: document.getElementById('actionObservedAtEdit').value,
    starting_time: document.getElementById('actionStartingTimeEdit').value,
    ending_time: document.getElementById('actionEndingTimeEdit').value,
    tags: document.getElementById('actionTags').value,
    iocs: document.getElementById('actionIocs').value,

    };

    try {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(), // Adjust if CSRF token is required
        },
        body: JSON.stringify(data),
    });

    if (response.ok) {
        const result = await response.json();
        editActionModal.style.display = 'none';
        // Optionally refresh or update the timeline here
    } else {
        const errorData = await response.json();
        alert(`Error: ${errorData.message || 'Failed to edit action'}`);
    }
    } catch (error) {
    console.error('Error:', error);
    alert('An error occurred while editing the action.');
    }
    });