/* ── Threat Intelligence Hub ─────────────────────────────────────────────── */

'use strict';

// ── State ─────────────────────────────────────────────────────────────────────

const state = {
    page:       1,
    totalPages: 1,
    filters:    {},
    selectedValue: null,
    typeChart:  null,
    verdictChart: null,
    campaigns:  [],
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function csrfToken() {
    return document.cookie.split('; ')
        .find(r => r.startsWith('csrftoken='))?.split('=')[1] ?? '';
}

function buildQuery(extra = {}) {
    const f = { ...state.filters, ...extra };
    const p = new URLSearchParams();
    Object.entries(f).forEach(([k, v]) => { if (v) p.set(k, v); });
    return p.toString();
}

function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function verdictBadge(v) {
    const icons = { malicious: '⚠', suspicious: '⚡', clean: '✓', unknown: '?' };
    const cls   = `ti-verdict-${v || 'unknown'}`;
    return `<span class="ti-verdict-badge ${cls}">${icons[v] || '?'} ${v || 'unknown'}</span>`;
}

function typeBadge(t) {
    return `<span class="ti-type-badge">${t || '—'}</span>`;
}

function statusBadge(s) {
    const labels = { COMPROMISED: 'Compromised', POTENTIALLY_COMPROMISED: 'Potential', SAFE: 'Safe' };
    return `<span class="ti-status-badge ti-status-${s}">${labels[s] || s}</span>`;
}

function sevBadge(s) {
    return `<span class="ti-sev-badge ti-sev-${s}">${s}</span>`;
}

// ── Quarterly preset buttons ──────────────────────────────────────────────────

function buildQuarterButtons() {
    const container = document.getElementById('tiQuarterBtns');
    const now = new Date();
    const quarters = [];

    // Generate last 6 quarters
    let year = now.getFullYear();
    let q    = Math.ceil((now.getMonth() + 1) / 3);

    for (let i = 0; i < 6; i++) {
        const startMonth = (q - 1) * 3;       // 0-indexed
        const endMonth   = startMonth + 2;
        const startDate  = new Date(year, startMonth, 1);
        const endDate    = new Date(year, endMonth + 1, 0);  // last day of quarter

        quarters.unshift({
            label: `Q${q} ${year}`,
            from:  startDate.toISOString().split('T')[0],
            to:    endDate.toISOString().split('T')[0],
        });

        q--;
        if (q === 0) { q = 4; year--; }
    }

    quarters.forEach(({ label, from, to }) => {
        const btn = document.createElement('button');
        btn.className   = 'ti-qbtn';
        btn.textContent = label;
        btn.dataset.from = from;
        btn.dataset.to   = to;
        btn.addEventListener('click', () => {
            const active = container.querySelector('.active');
            if (active === btn) {
                btn.classList.remove('active');
                document.getElementById('tiDateFrom').value = '';
                document.getElementById('tiDateTo').value   = '';
                state.filters.date_from = '';
                state.filters.date_to   = '';
            } else {
                container.querySelectorAll('.ti-qbtn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById('tiDateFrom').value = from;
                document.getElementById('tiDateTo').value   = to;
                state.filters.date_from = from;
                state.filters.date_to   = to;
            }
            state.page = 1;
            refresh();
        });
        container.appendChild(btn);
    });
}

// ── IOC Table ─────────────────────────────────────────────────────────────────

async function loadIocs() {
    const tbody = document.getElementById('tiTableBody');
    tbody.innerHTML = '<tr><td colspan="7" class="ti-loading"><div class="ti-spinner"></div> Loading…</td></tr>';

    const qs = buildQuery({ page: state.page });
    try {
        const resp = await fetch(`/api/threat-intel/iocs/?${qs}`);
        const data = await resp.json();

        state.totalPages = data.pages || 1;
        document.getElementById('tableTotal').textContent = `${data.total} IOC${data.total !== 1 ? 's' : ''}`;

        if (!data.iocs || data.iocs.length === 0) {
            tbody.innerHTML = '<tr class="ti-empty-row"><td colspan="7">No IOCs match the current filters.</td></tr>';
            document.getElementById('tiPagination').style.display = 'none';
            return;
        }

        tbody.innerHTML = data.iocs.map(ioc => {
            const ageDays = Math.floor((Date.now() - new Date(ioc.created_at)) / 86400000);
            const stale   = ageDays > 90;
            return `
            <tr class="ti-row${stale ? ' ti-row-stale' : ''}" data-value="${escHtml(ioc.value)}" data-type="${escHtml(ioc.type)}">
                <td class="ti-value-cell" title="${escHtml(ioc.value)}">
                    ${stale ? '<span class="ti-stale-icon" title="IOC older than 90 days — verify before sharing"><i class="fa-regular fa-clock"></i></span>' : ''}
                    ${escHtml(ioc.value.length > 36 ? ioc.value.slice(0, 34) + '…' : ioc.value)}
                </td>
                <td>${typeBadge(ioc.type)}</td>
                <td>${statusBadge(ioc.status)}</td>
                <td>${verdictBadge(ioc.verdict)}</td>
                <td>
                    <a class="ti-inc-link" href="/incident/${ioc.incident_id}/iocs"
                       onclick="event.stopPropagation()" title="${escHtml(ioc.incident)}">
                        ${escHtml(ioc.incident.length > 24 ? ioc.incident.slice(0, 22) + '…' : ioc.incident)}
                    </a>
                </td>
                <td>${formatDate(ioc.created_at)}</td>
                <td>
                    ${ioc.occurrences > 1
                        ? `<span class="ti-occ-badge"><i class="fa-solid fa-link-slash"></i> ×${ioc.occurrences}</span>`
                        : '<span style="color:var(--muted-color);font-size:.75rem;">1</span>'}
                </td>
            </tr>
        `;}).join('');

        // Pagination
        const pg = document.getElementById('tiPagination');
        pg.style.display = 'flex';
        document.getElementById('pageInfo').textContent = `Page ${state.page} of ${state.totalPages}`;
        document.getElementById('pagePrev').disabled = state.page <= 1;
        document.getElementById('pageNext').disabled = state.page >= state.totalPages;

    } catch (e) {
        tbody.innerHTML = `<tr class="ti-empty-row"><td colspan="7">Failed to load IOCs: ${e.message}</td></tr>`;
    }
}

function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

document.getElementById('pagePrev').addEventListener('click', () => {
    if (state.page > 1) { state.page--; loadIocs(); }
});
document.getElementById('pageNext').addEventListener('click', () => {
    if (state.page < state.totalPages) { state.page++; loadIocs(); }
});

// Event delegation for IOC rows — avoids inline onclick and the XSS risk of
// embedding arbitrary IOC values inside a JS string in an HTML attribute.
document.getElementById('tiTableBody').addEventListener('click', e => {
    const row = e.target.closest('tr.ti-row');
    if (row) pivotOn(row.dataset.value);
});

// ── Pivot Panel ───────────────────────────────────────────────────────────────

let _currentPivotValue = null;

async function pivotOn(value) {
    _currentPivotValue = value;

    // Highlight selected row
    document.querySelectorAll('.ti-row').forEach(r => r.classList.remove('selected'));
    document.querySelectorAll(`.ti-row[data-value="${CSS.escape(value)}"]`).forEach(r => r.classList.add('selected'));

    document.getElementById('pivotEmpty').style.display   = 'none';
    document.getElementById('pivotContent').style.display = 'block';

    document.getElementById('pivotValue').textContent = value;
    document.getElementById('pivotTypeBadge').innerHTML = '';
    document.getElementById('pivotVerdictBadge').innerHTML = '<span style="color:var(--muted-color)">Loading…</span>';
    document.getElementById('pivotIncList').innerHTML = '<div class="ti-loading"><div class="ti-spinner"></div></div>';
    document.getElementById('pivotRepSection').style.display = 'none';

    try {
        const resp = await fetch(`/api/threat-intel/pivot/?value=${encodeURIComponent(value)}`);
        const data = await resp.json();

        document.getElementById('pivotTypeBadge').innerHTML =
            data.incidents[0] ? typeBadge(data.incidents[0].type) : '';
        document.getElementById('pivotVerdictBadge').innerHTML =
            verdictBadge(data.reputation?.status);

        // Reputation breakdown
        const vt = data.reputation?.vt;
        if (vt) {
            document.getElementById('pivotRepSection').style.display = 'block';
            document.getElementById('pivotRepGrid').innerHTML = `
                <div class="ti-pivot-rep-item">
                    <span class="ti-pivot-rep-label">Malicious</span>
                    <span class="ti-pivot-rep-val rep-mal">${vt.malicious ?? '—'}</span>
                </div>
                <div class="ti-pivot-rep-item">
                    <span class="ti-pivot-rep-label">Suspicious</span>
                    <span class="ti-pivot-rep-val rep-susp">${vt.suspicious ?? '—'}</span>
                </div>
                <div class="ti-pivot-rep-item">
                    <span class="ti-pivot-rep-label">Harmless</span>
                    <span class="ti-pivot-rep-val rep-clean">${vt.harmless ?? '—'}</span>
                </div>
                <div class="ti-pivot-rep-item">
                    <span class="ti-pivot-rep-label">Total engines</span>
                    <span class="ti-pivot-rep-val">${vt.total ?? '—'}</span>
                </div>
                ${vt.country ? `
                <div class="ti-pivot-rep-item">
                    <span class="ti-pivot-rep-label">Country</span>
                    <span class="ti-pivot-rep-val">${vt.country}</span>
                </div>` : ''}
                ${vt.as_owner ? `
                <div class="ti-pivot-rep-item">
                    <span class="ti-pivot-rep-label">ASN owner</span>
                    <span class="ti-pivot-rep-val" title="${escHtml(vt.as_owner)}">${escHtml(String(vt.as_owner).slice(0, 14))}</span>
                </div>` : ''}
            `;
        }

        // Incident list
        document.getElementById('pivotIncTitle').textContent =
            `Appears in ${data.count} incident${data.count !== 1 ? 's' : ''}`;

        if (data.incidents.length === 0) {
            document.getElementById('pivotIncList').innerHTML =
                '<p style="color:var(--text-color-2);font-size:.82rem;">Not found in any accessible incidents.</p>';
        } else {
            document.getElementById('pivotIncList').innerHTML = data.incidents.map(inc => `
                <a class="ti-pivot-inc-row" href="/incident/${inc.incident_id}/iocs">
                    <span class="ti-pivot-inc-name">${escHtml(inc.incident)}</span>
                    <div class="ti-pivot-inc-meta">
                        ${sevBadge(inc.severity)}
                        <span>${verdictBadge(inc.verdict)}</span>
                        <span>${statusBadge(inc.status)}</span>
                        <span><i class="fa-regular fa-calendar"></i> ${formatDate(inc.created_at)}</span>
                    </div>
                </a>
            `).join('');
        }

    } catch (e) {
        document.getElementById('pivotVerdictBadge').innerHTML = '—';
        document.getElementById('pivotIncList').innerHTML =
            `<p style="color:#dc2626;font-size:.82rem;">Error: ${e.message}</p>`;
    }
}

function copyPivotValue() {
    if (!_currentPivotValue) return;
    navigator.clipboard.writeText(_currentPivotValue).then(() => {
        const btn = document.getElementById('pivotCopyBtn');
        btn.classList.add('copied');
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied';
        setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
        }, 2000);
    });
}

