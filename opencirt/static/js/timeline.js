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

        if (!data.observed_at && !(data.starting_time && data.ending_time)) {
            alert('Please provide an Observed time, or both a Starting and Ending time.');
            return;
        }

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
                const errorData = await response.json().catch(() => ({}));
                alert(`Error: ${errorData.error || errorData.message || 'Failed to save action'}`);
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
                const errorData = await response.json().catch(() => ({}));
                alert(`Error: ${errorData.error || errorData.message || 'Failed to update action'}`);
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
    const shownValue = (window.IocDefang && window.IocDefang.defang(ioc.type, ioc.value)) || ioc.value;
    valEl.title = shownValue;
    valEl.textContent = shownValue.length > 32 ? shownValue.slice(0, 30) + '…' : shownValue;

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

// ============================================
// TIMECHART
// ============================================
const timelineTimechart  = document.getElementById('timelineTimechart');
const timelineTypeLegend = document.getElementById('timelineTypeLegend');
const timelineActionTypes = document.getElementById('timelineActionTypes');
const timelineZoomIn     = document.getElementById('timelineZoomIn');
const timelineZoomOut    = document.getElementById('timelineZoomOut');
const timelineZoomReset  = document.getElementById('timelineZoomReset');

const PINNED_ACTION_TYPE_COLORS = {
    malicious: '#ef4444',
    defensive: '#3b82f6',
    mitigation: '#8b5cf6',
    alert: '#f59e0b',
    communication: '#14b8a6',
};
const FALLBACK_ACTION_TYPE_COLORS = [
    '#0ea5e9','#10b981','#f97316','#eab308','#a855f7','#06b6d4','#f43f5e','#84cc16',
];
const ACTION_TYPE_FALLBACK_LABELS = { other: 'Other' };
const ACTION_TYPE_ICONS = {
    malicious:     'fa-solid fa-skull-crossbones',
    defensive:     'fa-solid fa-shield',
    mitigation:    'fa-solid fa-wrench',
    alert:         'fa-solid fa-bell',
    communication: 'fa-solid fa-comments',
    other:         'fa-solid fa-circle-dot',
};

function tcToTitleCase(v) {
    return String(v||'').toLowerCase().replace(/[_-]+/g,' ').replace(/\b\w/g,m=>m.toUpperCase());
}
function getConfiguredActionTypes() {
    if (!timelineActionTypes) return [{ key:'other', label:'Other' }];
    const entries = Array.from(timelineActionTypes.querySelectorAll('[data-type]')).map(n=>{
        const key = String(n.getAttribute('data-type')||'').toLowerCase();
        const label = n.getAttribute('data-label') || tcToTitleCase(key);
        return key ? { key, label } : null;
    }).filter(Boolean);
    if (!entries.length) return [{ key:'other', label:'Other' }];
    if (!entries.some(e=>e.key==='other')) entries.push({ key:'other', label:'Other' });
    return entries;
}
function buildActionTypeColorMap(typeEntries) {
    const map = {}; let ci = 0;
    typeEntries.forEach(e=>{
        if (PINNED_ACTION_TYPE_COLORS[e.key]) { map[e.key]=PINNED_ACTION_TYPE_COLORS[e.key]; return; }
        map[e.key]=FALLBACK_ACTION_TYPE_COLORS[ci%FALLBACK_ACTION_TYPE_COLORS.length]; ci++;
    });
    if (!map.other) map.other='#9ca3af';
    return map;
}
const CONFIGURED_ACTION_TYPES = getConfiguredActionTypes();
const ACTION_TYPE_COLORS = buildActionTypeColorMap(CONFIGURED_ACTION_TYPES);
const ACTION_TYPE_LABELS = CONFIGURED_ACTION_TYPES.reduce((acc,e)=>{ acc[e.key]=e.label; return acc; }, {...ACTION_TYPE_FALLBACK_LABELS});

let tcPointsCache = [];
let tcView = null;
let tcDragState = null;
let tcMinH = 52;
let tcTooltipTimer = null;

function hexToRgb(hex) {
    const n = String(hex||'').trim().replace('#','');
    if (!/^[0-9a-fA-F]{6}$/.test(n)) return null;
    return { r:parseInt(n.slice(0,2),16), g:parseInt(n.slice(2,4),16), b:parseInt(n.slice(4,6),16) };
}
function tint(hex, alpha) {
    const rgb = hexToRgb(hex);
    if (!rgb) return `rgba(156,163,175,${alpha})`;
    return `rgba(${rgb.r},${rgb.g},${rgb.b},${alpha})`;
}
function normalizeActionType(v) {
    const raw = String(v||'').trim().toLowerCase();
    return ACTION_TYPE_LABELS[raw] ? raw : 'other';
}
function getActionTypeIconClass(v) {
    return ACTION_TYPE_ICONS[normalizeActionType(v)] || ACTION_TYPE_ICONS.other;
}

