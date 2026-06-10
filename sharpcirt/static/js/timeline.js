// Get modal and button elements
const actionAddModal = document.getElementById('actionAddModal');
const actionAddButton = document.querySelector('.ActionAddButton');
const closeActionModal = document.getElementById('closeActionModal');
const cancelActionForm = document.getElementById('cancelActionForm');
const actionForm = document.getElementById('actionForm');
const actionEditForm = document.getElementById('actionEditForm');
const incidentId = document.querySelector('[incident-id]')?.getAttribute('incident-id');
const modalEditAction = document.getElementById('editActionModal');

// ============================================
// DELETE BUTTON HANDLER (inline confirm)
// ============================================
document.addEventListener('click', async function (event) {

    // Show inline confirm
    const deleteTrigger = event.target.closest('.delete-action-trigger');
    if (deleteTrigger) {
        const foot = deleteTrigger.closest('.tl-card-foot');
        if (foot) {
            deleteTrigger.classList.add('hidden');
            foot.querySelector('.tl-delete-confirm').classList.add('show');
        }
        return;
    }

    // Cancel delete
    const confirmNo = event.target.closest('.tl-confirm-no');
    if (confirmNo) {
        const foot = confirmNo.closest('.tl-card-foot');
        if (foot) {
            foot.querySelector('.tl-delete-confirm').classList.remove('show');
            foot.querySelector('.delete-action-trigger').classList.remove('hidden');
        }
        return;
    }

    // Confirm delete
    const confirmYes = event.target.closest('.tl-confirm-yes');
    if (!confirmYes) return;

    const timelineItem = confirmYes.closest('.tl-item');
    if (!timelineItem) return;

    const actionId = timelineItem.getAttribute('data-action-id');
    if (!actionId) return;

    try {
        const csrfToken = getCsrfToken();
        const response = await fetch(`/api/incident/${incidentId}/delete-action/`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ id: actionId }),
        });

        if (response.ok) {
            timelineItem.style.opacity = '0';
            timelineItem.style.transition = 'opacity 0.3s ease-out';
            setTimeout(() => { timelineItem.remove(); location.reload(); }, 300);
        } else {
            const errorData = await response.json();
            alert(`Failed to delete: ${errorData.error || 'Unknown error'}`);
            // Restore button state
            const foot = confirmYes.closest('.tl-card-foot');
            if (foot) {
                foot.querySelector('.tl-delete-confirm').classList.remove('show');
                foot.querySelector('.delete-action-trigger').classList.remove('hidden');
            }
        }
    } catch (error) {
        console.error('Fetch error:', error);
        alert(`Error: ${error.message}`);
    }
}, true);

// ============================================
// TIMELINE CARD CLICK TO EDIT
// ============================================
document.addEventListener('click', async function (event) {
    if (event.target.closest('.delete-action-trigger')) return;
    if (event.target.closest('.tl-confirm-yes')) return;
    if (event.target.closest('.tl-confirm-no')) return;
    if (event.target.closest('button')) return;

    // IoC chip → navigate to IoC page and open that IoC's edit modal
    const iocChip = event.target.closest('.ioc-item');
    if (iocChip) {
        const iocId = iocChip.dataset.iocId;
        if (iocId && incidentId) {
            window.location.href = `/incident/${incidentId}/iocs?open=${iocId}`;
        }
        return;
    }

    const timelineCard = event.target.closest('.timeline-card');
    if (!timelineCard) return;

    const timelineItem = timelineCard.closest('.tl-item');
    if (!timelineItem) return;

    const actionId = timelineItem.getAttribute('data-action-id');
    if (!actionId) return;

    try {
        await loadActionDetailsForEdit(actionId);
    } catch (error) {
        console.error('Error loading action details:', error);
    }
}, true);

// ============================================
// MODAL & FORM HANDLERS
// ============================================
if (actionAddButton) {
    actionAddButton.addEventListener('click', function () {
        actionAddModal.style.display = 'flex';
        initAddModalIocPicker();
    });
}