// ── Heatmap ───────────────────────────────────────────────────────────────────

async function loadHeatmap() {
    const today = new Date();
    const defaultFrom = (() => {
        const d = new Date(today);
        d.setMonth(d.getMonth() - 3);
        return d.toISOString().split('T')[0];
    })();

    const fromIsDefault = !state.filters.date_from;
    const toIsDefault   = !state.filters.date_to;

    // Use toolbar dates if set; otherwise default to 3 months back
    const from = state.filters.date_from || defaultFrom;
    const to   = state.filters.date_to   || today.toISOString().split('T')[0];

    // Update title to reflect actual range
    const titleEl = document.getElementById('heatmapTitle');
    if (titleEl) {
        if (fromIsDefault && toIsDefault) {
            titleEl.textContent = 'IOC activity — past 3 months';
        } else {
            const fmt = d => new Date(d + 'T00:00:00').toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
            titleEl.textContent = `IOC activity — ${fmt(from)} → ${fmt(to)}`;
        }
    }

    // Pass campaign/type/verdict filters too so heatmap matches the table
    const extra = {};
    if (state.filters.campaign) extra.campaign = state.filters.campaign;
    if (state.filters.type)     extra.type     = state.filters.type;
    if (state.filters.verdict)  extra.verdict  = state.filters.verdict;

    const params = new URLSearchParams({ date_from: from, date_to: to, ...extra });
    const resp = await fetch(`/api/threat-intel/heatmap/?${params}`);
    const data = await resp.json();

    buildHeatmap(data.days);

    // Scroll to rightmost position when content overflows (most recent data visible)
    requestAnimationFrame(() => {
        const outer = document.getElementById('tiHeatmap').closest('.ti-heatmap-outer');
        outer.scrollLeft = outer.scrollWidth;
    });
}

