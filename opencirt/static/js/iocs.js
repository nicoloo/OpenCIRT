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
    // Logic lives in defang.js (loaded before this script) so the IOC page and
    // the timeline page share one implementation. Fall back to a no-op if it
    // somehow failed to load.
    const defang = (window.IocDefang && window.IocDefang.defang)
        ? window.IocDefang.defang
        : function () { return null; };

    // ── Copy helper ───────────────────────────────────────────────────────

    function makeCopyBtn(valueToCopy, label) {
        const btn = document.createElement('button');
        btn.className = 'ioc-copy-raw';
        btn.title = label || 'Copy';
        btn.innerHTML = '<i class="fa-regular fa-copy"></i>';
        btn.addEventListener('click', e => {
            e.stopPropagation();
            navigator.clipboard.writeText(valueToCopy).then(() => {
                btn.innerHTML = '<i class="fa-solid fa-check"></i>';
                btn.classList.add('copied');
                setTimeout(() => {
                    btn.innerHTML = '<i class="fa-regular fa-copy"></i>';
                    btn.classList.remove('copied');
                }, 1500);
            });
        });
        return btn;
    }

    // Apply defanging AND copy button to all value cells
    document.querySelectorAll('.ioc-value-cell').forEach(cell => {
        const raw      = cell.dataset.raw  || '';
        const type     = cell.dataset.type || '';
        const defanged = defang(type, raw);
        // What gets copied: the defanged form when it exists, raw otherwise
        const copyValue = defanged || raw;

        cell.innerHTML = '';

        const wrap = document.createElement('span');

        if (defanged) {
            // Defanged display
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
        } else {
            // Plain display
            wrap.className = 'ioc-raw-wrap';

            const span = document.createElement('span');
            span.className = 'ioc-raw-text';
            span.textContent = raw;
            span.title = raw;
            wrap.appendChild(span);
        }

        wrap.appendChild(makeCopyBtn(copyValue, defanged ? 'Copy defanged value' : 'Copy value'));
        cell.appendChild(wrap);

        // Clicking anywhere on the value cell also copies
        cell.style.cursor = 'copy';
        cell.addEventListener('click', e => {
            e.stopPropagation();
            navigator.clipboard.writeText(copyValue).then(() => {
                const prev = cell.title;
                cell.title = 'Copied!';
                const orig = cell.style.opacity;
                cell.style.opacity = '0.6';
                setTimeout(() => { cell.title = prev; cell.style.opacity = orig; }, 800);
            });
        });
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
            case 'DOMAIN': {
                if (!/^([a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$/i.test(value))
                    return { ok: false, message: 'Invalid domain. Expected: sub.example.com' };
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
            if (event.target.closest('.rep-cell')) return;
            if (event.target.closest('.ioc-value-cell')) return;
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

    // ── Floating tooltip (body-level — immune to table overflow clipping) ───

    const _tipEl = document.createElement('div');
    _tipEl.className = 'rep-float-tip';
    document.body.appendChild(_tipEl);

    function _showTip(el) {
        const text = el.dataset.tip;
        if (!text) return;
        _tipEl.textContent = text;
        _tipEl.style.display = 'block';
        const r  = el.getBoundingClientRect();
        const tw = _tipEl.offsetWidth;
        const th = _tipEl.offsetHeight;
        // Prefer above, flip to below if not enough room
        let top  = r.top - th - 8;
        if (top < 6) top = r.bottom + 6;
        let left = r.left + r.width / 2 - tw / 2;
        left = Math.max(6, Math.min(left, window.innerWidth - tw - 6));
        _tipEl.style.top  = top  + 'px';
        _tipEl.style.left = left + 'px';
    }

    function _hideTip() { _tipEl.style.display = 'none'; }

    document.addEventListener('mouseover', e => {
        const el = e.target.closest('[data-tip]');
        if (el) _showTip(el);
    });
    document.addEventListener('mouseout', e => {
        if (e.target.closest('[data-tip]')) _hideTip();
    });

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
                ${vt.link ? `<a href="${vt.link}" target="_blank" rel="noopener noreferrer" class="rep-vt-link">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i> View full report on VirusTotal
                </a>` : ''}
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

    // ── Check All (rate-limited: VT free tier = 4 req/min → 1 per 15 s) ────
    //    Click again while running to cancel.

    let _checkAllRunning = false;
    let _checkAllStop    = false;

    const checkAllBtn = document.getElementById('checkAllBtn');
    if (checkAllBtn) {
        checkAllBtn.addEventListener('click', async () => {
            // Second click while running → request cancellation
            if (_checkAllRunning) {
                _checkAllStop = true;
                checkAllBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Stopping…';
                return;
            }

            const buttons = Array.from(document.querySelectorAll('.rep-cell .rep-check-btn'));
            if (!buttons.length) return;

            _checkAllRunning = true;
            _checkAllStop    = false;
            const total   = buttons.length;
            const WAIT_MS = 15000; // VT free: 4 lookups / min

            for (let i = 0; i < total; i++) {
                if (_checkAllStop) break;

                checkAllBtn.innerHTML =
                    `<i class="fa-solid fa-spinner fa-spin"></i> ${i + 1}/${total} · click to stop`;

                await doRepCheck(buttons[i]);

                // No wait after the last check, or if cancelled
                if (_checkAllStop || i === total - 1) break;

                // Live countdown so the user knows how long to wait
                const deadline = Date.now() + WAIT_MS;
                while (Date.now() < deadline) {
                    if (_checkAllStop) break;
                    const secsLeft  = Math.ceil((deadline - Date.now()) / 1000);
                    const secsTotal = (total - i - 1) * (WAIT_MS / 1000) + secsLeft;
                    const eta = secsTotal >= 60
                        ? `~${Math.ceil(secsTotal / 60)} min`
                        : `~${Math.ceil(secsTotal)} s`;
                    checkAllBtn.innerHTML =
                        `<i class="fa-solid fa-hourglass-half"></i> ` +
                        `${i + 1}/${total} · next in ${secsLeft}s · ${eta} left · click to stop`;
                    await new Promise(r => setTimeout(r, 1000));
                }
            }

            _checkAllRunning = false;
            _checkAllStop    = false;
            checkAllBtn.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Run Threat Intel on all IoCs';
        });
    }

    // ── Auto-check newly added IoC (?check_new=<id>) ──────────────────────

    const checkNewId = new URLSearchParams(window.location.search).get('check_new');
    if (checkNewId) {
        history.replaceState(null, '', window.location.pathname);
        // Wait one tick for rep-cell listeners to be attached, then check
        setTimeout(() => {
            const row = document.querySelector(`.ioc-row[data-ioc-id="${checkNewId}"]`);
            if (row) {
                const btn = row.querySelector('.rep-check-btn');
                if (btn) doRepCheck(btn);
            }
        }, 100);
    }

    // ── Reputation check / refresh ────────────────────────────────────────

    const VERDICT_CFG = {
        clean:      { cls: 'rep-badge-clean',      icon: 'fa-circle-check',         label: 'Clean' },
        suspicious: { cls: 'rep-badge-suspicious', icon: 'fa-triangle-exclamation', label: 'Suspicious' },
        malicious:  { cls: 'rep-badge-malicious',  icon: 'fa-skull-crossbones',     label: 'Malicious' },
        unknown:    { cls: 'rep-badge-unknown',     icon: 'fa-circle-question',      label: 'Unknown' },
    };

    function repBadgeHtml(rep, iocId) {
        const cfg = VERDICT_CFG[rep.status] || VERDICT_CFG.unknown;
        return `<span class="rep-badge ${cfg.cls}" data-ioc-id="${iocId}">` +
               `<i class="fa-solid ${cfg.icon}"></i><span class="rep-label"> ${cfg.label}</span></span>` +
               `<button class="rep-check-btn rep-refresh-btn" data-ioc-id="${iocId}" title="Refresh reputation" style="margin-left:4px;">` +
               `<i class="fa-solid fa-arrows-rotate"></i></button>`;
    }

    async function doRepCheck(btn) {
        const iocId      = btn.dataset.iocId;
        const incidentId = document.querySelector('[incident-id]').getAttribute('incident-id');
        const cell       = btn.closest('.rep-cell');

        // Show loading state immediately
        btn.disabled  = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Checking…';

        try {
            const r    = await fetch(`/api/incident/${incidentId}/ioc/${iocId}/reputation/`);
            const data = await r.json();

            if (r.ok && data.status === 'ok' && cell) {
                cell.innerHTML = repBadgeHtml(data.reputation, iocId);
                attachRepListeners(cell);
            } else {
                const msg = (data && data.error) ? data.error : `HTTP ${r.status}`;
                if (cell) {
                    cell.innerHTML =
                        `<span class="rep-badge rep-badge-unknown" style="gap:5px;">` +
                        `<i class="fa-solid fa-circle-exclamation"></i> ${msg}</span>` +
                        `<button class="rep-check-btn rep-refresh-btn" data-ioc-id="${iocId}" title="Retry" style="margin-left:4px;">` +
                        `<i class="fa-solid fa-arrows-rotate"></i></button>`;
                    attachRepListeners(cell);
                }
            }
        } catch (err) {
            console.error('[RepCheck] fetch error:', err);
            if (cell) {
                btn.disabled  = false;
                btn.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Check';
            }
        }
    }

    function attachRepListeners(cell) {
        cell.querySelectorAll('.rep-check-btn').forEach(b => {
            b.addEventListener('click', e => { e.stopPropagation(); doRepCheck(b); });
        });
        cell.querySelectorAll('.rep-badge[data-ioc-id]').forEach(b => {
            b.addEventListener('click', e => { e.stopPropagation(); openRepModal(b.dataset.iocId); });
        });
    }

    async function openRepModal(iocId) {
        const incidentId = document.querySelector('[incident-id]').getAttribute('incident-id');
        if (!repModal || !repModalBody) return;
        repModalBody.innerHTML = '<p class="rep-loading">Loading…</p>';
        repModal.style.display = 'flex';
        try {
            const r    = await fetch(`/api/incident/${incidentId}/get-ioc/${iocId}/`);
            const data = await r.json();
            if (data.status === 'success') renderRepModal(data.data);
        } catch {
            repModalBody.innerHTML = '<p class="rep-loading">Failed to load reputation data.</p>';
        }
    }

    // Attach reputation listeners on initial page load
    document.querySelectorAll('.rep-cell').forEach(cell => {
        attachRepListeners(cell);
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
