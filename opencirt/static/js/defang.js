// Shared IOC defanging — single source of truth for the IOC (evidence) page,
// the timeline page and any other view that displays IOC values.
//
// Exposes window.IocDefang.defang(type, value) and auto-defangs timeline chips.
(function (global) {
    'use strict';

    const URL_RE  = /^[a-z][a-z0-9+.\-]*:\/\//i;            // any scheme://  (http, https, ftp, tcp, smb, …)
    const IPV4_RE = /^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$/;
    const DOT     = /\./g;

    function defangUrl(v) {
        return v
            .replace(/^https:\/\//i, 'hxxps[:]//')
            .replace(/^http:\/\//i,  'hxxp[:]//')
            .replace(/^ftp:\/\//i,   'fxp[:]//')
            .replace(/:\/\//,        '[://]')               // any other scheme (tcp://, smb://…)
            .replace(DOT,            '[.]');
    }

    function defangEmail(v) {
        const at = v.indexOf('@');
        if (at === -1) return v.replace(DOT, '[.]');
        return v.slice(0, at) + '[@]' + v.slice(at + 1).replace(DOT, '[.]');
    }

    // Normalise type aliases that show up in fixtures / imported data so a
    // mis-typed indicator (e.g. "IPV4" instead of "IPADRESS") still defangs.
    function normType(type) {
        const t = (type || '').toUpperCase().trim();
        if (t === 'IPV4' || t === 'IPV6' || t === 'IP') return 'IPADRESS';
        return t;
    }

    function defang(type, value) {
        if (!value) return null;
        const v = value.trim();
        const t = normType(type);

        if (t === 'URL')      return defangUrl(v);
        if (t === 'IPADRESS') return v.replace(DOT, '[.]');
        if (t === 'EMAIL')    return defangEmail(v);
        if (t === 'DOMAIN' || t === 'NETWORK')
            return URL_RE.test(v) ? defangUrl(v) : v.replace(DOT, '[.]');

        // Content-based fallback: a network indicator filed under the wrong type
        // (filenames / hashes / accounts won't match any of these).
        if (URL_RE.test(v))                       return defangUrl(v);
        if (IPV4_RE.test(v))                      return v.replace(DOT, '[.]');
        if (v.includes('@') && v.includes('.'))   return defangEmail(v);

        return null; // nothing to defang
    }

    global.IocDefang = { defang, defangUrl, normType };

    // ── Auto-apply to timeline IOC chips (server-rendered) ──────────────────
    function truncate(s, n) { return s.length > n ? s.slice(0, n) + '…' : s; }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.tl-ioc-chip').forEach(function (chip) {
            const valEl = chip.querySelector('.tl-ioc-value');
            if (!valEl) return;
            const type  = chip.dataset.iocType  || '';
            const raw   = chip.dataset.iocValue || valEl.textContent || '';
            const shown = defang(type, raw) || raw;
            valEl.textContent = truncate(shown, 30);
            const label = chip.dataset.iocTypeLabel || type;
            chip.title = label ? label + ': ' + shown : shown;
        });
    });
})(window);