function buildHeatmap(days) {
    const container     = document.getElementById('tiHeatmap');
    const monthLabels   = document.getElementById('heatmapMonthLabels');
    const tooltip       = document.getElementById('hmTooltip');

    container.innerHTML   = '';
    monthLabels.innerHTML = '';

    if (!days || days.length === 0) return;

    const counts = days.map(d => d.count);
    const maxVal = Math.max(...counts, 1);

    function level(c) {
        if (c === 0) return '0';
        const r = c / maxVal;
        if (r < 0.2) return '1';
        if (r < 0.4) return '2';
        if (r < 0.6) return '3';
        if (r < 0.8) return '4';
        return '5';
    }

    // Figure out day-of-week for first cell (to pad the grid correctly)
    const firstDate = new Date(days[0].date + 'T00:00:00');
    const firstDow  = (firstDate.getDay() + 6) % 7;  // Mon=0 … Sun=6

    // Pad start so first day lands in the right row
    for (let i = 0; i < firstDow; i++) {
        const pad = document.createElement('div');
        pad.style.visibility = 'hidden';
        pad.className = 'ti-hm-cell';
        container.appendChild(pad);
    }

    let prevMonth  = -1;
    let colCount   = Math.floor(firstDow);  // columns used so far
    const pendingLabels = [];               // collect before we know final colCount

    days.forEach(({ date, count }) => {
        const d   = new Date(date + 'T00:00:00');
        const dow = (d.getDay() + 6) % 7;

        // Month label when we start a new column (week) and month changes
        if (dow === 0) {
            colCount++;
            const m = d.getMonth();
            if (m !== prevMonth) {
                prevMonth = m;
                const span = document.createElement('span');
                span.textContent = d.toLocaleString('en-GB', { month: 'short' });
                span.style.gridColumn = colCount;
                span.style.whiteSpace = 'nowrap';
                pendingLabels.push(span);
            }
        }

        const cell = document.createElement('div');
        cell.className     = 'ti-hm-cell';
        cell.dataset.level = level(count);
        cell.dataset.date  = date;
        cell.dataset.count = count;

        cell.addEventListener('mouseenter', e => {
            tooltip.textContent = `${date}: ${count} IOC${count !== 1 ? 's' : ''}`;
            tooltip.classList.add('visible');
        });
        cell.addEventListener('mousemove', e => {
            tooltip.style.left = (e.clientX + 12) + 'px';
            tooltip.style.top  = (e.clientY - 28) + 'px';
        });
        cell.addEventListener('mouseleave', () => tooltip.classList.remove('visible'));

        // Click to filter table to this day
        cell.addEventListener('click', () => {
            document.getElementById('tiDateFrom').value = date;
            document.getElementById('tiDateTo').value   = date;
            state.filters.date_from = date;
            state.filters.date_to   = date;
            // Deactivate quarter buttons
            document.querySelectorAll('.ti-qbtn').forEach(b => b.classList.remove('active'));
            state.page = 1;
            refresh();
        });

        container.appendChild(cell);
    });

    // Apply month labels now that we know the final column count
    if (pendingLabels.length > 0) {
        monthLabels.style.display = 'grid';
        monthLabels.style.gridTemplateColumns = `repeat(${colCount}, 16px)`;
        pendingLabels.forEach(s => monthLabels.appendChild(s));
    }
}