function applyTimelineTypeColors() {
    document.querySelectorAll('.tl-item[data-action-id]').forEach(item=>{
        const type  = normalizeActionType(item.dataset.actionType);
        const color = ACTION_TYPE_COLORS[type] || ACTION_TYPE_COLORS.other;
        const card  = item.querySelector('.tl-card');
        const dot   = item.querySelector('.tl-dot');
        const badge = item.querySelector('.tl-badge');
        const head  = item.querySelector('.tl-card-head');
        if (card)  card.style.borderLeftColor = color;
        if (dot)  { dot.style.background = color; dot.style.boxShadow = `0 0 0 3px ${tint(color,0.24)}`; }
        if (badge) { badge.style.background = tint(color,0.16); badge.style.color = color; }
        if (head)  head.style.background = tint(color,0.05);
    });
}

function setTimechartActive(actionId) {
    document.querySelectorAll('.tl-item.tl-item-chart-active').forEach(i=>i.classList.remove('tl-item-chart-active'));
    document.querySelectorAll('.timechart-point.is-active').forEach(p=>p.classList.remove('is-active'));
    if (!actionId) return;
    const item = document.querySelector(`.tl-item[data-action-id="${actionId}"]`);
    if (item) item.classList.add('tl-item-chart-active');
    const pt = timelineTimechart?.querySelector(`.timechart-point[data-action-id="${actionId}"]`);
    if (pt) pt.classList.add('is-active');
}
function focusActionFromChart(actionId) {
    const target = document.querySelector(`.tl-item[data-action-id="${actionId}"]`);
    if (!target) return;
    setTimechartActive(actionId);
    target.scrollIntoView({ behavior:'smooth', block:'center' });
}
function formatActionTimestamp(rawTime, fallback) {
    if (!rawTime) return fallback || 'No timestamp';
    const d = new Date(rawTime);
    if (Number.isNaN(d.getTime())) return fallback || 'No timestamp';
    return d.toLocaleString(undefined,{year:'numeric',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit'});
}

function ensureTooltip() {
    if (!timelineTimechart) return null;
    let t = timelineTimechart.querySelector('.timechart-tooltip');
    if (!t) { t=document.createElement('div'); t.className='timechart-tooltip'; t.setAttribute('aria-hidden','true'); timelineTimechart.appendChild(t); }
    return t;
}
function cancelTcHide() { if (tcTooltipTimer) { clearTimeout(tcTooltipTimer); tcTooltipTimer=null; } }
function scheduleTcHide(ms=90) { cancelTcHide(); tcTooltipTimer=setTimeout(hideTimechartTooltip,ms); }
function ensureSelectionBox() {
    if (!timelineTimechart) return null;
    let s = timelineTimechart.querySelector('.timechart-zoom-selection');
    if (!s) { s=document.createElement('div'); s.className='timechart-zoom-selection'; timelineTimechart.appendChild(s); }
    return s;
}
function showTimechartTooltip(marker) {
    cancelTcHide();
    const tooltip = ensureTooltip();
    if (!tooltip || !timelineTimechart) return;
    const typeLabel = marker.dataset.typeLabel || 'Other';
    const title     = marker.dataset.actionTitle || 'Untitled action';
    const when      = marker.dataset.actionTimeLabel || 'No timestamp';
    const color     = marker.style.getPropertyValue('--point-color') || ACTION_TYPE_COLORS.other;
    tooltip.innerHTML = `
        <div class="timechart-tooltip-title">${title}</div>
        <div class="timechart-tooltip-meta">
            <span class="timechart-tooltip-type">
                <span class="timechart-tooltip-type-dot" style="background:${color}"></span>
                ${typeLabel}
            </span>
            <span>${when}</span>
        </div>`;
    const railW = timelineTimechart.clientWidth;
    const ttW   = tooltip.offsetWidth || 260;
    const clamped = Math.max(ttW/2+8, Math.min(railW-ttW/2-8, marker.offsetLeft));
    tooltip.style.left = `${clamped}px`;
    tooltip.classList.add('show');
}
function hideTimechartTooltip() {
    cancelTcHide();
    timelineTimechart?.querySelector('.timechart-tooltip')?.classList.remove('show');
}

function resetTcView() {
    const times = tcPointsCache.filter(p=>Number.isFinite(p.timeMs)).map(p=>p.timeMs);
    if (!times.length) { tcView=null; return; }
    const mn=Math.min(...times), mx=Math.max(...times);
    tcView = { fullMin:mn, fullMax:mx, min:mn, max:mx };
}
function estimateTcHeight(points) {
    if (!points.length) return 52;
    const times = points.filter(p=>Number.isFinite(p.timeMs)).map(p=>p.timeMs);
    const hasT = !!times.length;
    const mn = hasT ? Math.min(...times) : 0;
    const mx = hasT ? Math.max(...times) : 0;
    const span = Math.max(1, mx-mn);
    const spacing = points.length>1 ? 100/(points.length-1) : 100;
    const laneMap = new Map(); let maxLane=0;
    points.forEach((p,i)=>{
        const fb = points.length===1 ? 50 : i*spacing;
        const pos = hasT && Number.isFinite(p.timeMs) ? ((p.timeMs-mn)/span)*100 : fb;
        const bkt = Math.round(Math.min(99,Math.max(1,pos))*2)/2;
        const lane = laneMap.get(bkt)||0; laneMap.set(bkt,lane+1); maxLane=Math.max(maxLane,lane);
    });
    return Math.max(52, 34+(maxLane+1)*14);
}
function zoomTimechart(scale) {
    if (!tcView) return;
    const full = Math.max(1, tcView.fullMax-tcView.fullMin);
    const cur  = Math.max(1, tcView.max-tcView.min);
    const next = Math.max(full*0.02, Math.min(full, cur*scale));
    const center = (tcView.min+tcView.max)/2;
    let mn=center-next/2, mx=center+next/2;
    if (mn<tcView.fullMin) { mn=tcView.fullMin; mx=mn+next; }
    if (mx>tcView.fullMax) { mx=tcView.fullMax; mn=mx-next; }
    tcView.min=mn; tcView.max=mx;
    renderTimechart();
}
function attachTcZoomInteractions() {
    if (!timelineTimechart || !tcView) return;
    const sel = ensureSelectionBox();
    if (!sel) return;
    timelineTimechart.addEventListener('mousedown', e=>{
        if (e.target.closest('.timechart-point') || !tcView) return;
        const rect = timelineTimechart.getBoundingClientRect();
        const sx = Math.max(0, Math.min(rect.width, e.clientX-rect.left));
        tcDragState = { startX:sx, currentX:sx };
        sel.style.display='block'; sel.style.left=`${sx}px`; sel.style.width='0px';
    });
    window.addEventListener('mousemove', e=>{
        if (!tcDragState || !tcView) return;
        const rect = timelineTimechart.getBoundingClientRect();
        const cx = Math.max(0, Math.min(rect.width, e.clientX-rect.left));
        tcDragState.currentX=cx;
        const left=Math.min(tcDragState.startX,cx), w=Math.abs(tcDragState.startX-cx);
        sel.style.left=`${left}px`; sel.style.width=`${w}px`;
    });
    window.addEventListener('mouseup', ()=>{
        if (!tcDragState || !tcView) return;
        const rect = timelineTimechart.getBoundingClientRect();
        const left=Math.min(tcDragState.startX,tcDragState.currentX);
        const right=Math.max(tcDragState.startX,tcDragState.currentX);
        sel.style.display='none';
        if (right-left>=12 && rect.width>0) {
            const span=tcView.max-tcView.min;
            const mn2=tcView.min+(left/rect.width)*span;
            const mx2=tcView.min+(right/rect.width)*span;
            if (mx2-mn2>0) { tcView.min=mn2; tcView.max=mx2; renderTimechart(); }
        }
        tcDragState=null;
    });
    timelineZoomIn?.addEventListener('click', ()=>zoomTimechart(0.6));
    timelineZoomOut?.addEventListener('click', ()=>zoomTimechart(1.6));
    timelineZoomReset?.addEventListener('click', ()=>{ resetTcView(); renderTimechart(); });
}

function renderTimechart() {
    if (!timelineTimechart || !tcPointsCache.length) return;
    const points = tcPointsCache;
    const times = points.filter(p=>Number.isFinite(p.timeMs)).map(p=>p.timeMs);
    const hasT = !!times.length;
    const vMin = hasT && tcView ? tcView.min : 0;
    const vMax = hasT && tcView ? tcView.max : 0;
    const vSpan = Math.max(1, vMax-vMin);

    timelineTimechart.querySelectorAll('.timechart-point').forEach(n=>n.remove());
    hideTimechartTooltip();

    const vis = points.filter(p=>{ if (!hasT || !Number.isFinite(p.timeMs)) return true; return p.timeMs>=vMin && p.timeMs<=vMax; });
    const spacing = vis.length>1 ? 100/(vis.length-1) : 100;
    const laneMap = new Map(); let maxLane=0;

    vis.forEach((p,vi)=>{
        const marker = document.createElement('button');
        marker.type='button'; marker.className='timechart-point';
        marker.dataset.actionId = p.actionId;
        marker.style.setProperty('--point-color', ACTION_TYPE_COLORS[p.actionType]||ACTION_TYPE_COLORS.other);
        marker.innerHTML = `<i class="${getActionTypeIconClass(p.actionType)} timechart-point-icon" aria-hidden="true"></i>`;

        const fb  = vis.length===1 ? 50 : vi*spacing;
        const pos = hasT && Number.isFinite(p.timeMs) ? ((p.timeMs-vMin)/vSpan)*100 : fb;
        const bpos = Math.min(99,Math.max(1,pos));
        marker.style.left=`${bpos}%`;

        const bkt = Math.round(bpos*2)/2;
        const lane = laneMap.get(bkt)||0; laneMap.set(bkt,lane+1); maxLane=Math.max(maxLane,lane);
        marker.style.setProperty('--marker-top', `${18+lane*14}px`);

        marker.title = `${ACTION_TYPE_LABELS[p.actionType]} | ${p.title} | ${p.timeLabel}`;
        marker.setAttribute('aria-label', marker.title);
        marker.dataset.typeLabel      = ACTION_TYPE_LABELS[p.actionType]||'Other';
        marker.dataset.actionTitle    = p.title;
        marker.dataset.actionTimeLabel= p.timeLabel;

        marker.addEventListener('mouseenter', ()=>{ setTimechartActive(p.actionId); showTimechartTooltip(marker); });
        marker.addEventListener('mouseleave', ()=>{ setTimechartActive(null); scheduleTcHide(); });
        marker.addEventListener('focus',      ()=>{ setTimechartActive(p.actionId); showTimechartTooltip(marker); });
        marker.addEventListener('blur',       ()=>{ setTimechartActive(null); scheduleTcHide(0); });
        marker.addEventListener('click',      ()=> focusActionFromChart(p.actionId));
        timelineTimechart.appendChild(marker);
    });

    timelineTimechart.style.height = `${Math.max(tcMinH, 34+(maxLane+1)*14)}px`;

    if (timelineTypeLegend) {
        timelineTypeLegend.innerHTML = CONFIGURED_ACTION_TYPES.map(e=>(
            `<span class="timechart-legend-item"><span class="timechart-legend-swatch" style="background:${ACTION_TYPE_COLORS[e.key]}"></span>${ACTION_TYPE_LABELS[e.key]}</span>`
        )).join('');
    }

    if (!timelineTimechart.dataset.hoverBound) {
        timelineTimechart.addEventListener('mouseleave',()=>{ setTimechartActive(null); scheduleTcHide(0); });
        timelineTimechart.dataset.hoverBound='1';
    }
}

function buildTimelineTimechart() {
    if (!timelineTimechart) return;
    const items = Array.from(document.querySelectorAll('.tl-item[data-action-id]'));
    if (!items.length) return;

    applyTimelineTypeColors();

    tcPointsCache = items.map((item,i)=>({
        actionId:   item.dataset.actionId,
        actionType: normalizeActionType(item.dataset.actionType),
        title:      item.querySelector('.tl-action-title')?.textContent?.trim() || `Action ${i+1}`,
        timeLabel:  formatActionTimestamp(item.dataset.actionTime, item.querySelector('.tl-time')?.textContent?.trim()),
        timeMs:     item.dataset.actionTime ? Date.parse(item.dataset.actionTime) : NaN,
        index:      i,
    }));

    tcMinH = estimateTcHeight(tcPointsCache);
    resetTcView();
    renderTimechart();
    attachTcZoomInteractions();

    items.forEach(item=>{
        item.addEventListener('mouseenter', ()=> setTimechartActive(item.dataset.actionId));
        item.addEventListener('mouseleave', ()=>{ setTimechartActive(null); hideTimechartTooltip(); });
    });
}

buildTimelineTimechart();