if (closeActionModal) {
    closeActionModal.addEventListener('click', function () {
        actionAddModal.style.display = 'none';
    });
}

if (cancelActionForm) {
    cancelActionForm.addEventListener('click', function () {
        actionAddModal.style.display = 'none';
    });
}

if (actionAddModal) {
    window.addEventListener('click', function (event) {
        if (event.target === actionAddModal) actionAddModal.style.display = 'none';
    });
}

// Close edit modal
document.querySelectorAll('.close.action-modal').forEach(btn => {
    btn.addEventListener('click', () => { modalEditAction.style.display = 'none'; });
});

if (modalEditAction) {
    window.addEventListener('click', function (event) {
        if (event.target === modalEditAction) modalEditAction.style.display = 'none';
    });
}

// ============================================
// FORM SUBMISSION
// ============================================
let selectedIocIds = [];
let selectedAddIocIds = [];

if (actionForm) {
    actionForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const data = {
            title: document.getElementById('actionTitle').value,
            type: document.getElementById('actionType').value,
            description: document.getElementById('actionDescription').value,
            observed_at: document.getElementById('actionObservedAt').value || null,
            starting_time: document.getElementById('actionStartingTime').value || null,
            ending_time: document.getElementById('actionEndingTime').value || null,
            tags: [],
            iocs: selectedAddIocIds,
        };

        try {
            const response = await fetch(`/api/incident/${incidentId}/add-action/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify(data),
            });

            if (response.ok) {
                actionForm.reset();
                selectedAddIocIds = [];
                actionAddModal.style.display = 'none';
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
}

// ============================================
// EDIT ACTION FORM SUBMISSION
// ============================================
if (actionEditForm) {
    actionEditForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const actionId = document.getElementById('modalEditActionId').value;
        const data = {
            id: actionId,
            title: document.getElementById('modal-action-title').value,
            type: document.getElementById('modal-action-type').value,
            description: document.getElementById('modal-action-description').value,
            observed_at: document.getElementById('actionObservedAtEdit').value || null,
            starting_time: document.getElementById('actionStartingTimeEdit').value || null,
            ending_time: document.getElementById('actionEndingTimeEdit').value || null,
            tags: [],
            iocs: selectedIocIds,
        };

        try {
            const response = await fetch(`/api/incident/${incidentId}/update-action/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify(data),
            });

            if (response.ok) {
                modalEditAction.style.display = 'none';
                location.reload();
            } else {
                const errorData = await response.json();
                alert(`Error: ${errorData.message || 'Failed to update action'}`);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while updating the action.');
        }
    });
}

// ============================================
// TIMING FIELDS TOGGLE
// ============================================
const toggleTimingFields = document.getElementById('toggleTimingFields');
const observedAtField = document.getElementById('observedAtField');
const startingEndingTimeFields = document.getElementById('startingEndingTimeFields');

if (toggleTimingFields) {
    toggleTimingFields.addEventListener('click', function () {
        const isObservedAtVisible = observedAtField.style.display !== 'none';
        if (isObservedAtVisible) {
            observedAtField.style.display = 'none';
            startingEndingTimeFields.style.display = 'block';
            this.textContent = 'Switch to Observed At';
        } else {
            observedAtField.style.display = 'block';
            startingEndingTimeFields.style.display = 'none';
            this.textContent = 'Switch to Starting/Ending Time';
        }
    });
}

const toggleTimingFieldsEdit = document.getElementById('toggleTimingFieldsEdit');
const observedAtFieldEdit = document.getElementById('observedAtFieldEdit');
const startingEndingTimeFieldsEdit = document.getElementById('startingEndingTimeFieldsEdit');