// ── Stats / Charts ────────────────────────────────────────────────────────────

const OCHRE = ['#c49840','#d4b06e','#e8cc8e','#f0dba8','#f5e8cc','#8b6b00','#a07830','#b89050'];
const VERDICT_COLORS = {
    malicious:  '#dc2626',
    suspicious: '#d97706',
    clean:      '#16a34a',
    unknown:    '#9aa6b2',
};

async function loadStats() {
    const qs = buildQuery({});
    const resp = await fetch(`/api/threat-intel/stats/?${qs}`);
    const data = await resp.json();

    // KPI updates
    document.getElementById('kpiTotal').textContent     = data.total;
    document.getElementById('kpiUnique').textContent    = data.unique;
    document.getElementById('kpiMalicious').textContent = data.malicious;
    document.getElementById('kpiSuspicious').textContent = data.suspicious;
    document.getElementById('kpiIncidents').textContent = data.incident_count;

    // Type donut
    const typeLabels = data.by_type.map(r => r.type);
    const typeValues = data.by_type.map(r => r.cnt);

    if (state.typeChart) state.typeChart.destroy();
    state.typeChart = new Chart(document.getElementById('typeChart'), {
        type: 'doughnut',
        data: {
            labels:   typeLabels,
            datasets: [{ data: typeValues, backgroundColor: OCHRE, borderWidth: 0 }],
        },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: '58%',
            plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } },
        },
    });

    // Verdict donut
    const repLabels  = ['malicious', 'suspicious', 'clean', 'unknown'];
    const repValues  = [data.malicious, data.suspicious, data.clean,
                        data.total - data.malicious - data.suspicious - data.clean];
    const repColors  = repLabels.map(l => VERDICT_COLORS[l]);

    if (state.verdictChart) state.verdictChart.destroy();
    state.verdictChart = new Chart(document.getElementById('verdictChart'), {
        type: 'doughnut',
        data: {
            labels:   repLabels,
            datasets: [{ data: repValues, backgroundColor: repColors, borderWidth: 0 }],
        },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: '58%',
            plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } },
        },
    });
}

