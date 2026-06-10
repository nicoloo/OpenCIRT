document.addEventListener('DOMContentLoaded', function () {
    const modalAdd = document.getElementById('addIocModal');
    const modalAddBtn = document.getElementById('addIocBtn');
    const modalEdit = document.getElementById('editIocModal');
    const saveEditButton = document.getElementById('saveEditIoC');
    const modalType = document.getElementById('modal-ioc-type');
    const modalValue = document.getElementById('modal-ioc-value');
    const modalStatus = document.getElementById('modal-ioc-status');
    const modalDescription = document.getElementById('modal-ioc-description');
    const modalCreatedBy = document.getElementById('modal-ioc-createdby');
    const modalCreatedAt = document.getElementById('modal-ioc-createdat');
    const modalActions = document.getElementById('modal-ioc-actions');
    const csrfToken = document.getElementById('csrf-token').value;
    const searchInput = document.getElementById('ioc-search');
    const typeFilter = document.getElementById('ioc-type-filter');
    let currentIoCId = null;

    // ── Defang ───────────────────────────────────────────────────────────

    const URL_RE = /^(https?|ftp):\/\//i;

    function defangUrl(v) {
        // hxxp[:]// or hxxps[:]// or fxp[:]//
        v = v.replace(/^https:\/\//i, 'hxxps[:]//');
        v = v.replace(/^http:\/\//i,  'hxxp[:]//');
        v = v.replace(/^ftp:\/\//i,   'fxp[:]//');
        // defang all remaining dots
        v = v.replace(/\./g, '[.]');
        return v;
    }

    function defang(type, value) {
        if (!value) return null;
        const v = value.trim();

        // Explicit URL type
        if (type === 'URL') return defangUrl(v);

        // IP address: replace all dots
        if (type === 'IPADRESS') return v.replace(/\./g, '[.]');

        // Email: defang @ and domain dots
        if (type === 'EMAIL') {
            const at = v.indexOf('@');
            if (at !== -1) {
                return v.slice(0, at) + '[@]' + v.slice(at + 1).replace(/\./g, '[.]');
            }
            return v.replace(/\./g, '[.]');
        }

        // Network/CIDR: defang if URL-shaped, otherwise just dots
        if (type === 'NETWORK') {
            return URL_RE.test(v) ? defangUrl(v) : v.replace(/\./g, '[.]');
        }

        // Any other type: auto-detect URL and defang it
        if (URL_RE.test(v)) return defangUrl(v);

        return null; // nothing to defang
    }

    // Apply defanging to all value cells
    document.querySelectorAll('.ioc-value-cell').forEach(cell => {
        const raw     = cell.dataset.raw  || '';
        const type    = cell.dataset.type || '';
        const defanged = defang(type, raw);

        if (!defanged) return; // no defang needed for this type

        cell.innerHTML = '';

        const wrap = document.createElement('span');
        wrap.className = 'ioc-value-wrap';

        const span = document.createElement('span');
        span.className = 'ioc-defanged';
        span.textContent = defanged;
        span.title = 'Defanged — raw: ' + raw;
        wrap.appendChild(span);

        const badge = document.createElement('span');
        badge.className = 'defang-badge';
        badge.textContent = 'defanged';
        badge.title = 'Value is displayed in defanged format for safe sharing';
        wrap.appendChild(badge);

        const copyBtn = document.createElement('button');
        copyBtn.className = 'ioc-copy-raw';
        copyBtn.title = 'Copy raw value';
        copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>';
        copyBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            navigator.clipboard.writeText(raw).then(() => {
                copyBtn.innerHTML = '<i class="fa-solid fa-check"></i>';
                copyBtn.classList.add('copied');
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>';
                    copyBtn.classList.remove('copied');
                }, 1500);
            });
        });
        wrap.appendChild(copyBtn);

        cell.appendChild(wrap);
    });

    // ── Modal open/close ─────────────────────────────────────────────────

    if (modalAddBtn) {
        modalAddBtn.addEventListener('click', function () {
            modalAdd.style.display = 'flex';
            const created = document.getElementById('created_at');
            if (created) created.value = new Date().toISOString();
        });
    }

    document.querySelectorAll('.add-ioc-modal').forEach(btn => {
        btn.addEventListener('click', () => { modalAdd.style.display = 'none'; });
    });

    document.querySelectorAll('.ioc-modal').forEach(btn => {
        btn.addEventListener('click', () => { modalEdit.style.display = 'none'; });
    });

    window.addEventListener('click', function (event) {
        if (event.target === modalAdd) modalAdd.style.display = 'none';
        if (event.target === modalEdit) modalEdit.style.display = 'none';
    });

    // ── Format validation ─────────────────────────────────────────────────

    function validateIocValue(type, value) {
        if (!value) return { ok: false, message: 'Value is required.' };

        switch (type) {
            case 'IPADRESS': {
                const ipv4 = /^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$/;
                const ipv6 = /^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(\/\d{1,3})?$/;
                if (!ipv4.test(value) && !ipv6.test(value))
                    return { ok: false, message: 'Invalid IP address. Expected: 192.168.1.1 or 2001:db8::1' };
                if (ipv4.test(value)) {
                    const octets = value.split('/')[0].split('.');
                    if (octets.some(o => parseInt(o) > 255))
                        return { ok: false, message: 'Invalid IP address: each octet must be 0–255.' };
                }
                break;
            }
            case 'EMAIL': {
                if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value))
                    return { ok: false, message: 'Invalid email format. Expected: user@domain.com' };
                break;
            }
            case 'HASH': {
                const md5    = /^[a-fA-F0-9]{32}$/;
                const sha1   = /^[a-fA-F0-9]{40}$/;
                const sha256 = /^[a-fA-F0-9]{64}$/;
                const sha512 = /^[a-fA-F0-9]{128}$/;
                if (!md5.test(value) && !sha1.test(value) && !sha256.test(value) && !sha512.test(value))
                    return { ok: false, message: 'Invalid hash. Expected MD5 (32), SHA1 (40), SHA256 (64), or SHA512 (128) hex chars.' };
                break;
            }
            case 'URL': {
                if (!/^https?:\/\/.+/i.test(value) && !/^ftp:\/\/.+/i.test(value))
                    return { ok: false, message: 'Invalid URL. Expected: http://… or https://…' };
                break;
            }
            case 'NETWORK': {
                const url  = /^https?:\/\/.+/i;
                const cidr = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
                if (!url.test(value) && !cidr.test(value))
                    return { ok: false, message: 'Invalid format. Expected URL (http://…) or CIDR (192.168.1.0/24).' };
                break;
            }
            case 'SRC_PORT':
            case 'DST_PORT': {
                const port = parseInt(value);
                if (isNaN(port) || port < 1 || port > 65535)
                    return { ok: false, message: 'Invalid port. Expected a number between 1 and 65535.' };
                break;
            }
        }
        return { ok: true };
    }

    const addForm      = document.querySelector('#addIocModal form');
    const iocValueInput = document.getElementById('ioc-value');
    const iocTypeSelect = document.getElementById('ioc-type');
    const errorEl       = document.getElementById('ioc-value-error');

    if (addForm) {
        addForm.addEventListener('submit', function (e) {
            const type  = iocTypeSelect ? iocTypeSelect.value : '';
            const value = iocValueInput ? iocValueInput.value.trim() : '';
            const result = validateIocValue(type, value);
            if (!result.ok) {
                e.preventDefault();
                errorEl.textContent = result.message;
                errorEl.style.display = 'block';
            } else {
                errorEl.style.display = 'none';
            }
        });

        if (iocValueInput) {
            iocValueInput.addEventListener('input', () => { errorEl.style.display = 'none'; });
        }
        if (iocTypeSelect) {
            iocTypeSelect.addEventListener('change', () => {
                if (iocValueInput && iocValueInput.value.trim()) {
                    const result = validateIocValue(iocTypeSelect.value, iocValueInput.value.trim());
                    if (!result.ok) {
                        errorEl.textContent = result.message;
                        errorEl.style.display = 'block';
                    } else {
                        errorEl.style.display = 'none';
                    }
                }
            });
        }
    }

    // ── Filter / Search ───────────────────────────────────────────────────

    function applyFilters() {
        const term = searchInput ? searchInput.value.toLowerCase() : '';
        const type = typeFilter  ? typeFilter.value : '';
        document.querySelectorAll('.ioc-row').forEach(row => {
            const valueCell = row.querySelector('td.ioc-value-cell');
            // Search both raw and defanged text
            const rawValue  = (valueCell?.dataset.raw  || '').toLowerCase();
            const dispValue = (valueCell?.textContent   || '').toLowerCase();
            const desc      = (row.querySelector('td:nth-child(4)')?.textContent || '').toLowerCase();
            const rowType   = row.dataset.iocType || '';

            const matchSearch = !term || rawValue.includes(term) || dispValue.includes(term) || desc.includes(term);
            const matchType   = !type  || rowType === type;
            row.style.display = matchSearch && matchType ? '' : 'none';
        });
    }

    if (searchInput) searchInput.addEventListener('input', applyFilters);
    if (typeFilter)  typeFilter.addEventListener('change', applyFilters);

    // ── Inline delete confirmation ─────────────────────────────────────────

    function resetDeleteCell(cell) {
        const btn     = cell.querySelector('.delete-ioc-trigger');
        const confirm = cell.querySelector('.ioc-delete-confirm');
        if (btn)     btn.style.display = '';
        if (confirm) confirm.style.display = 'none';
    }

    document.querySelectorAll('.delete-ioc-trigger').forEach(button => {
        button.addEventListener('click', function (e) {
            e.stopPropagation();
            const cell    = button.closest('.ioc-delete-cell');
            const confirm = cell.querySelector('.ioc-delete-confirm');
            button.style.display = 'none';
            confirm.style.display = 'flex';
        });
    });

    document.querySelectorAll('.ioc-confirm-no').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            resetDeleteCell(btn.closest('.ioc-delete-cell'));
        });
    });

    document.querySelectorAll('.ioc-confirm-yes').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            const cell  = btn.closest('.ioc-delete-cell');
            const row   = btn.closest('tr');
            const iocId = row.dataset.iocId;
            const incidentId = document.querySelector('[incident-id]').getAttribute('incident-id');

            fetch(`/api/incident/${incidentId}/delete-ioc/`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
                body: JSON.stringify({ ioc_id: iocId })
            })
            .then(r => {
                if (r.ok) return r.json();
                throw new Error('Failed to delete IoC');
            })
            .then(() => row.remove())
            .catch(err => {
                console.error('Error:', err);
                resetDeleteCell(cell);
            });
        });
    });

    // ── Edit modal ─────────────────────────────────────────────────────────

    document.querySelectorAll('.ioc-row').forEach(item => {
        item.addEventListener('click', function (event) {
            if (event.target.closest('.ioc-delete-cell')) return;
            if (event.target.closest('.ioc-copy-raw')) return;
            const iocId = this.dataset.iocId;
            const incidentId = document.querySelector('[incident-id]').getAttribute('incident-id');
            currentIoCId = iocId;

            fetch(`/api/incident/${incidentId}/get-ioc/${iocId}/`)
                .then(r => r.json())
                .then(data => {
                    if (data.status !== 'success') return;
                    const ioc = data.data;
                    modalType.value        = ioc.type;
                    modalValue.value       = ioc.value; // always raw value in edit modal
                    modalStatus.value      = ioc.status;
                    modalDescription.value = ioc.description;
                    modalCreatedBy.textContent = ioc.created_by;
                    modalCreatedAt.textContent = ioc.created_at;

                    modalActions.innerHTML = '';
                    ioc.actions.forEach(action => {
                        const el = document.createElement('div');
                        el.className = 'action';
                        el.innerHTML = `<span>${action.created_at} — ${action.title}</span>`;
                        modalActions.appendChild(el);
                    });

                    modalEdit.style.display = 'flex';
                })
                .catch(err => console.error('Error fetching IoC:', err));
        });
    });

    // ── Auto-open from ?open=<iocId> (e.g. redirect from timeline) ───────────

    const openParam = new URLSearchParams(window.location.search).get('open');
    if (openParam) {
        // Clean URL immediately (no reload)
        history.replaceState(null, '', window.location.pathname);
        // Simulate a row click to open the edit modal
        const row = document.querySelector(`.ioc-row[data-ioc-id="${openParam}"]`);
        if (row) row.click();
    }

    // ── Reputation modal ───────────────────────────────────────────────────

    const repModal     = document.getElementById('repModal');
    const repModalBody = document.getElementById('repModalBody');

    if (repModal) {
        document.querySelectorAll('.rep-modal-close').forEach(btn => {
            btn.addEventListener('click', () => { repModal.style.display = 'none'; });
        });
        window.addEventListener('click', e => {
            if (e.target === repModal) repModal.style.display = 'none';
        });
    }

    function _repColor(n, threshWarn, threshBad) {
        if (n >= threshBad) return 'rep-bad';
        if (n >= threshWarn) return 'rep-warn';
        return 'rep-ok';
    }

    function renderRepModal(ioc) {
        if (!repModal || !repModalBody) return;
        const rep = ioc.reputation;
        if (!rep) {
            repModalBody.innerHTML = '<p class="rep-loading">No reputation data available yet. It may still be loading.</p>';
            repModal.style.display = 'flex';
            return;
        }

        const statusLabels = { clean: 'Clean', suspicious: 'Suspicious', malicious: 'Malicious', unknown: 'Unknown' };
        const statusClass  = { clean: 'rep-badge-clean', suspicious: 'rep-badge-suspicious', malicious: 'rep-badge-malicious', unknown: 'rep-badge-unknown' };
        const statusIcons  = { clean: 'fa-circle-check', suspicious: 'fa-triangle-exclamation', malicious: 'fa-skull-crossbones', unknown: 'fa-circle-question' };

        const checkedAt = rep.checked_at ? new Date(rep.checked_at).toLocaleString() : '';
        let html = `
            <div class="rep-status-row">
                <span class="rep-badge ${statusClass[rep.status] || 'rep-badge-unknown'} rep-status-label">
                    <i class="fa-solid ${statusIcons[rep.status] || 'fa-circle-question'}"></i>
                    ${statusLabels[rep.status] || 'Unknown'}
                </span>
                ${checkedAt ? `<span class="rep-checked-at">Checked: ${checkedAt}</span>` : ''}
            </div>`;

        if (rep.vt) {
            const vt = rep.vt;
            const mal = vt.malicious || 0;
            const sus = vt.suspicious || 0;
            const total = vt.total || 0;
            html += `<div class="rep-section">
                <p class="rep-section-title"><i class="fa-solid fa-virus"></i> VirusTotal</p>
                <div class="rep-grid">
                    <div class="rep-kv"><span class="rep-kv-label">Malicious</span><span class="rep-kv-value ${_repColor(mal, 1, 6)}">${mal}</span></div>
                    <div class="rep-kv"><span class="rep-kv-label">Suspicious</span><span class="rep-kv-value ${_repColor(sus, 1, 6)}">${sus}</span></div>
                    <div class="rep-kv"><span class="rep-kv-label">Harmless</span><span class="rep-kv-value rep-ok">${vt.harmless || 0}</span></div>
                    <div class="rep-kv"><span class="rep-kv-label">Undetected</span><span class="rep-kv-value">${vt.undetected || 0}</span></div>
                    <div class="rep-kv"><span class="rep-kv-label">Total engines</span><span class="rep-kv-value">${total}</span></div>
                    ${vt.country   ? `<div class="rep-kv"><span class="rep-kv-label">Country</span><span class="rep-kv-value">${vt.country}</span></div>` : ''}
                    ${vt.asn       ? `<div class="rep-kv"><span class="rep-kv-label">ASN</span><span class="rep-kv-value">${vt.asn}</span></div>` : ''}
                    ${vt.as_owner  ? `<div class="rep-kv"><span class="rep-kv-label">AS Owner</span><span class="rep-kv-value">${vt.as_owner}</span></div>` : ''}
                    ${vt.meaningful_name  ? `<div class="rep-kv"><span class="rep-kv-label">File name</span><span class="rep-kv-value">${vt.meaningful_name}</span></div>` : ''}
                    ${vt.type_description ? `<div class="rep-kv"><span class="rep-kv-label">File type</span><span class="rep-kv-value">${vt.type_description}</span></div>` : ''}
                </div>
            </div>`;
        }

        if (rep.abuseipdb) {
            const ab = rep.abuseipdb;
            const score = ab.score || 0;
            html += `<div class="rep-section">
                <p class="rep-section-title"><i class="fa-solid fa-shield-halved"></i> AbuseIPDB</p>
                <div class="rep-grid">
                    <div class="rep-kv"><span class="rep-kv-label">Abuse Score</span><span class="rep-kv-value ${_repColor(score, 10, 50)}">${score}%</span></div>
                    <div class="rep-kv"><span class="rep-kv-label">Reports</span><span class="rep-kv-value ${_repColor(ab.reports||0, 1, 5)}">${ab.reports || 0}</span></div>
                    ${ab.country      ? `<div class="rep-kv"><span class="rep-kv-label">Country</span><span class="rep-kv-value">${ab.country}</span></div>` : ''}
                    ${ab.isp          ? `<div class="rep-kv"><span class="rep-kv-label">ISP</span><span class="rep-kv-value">${ab.isp}</span></div>` : ''}
                    ${ab.domain       ? `<div class="rep-kv"><span class="rep-kv-label">Domain</span><span class="rep-kv-value">${ab.domain}</span></div>` : ''}
                    ${ab.last_reported ? `<div class="rep-kv"><span class="rep-kv-label">Last report</span><span class="rep-kv-value">${new Date(ab.last_reported).toLocaleDateString()}</span></div>` : ''}
                </div>
            </div>`;
        }

        repModalBody.innerHTML = html;
        repModal.style.display = 'flex';
    }

    document.querySelectorAll('.rep-badge:not(.rep-badge-pending)').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            const iocId = this.dataset.iocId;
            const incidentId = document.querySelector('[incident-id]').getAttribute('incident-id');
            repModalBody.innerHTML = '<p class="rep-loading">Loading…</p>';
            repModal.style.display = 'flex';

            fetch(`/api/incident/${incidentId}/get-ioc/${iocId}/`)
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'success') renderRepModal(data.data);
                })
                .catch(() => {
                    repModalBody.innerHTML = '<p class="rep-loading">Failed to load reputation data.</p>';
                });
        });
    });

    // ── Save edit ──────────────────────────────────────────────────────────

    if (saveEditButton) {
        saveEditButton.addEventListener('click', function () {
            const incidentId = document.querySelector('[incident-id]').getAttribute('incident-id');
            fetch(`/api/incident/${incidentId}/update-ioc/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ioc_id:      currentIoCId,
                    type:        modalType.value,
                    value:       modalValue.value,
                    status:      modalStatus.value,
                    description: modalDescription.value,
                }),
            })
            .then(r => r.ok ? r.json() : Promise.reject('Failed to update IoC'))
            .then(data => {
                if (data.status === 'success') {
                    modalEdit.style.display = 'none';
                    // Reload page to reflect updated value + defanging
                    location.reload();
                } else {
                    alert('Failed to update the IoC.');
                }
            })
            .catch(err => {
                console.error('Error:', err);
                alert('An error occurred while updating the IoC.');
            });
        });
    }
});