if (toggleTimingFieldsEdit) {
    toggleTimingFieldsEdit.addEventListener('click', function () {
        const isObservedAtVisible = observedAtFieldEdit.style.display !== 'none';
        if (isObservedAtVisible) {
            observedAtFieldEdit.style.display = 'none';
            startingEndingTimeFieldsEdit.style.display = 'block';
            this.textContent = 'Switch to Observed At';
        } else {
            observedAtFieldEdit.style.display = 'block';
            startingEndingTimeFieldsEdit.style.display = 'none';
            this.textContent = 'Switch to Starting/Ending Time';
        }
    });
}

// ============================================
// ACTION DETAILS LOADING (edit modal)
// ============================================
async function loadActionDetailsForEdit(actionId) {
    try {
        const response = await fetch(`/api/incident/${incidentId}/get-action/${actionId}/`);
        if (!response.ok) { alert('Failed to load action details'); return; }

        const json = await response.json();
        const action = json.data || json;

        document.getElementById('modalEditActionId').value = actionId;
        document.getElementById('modal-action-type').value = action.type;
        document.getElementById('modal-action-title').value = action.title;
        document.getElementById('modal-action-description').value = action.description;
        document.getElementById('modal-action-createdby').textContent = action.created_by || 'Unknown';
        document.getElementById('modal-action-createdat').textContent = new Date(action.created_at).toLocaleString();

        const toDatetimeLocal = s => s ? s.replace(' ', 'T').slice(0, 16) : '';
        document.getElementById('actionObservedAtEdit').value = toDatetimeLocal(action.observed_at);
        document.getElementById('actionStartingTimeEdit').value = toDatetimeLocal(action.starting_time);
        document.getElementById('actionEndingTimeEdit').value = toDatetimeLocal(action.ending_time);

        await loadAndDisplayActionIocs(action.iocs || []);

        modalEditAction.style.display = 'flex';
    } catch (error) {
        console.error('Error loading action details:', error);
        alert('An error occurred while loading action details.');
    }
}

// ============================================
// IOC PICKER (shared state)
// ============================================
let allIncidentIocs = [];

async function fetchAllIocs() {
    try {
        const resp = await fetch(`/api/incident/${incidentId}/iocs/`);
        const json = await resp.json();
        allIncidentIocs = json.iocs || [];
    } catch (e) {
        console.error('Failed to load incident IOCs', e);
        allIncidentIocs = [];
    }
}

// ---- Edit modal IOC picker ----
async function loadAndDisplayActionIocs(linkedIocs) {
    selectedIocIds = (linkedIocs || []).map(ioc => ioc.id);
    await fetchAllIocs();
    renderIocPicker('');

    const searchInput = document.getElementById('iocSearchInput');
    if (searchInput) {
        searchInput.value = '';
        const fresh = searchInput.cloneNode(true);
        searchInput.parentNode.replaceChild(fresh, searchInput);
        fresh.addEventListener('input', () => renderIocPicker(fresh.value));
    }
}

function renderIocPicker(filter) {
    const linkedEl    = document.getElementById('modal-action-iocs-linked');
    const availableEl = document.getElementById('modal-action-iocs-available');
    if (!linkedEl || !availableEl) return;

    const q = (filter || '').toLowerCase();
    const linked    = allIncidentIocs.filter(ioc => selectedIocIds.includes(ioc.id));
    const available = allIncidentIocs.filter(ioc =>
        !selectedIocIds.includes(ioc.id) &&
        (!q || ioc.value.toLowerCase().includes(q) || ioc.type.toLowerCase().includes(q))
    );

    linkedEl.innerHTML = '';
    linkedEl.appendChild(
        linked.length === 0
            ? makeEmpty('No IOCs linked yet')
            : document.createDocumentFragment()
    );
    linked.forEach(ioc => linkedEl.appendChild(buildIocChip(ioc, true, selectedIocIds, () => renderIocPicker(document.getElementById('iocSearchInput')?.value || ''))));

    availableEl.innerHTML = '';
    if (available.length === 0) {
        availableEl.appendChild(makeEmpty('No IOCs available' + (q ? ` matching "${filter}"` : '')));
    } else {
        available.forEach(ioc => availableEl.appendChild(buildIocChip(ioc, false, selectedIocIds, () => renderIocPicker(document.getElementById('iocSearchInput')?.value || ''))));
    }
}