// ── Export URLs ───────────────────────────────────────────────────────────────

function updateExportLinks() {
    const qs = buildQuery({});
    document.getElementById('exportCsv').href  = `/api/threat-intel/export/csv/?${qs}`;
    document.getElementById('exportJson').href = `/api/threat-intel/export/json/?${qs}`;
    document.getElementById('exportPdf').href  = `/api/threat-intel/export/pdf/?${qs}`;
}

// ── Campaigns ─────────────────────────────────────────────────────────────────

const CAMPAIGN_COLORS = ['#c49840','#dc2626','#2563eb','#16a34a','#9333ea','#db2777','#0891b2','#65a30d'];

async function loadCampaigns() {
    try {
        const resp = await fetch('/api/campaigns/');
        const data = await resp.json();
        state.campaigns = data.campaigns;
        renderCampaigns();
    } catch (e) {
        document.getElementById('campaignGrid').innerHTML =
            `<div class="ti-no-campaigns">Failed to load campaigns.</div>`;
    }
}

const SEV_COLORS = {
    CRITICAL: '#dc2626', HIGH: '#ea580c', MEDIUM: '#d97706', LOW: '#16a34a',
};

function renderCampaigns() {
    const grid = document.getElementById('campaignGrid');
    if (state.campaigns.length === 0) {
        grid.innerHTML = `<div class="ti-no-campaigns">
            <i class="fa-solid fa-layer-group" style="font-size:1.5rem;color:var(--border-color);margin-bottom:8px;display:block;"></i>
            No campaigns yet. Group related incidents together to track threat actors across events.
        </div>`;
        return;
    }

    grid.innerHTML = state.campaigns.map(c => {
        // Campaign IDs are integers so safe in onclick; names go into data attributes only
        const incTags = (c.incidents || []).map(inc => `
            <a class="ti-camp-inc-tag" href="/incident/${inc.id}/overview" onclick="event.stopPropagation()"
               title="${escHtml(inc.name)}">
                <span class="ti-camp-inc-dot" style="background:${SEV_COLORS[inc.severity] || '#9aa6b2'}"></span>
                ${escHtml(inc.name.length > 22 ? inc.name.slice(0, 20) + '…' : inc.name)}
            </a>
        `).join('');

        return `
        <div class="ti-campaign-card ${state.filters.campaign == c.id ? 'active-campaign' : ''}"
             data-camp-id="${c.id}" onclick="filterByCampaign(${c.id})">
            <div class="ti-campaign-stripe" style="background:${c.color}"></div>
            <div class="ti-campaign-body">
                <div class="ti-campaign-name">${escHtml(c.name)}</div>
                ${c.description ? `<div class="ti-campaign-desc">${escHtml(c.description)}</div>` : ''}
                ${incTags ? `<div class="ti-campaign-incidents">${incTags}</div>` : ''}
                <div class="ti-campaign-stats">
                    <span class="ti-campaign-stat">
                        <i class="fa-solid fa-virus"></i> ${c.ioc_count} IOC${c.ioc_count !== 1 ? 's' : ''}
                    </span>
                </div>
                ${(c.start_date || c.end_date) ? `
                <div class="ti-campaign-dates">
                    ${c.start_date ? formatDate(c.start_date) : '?'} → ${c.end_date ? formatDate(c.end_date) : 'ongoing'}
                </div>` : ''}
            </div>
            <div class="ti-campaign-actions" onclick="event.stopPropagation()">
                <button class="ti-camp-action-btn" onclick="openCampaignModal(${c.id})">
                    <i class="fa-solid fa-pen"></i> Edit
                </button>
                <button class="ti-camp-action-btn delete"
                        data-del-id="${c.id}" data-del-name="${escHtml(c.name)}"
                        onclick="deleteCampaignFromAttr(this)">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        </div>`;
    }).join('');
}

function filterByCampaign(id) {
    if (state.filters.campaign == id) {
        state.filters.campaign = '';
        document.getElementById('tiCampaignFilter').value = '';
    } else {
        state.filters.campaign = id;
        document.getElementById('tiCampaignFilter').value = id;
    }
    state.page = 1;
    refresh();
    renderCampaigns();
}

// ── Campaign Modal ────────────────────────────────────────────────────────────

function buildColorSwatches() {
    const row = document.getElementById('colorSwatches');
    row.innerHTML = CAMPAIGN_COLORS.map(c => `
        <div class="ti-color-swatch ${c === '#c49840' ? 'selected' : ''}"
             style="background:${c}" data-color="${c}"
             onclick="selectColor('${c}')"></div>
    `).join('');
}

function selectColor(color) {
    document.querySelectorAll('.ti-color-swatch').forEach(s => {
        s.classList.toggle('selected', s.dataset.color === color);
    });
}

function selectedColor() {
    return document.querySelector('.ti-color-swatch.selected')?.dataset.color || '#c49840';
}

function openCampaignModal(campaignId = null) {
    buildColorSwatches();
    const modal = document.getElementById('campaignModal');
    document.getElementById('campaignModalTitle').textContent = campaignId ? 'Edit Campaign' : 'New Campaign';
    document.getElementById('campaignId').value    = campaignId || '';
    document.getElementById('campaignName').value  = '';
    document.getElementById('campaignDesc').value  = '';
    document.getElementById('campaignStart').value = '';
    document.getElementById('campaignEnd').value   = '';

    // Uncheck all
    document.querySelectorAll('.inc-cb').forEach(cb => cb.checked = false);

    if (campaignId) {
        const c = state.campaigns.find(x => x.id === campaignId);
        if (c) {
            document.getElementById('campaignName').value  = c.name;
            document.getElementById('campaignDesc').value  = c.description;
            document.getElementById('campaignStart').value = c.start_date || '';
            document.getElementById('campaignEnd').value   = c.end_date   || '';
            selectColor(c.color || '#c49840');

            // Fetch current incidents for this campaign to pre-check
            fetch(`/api/campaigns/`).then(r => r.json()).then(data => {
                const camp = data.campaigns.find(x => x.id === campaignId);
                // We'd need incident ids — use full update approach: keep existing on save
            });
        }
    }

    modal.classList.add('open');
}

function closeCampaignModal() {
    document.getElementById('campaignModal').classList.remove('open');
}

async function saveCampaign() {
    const id   = document.getElementById('campaignId').value;
    const name = document.getElementById('campaignName').value.trim();
    if (!name) { alert('Campaign name is required.'); return; }

    const incident_ids = Array.from(document.querySelectorAll('.inc-cb:checked')).map(cb => parseInt(cb.value));

    const payload = {
        name,
        description: document.getElementById('campaignDesc').value,
        color:       selectedColor(),
        start_date:  document.getElementById('campaignStart').value || null,
        end_date:    document.getElementById('campaignEnd').value   || null,
        incident_ids,
    };

    const url = id ? `/api/campaigns/${id}/update/` : '/api/campaigns/create/';

    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
            body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (data.status === 'created' || data.status === 'updated') {
            closeCampaignModal();
            loadCampaigns();
        } else {
            alert(data.error || 'Save failed.');
        }
    } catch (e) {
        alert('Network error: ' + e.message);
    }
}

function deleteCampaignFromAttr(btn) {
    const id   = parseInt(btn.dataset.delId, 10);
    const name = btn.dataset.delName;  // read from data attribute, never from inline JS string
    deleteCampaign(id, name);
}