// ---- Add modal IOC picker ----
async function initAddModalIocPicker() {
    selectedAddIocIds = [];
    await fetchAllIocs();
    renderAddIocPicker('');

    const searchInput = document.getElementById('addIocSearchInput');
    if (searchInput) {
        searchInput.value = '';
        const fresh = searchInput.cloneNode(true);
        searchInput.parentNode.replaceChild(fresh, searchInput);
        fresh.addEventListener('input', () => renderAddIocPicker(fresh.value));
    }
}

function renderAddIocPicker(filter) {
    const linkedEl    = document.getElementById('add-modal-iocs-linked');
    const availableEl = document.getElementById('add-modal-iocs-available');
    if (!linkedEl || !availableEl) return;

    const q = (filter || '').toLowerCase();
    const linked    = allIncidentIocs.filter(ioc => selectedAddIocIds.includes(ioc.id));
    const available = allIncidentIocs.filter(ioc =>
        !selectedAddIocIds.includes(ioc.id) &&
        (!q || ioc.value.toLowerCase().includes(q) || ioc.type.toLowerCase().includes(q))
    );

    linkedEl.innerHTML = '';
    if (linked.length === 0) {
        linkedEl.appendChild(makeEmpty('No IOCs linked yet'));
    } else {
        linked.forEach(ioc => linkedEl.appendChild(buildIocChip(ioc, true, selectedAddIocIds, () => renderAddIocPicker(document.getElementById('addIocSearchInput')?.value || ''))));
    }

    availableEl.innerHTML = '';
    if (available.length === 0) {
        availableEl.appendChild(makeEmpty('No IOCs available' + (q ? ` matching "${filter}"` : '')));
    } else {
        available.forEach(ioc => availableEl.appendChild(buildIocChip(ioc, false, selectedAddIocIds, () => renderAddIocPicker(document.getElementById('addIocSearchInput')?.value || ''))));
    }
}

// ---- Shared chip builder ----
function makeEmpty(text) {
    const span = document.createElement('span');
    span.className = 'ioc-picker-empty';
    span.textContent = text;
    return span;
}

function buildIocChip(ioc, isLinked, idsArray, onToggle) {
    const chip = document.createElement('div');
    chip.className = `ioc-picker-chip ipc-${ioc.type.toLowerCase()}`;

    const typeEl = document.createElement('span');
    typeEl.className = 'ioc-chip-type';
    typeEl.textContent = ioc.type;

    const valEl = document.createElement('span');
    valEl.className = 'ioc-chip-value';
    valEl.title = ioc.value;
    valEl.textContent = ioc.value.length > 32 ? ioc.value.slice(0, 30) + '…' : ioc.value;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'ioc-chip-action';
    btn.textContent = isLinked ? '×' : '+';
    btn.addEventListener('click', () => {
        if (isLinked) {
            const idx = idsArray.indexOf(ioc.id);
            if (idx > -1) idsArray.splice(idx, 1);
        } else {
            idsArray.push(ioc.id);
        }
        onToggle();
    });

    chip.appendChild(typeEl);
    chip.appendChild(valEl);
    chip.appendChild(btn);
    return chip;
}

// ============================================
// UTILITY FUNCTIONS
// ============================================
function getCsrfToken() {
    const cookies = document.cookie.split('; ');
    const csrfCookie = cookies.find(row => row.startsWith('csrftoken='));
    if (csrfCookie) return csrfCookie.split('=')[1];
    const csrfInput = document.querySelector('[name="csrfmiddlewaretoken"]');
    if (csrfInput) return csrfInput.value;
    return '';
}