async function deleteCampaign(id, name) {
    if (!confirm(`Delete campaign "${name}"? This will not delete the linked incidents.`)) return;
    try {
        await fetch(`/api/campaigns/${id}/delete/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken() },
        });
        if (state.filters.campaign == id) {
            state.filters.campaign = '';
            document.getElementById('tiCampaignFilter').value = '';
        }
        loadCampaigns();
        refresh();
    } catch (e) {
        alert('Delete failed: ' + e.message);
    }
}

// Close modal on overlay click
document.getElementById('campaignModal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeCampaignModal();
});

// ── Filter wiring ─────────────────────────────────────────────────────────────

let _debounceTimer = null;

function debounce(fn, ms = 350) {
    clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(fn, ms);
}

function refresh() {
    updateExportLinks();
    loadIocs();
    loadStats();
    loadHeatmap();
}

document.getElementById('tiSearch').addEventListener('input', e => {
    state.filters.search = e.target.value;
    state.page = 1;
    debounce(refresh);
});

document.getElementById('tiTypeFilter').addEventListener('change', e => {
    state.filters.type = e.target.value;
    state.page = 1;
    refresh();
});

document.getElementById('tiStatusFilter').addEventListener('change', e => {
    state.filters.status = e.target.value;
    state.page = 1;
    refresh();
});

document.getElementById('tiVerdictFilter').addEventListener('change', e => {
    state.filters.verdict = e.target.value;
    state.page = 1;
    refresh();
});

document.getElementById('tiTlpFilter').addEventListener('change', e => {
    state.filters.tlp = e.target.value;
    state.page = 1;
    refresh();
});

document.getElementById('tiCampaignFilter').addEventListener('change', e => {
    state.filters.campaign = e.target.value;
    state.page = 1;
    refresh();
    renderCampaigns();
});

document.getElementById('tiDateFrom').addEventListener('change', e => {
    state.filters.date_from = e.target.value;
    document.querySelectorAll('.ti-qbtn').forEach(b => b.classList.remove('active'));
    state.page = 1;
    refresh();
});

document.getElementById('tiDateTo').addEventListener('change', e => {
    state.filters.date_to = e.target.value;
    document.querySelectorAll('.ti-qbtn').forEach(b => b.classList.remove('active'));
    state.page = 1;
    refresh();
});

// ── Tab switching ─────────────────────────────────────────────────────────────

function switchTab(tab, btn) {
    document.querySelectorAll('.ti-tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.ti-tab-panel').forEach(p => p.style.display = 'none');
    btn.classList.add('active');
    document.getElementById('tab-' + tab).style.display = 'flex';

    if (tab === 'campaigns') {
        loadCampaignStats();
        loadCampaigns();
    }
}

// ── Campaign tab state ────────────────────────────────────────────────────────

const campState = { date_from: '', date_to: '' };

function buildCampPeriodButtons() {
    const container = document.getElementById('campPeriodBtns');
    const now = new Date();
    const y   = now.getFullYear();
    const m   = now.getMonth();

    function iso(d) { return d.toISOString().split('T')[0]; }
    function lastDay(year, mo) { return new Date(year, mo + 1, 0); }

    // Quarter helper
    const q   = Math.ceil((m + 1) / 3);
    const qStart = (q - 1) * 3;

    const presets = [
        {
            label: 'This month',
            from: iso(new Date(y, m, 1)),
            to:   iso(lastDay(y, m)),
        },
        {
            label: 'Last month',
            from: iso(new Date(y, m - 1, 1)),
            to:   iso(lastDay(y, m - 1)),
        },
        {
            label: `Q${q} ${y}`,
            from: iso(new Date(y, qStart, 1)),
            to:   iso(lastDay(y, qStart + 2)),
        },
        {
            label: q > 1 ? `Q${q - 1} ${y}` : `Q4 ${y - 1}`,
            from: iso(new Date(q > 1 ? y : y - 1, q > 1 ? qStart - 3 : 9, 1)),
            to:   iso(lastDay(q > 1 ? y : y - 1, q > 1 ? qStart - 1 : 11)),
        },
        {
            label: 'Last 6 months',
            from: iso(new Date(y, m - 5, 1)),
            to:   iso(lastDay(y, m)),
        },
        {
            label: `${y}`,
            from: iso(new Date(y, 0, 1)),
            to:   iso(new Date(y, 11, 31)),
        },
    ];

    presets.forEach(({ label, from, to }) => {
        const btn = document.createElement('button');
        btn.className    = 'ti-qbtn';
        btn.textContent  = label;
        btn.dataset.from = from;
        btn.dataset.to   = to;
        btn.addEventListener('click', () => {
            const active = container.querySelector('.active');
            if (active === btn) {
                btn.classList.remove('active');
                document.getElementById('campDateFrom').value = '';
                document.getElementById('campDateTo').value   = '';
                campState.date_from = '';
                campState.date_to   = '';
            } else {
                container.querySelectorAll('.ti-qbtn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById('campDateFrom').value = from;
                document.getElementById('campDateTo').value   = to;
                campState.date_from = from;
                campState.date_to   = to;
            }
            updateCampExportLink();
            loadCampaignStats();
        });
        container.appendChild(btn);
    });
}

function updateCampExportLink() {
    const link = document.getElementById('exportCampPdf');
    const p = new URLSearchParams();
    if (campState.date_from) p.set('date_from', campState.date_from);
    if (campState.date_to)   p.set('date_to',   campState.date_to);
    const qs = p.toString();
    link.href = '/api/threat-intel/export/campaign-pdf/' + (qs ? '?' + qs : '');
}

async function loadCampaignStats() {
    const p = new URLSearchParams();
    if (campState.date_from) p.set('date_from', campState.date_from);
    if (campState.date_to)   p.set('date_to',   campState.date_to);

    try {
        const resp = await fetch(`/api/threat-intel/campaign-stats/?${p}`);
        const data = await resp.json();

        document.getElementById('campKpiTotal').textContent    = data.total     ?? '—';
        document.getElementById('campKpiOpen').textContent     = (data.open ?? 0) + (data.in_progress ?? 0);
        document.getElementById('campKpiCritHigh').textContent = data.crit_high ?? '—';
        document.getElementById('campKpiResolved').textContent = (data.resolved ?? 0) + (data.closed ?? 0);
        document.getElementById('campKpiCampaigns').textContent = data.campaigns ?? '—';
        document.getElementById('campKpiTtd').textContent      = data.avg_ttd    ?? '—';
        document.getElementById('campKpiTtr').textContent      = data.avg_ttr    ?? '—';
        document.getElementById('campKpiDur').textContent      = data.avg_duration ?? '—';

        renderMonthlyBars(data.monthly || []);
    } catch (e) {
        console.error('Campaign stats error:', e);
    }
}

function renderMonthlyBars(monthly) {
    const wrap = document.getElementById('campMonthlyBars');
    if (!monthly.length) {
        wrap.innerHTML = '<div class="ti-monthly-empty">No incident data for this period.</div>';
        return;
    }

    const maxCount = Math.max(...monthly.map(m => m.count), 1);

    wrap.innerHTML = monthly.map(({ month, count }) => {
        const heightPct = Math.max(4, Math.round((count / maxCount) * 100));
        const label = new Date(month + '-01').toLocaleDateString('en-GB', { month: 'short', year: '2-digit' });
        return `
            <div class="ti-monthly-col">
                <span class="ti-monthly-count">${count}</span>
                <div class="ti-monthly-bar-wrap">
                    <div class="ti-monthly-bar" style="height:${heightPct}%" title="${count} incident${count !== 1 ? 's' : ''} in ${label}"></div>
                </div>
                <span class="ti-monthly-label">${label}</span>
            </div>
        `;
    }).join('');
}

document.getElementById('campDateFrom').addEventListener('change', e => {
    campState.date_from = e.target.value;
    document.querySelectorAll('#campPeriodBtns .ti-qbtn').forEach(b => b.classList.remove('active'));
    updateCampExportLink();
    loadCampaignStats();
});

document.getElementById('campDateTo').addEventListener('change', e => {
    campState.date_to = e.target.value;
    document.querySelectorAll('#campPeriodBtns .ti-qbtn').forEach(b => b.classList.remove('active'));
    updateCampExportLink();
    loadCampaignStats();
});

// ── Init ──────────────────────────────────────────────────────────────────────

buildQuarterButtons();
buildCampPeriodButtons();
updateExportLinks();
updateCampExportLink();
loadIocs();
loadStats();
loadHeatmap();
loadCampaigns();  // populate state.campaigns for the IOC tab campaign filter
