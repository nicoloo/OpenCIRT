"""
Threat intelligence lookups for IoCs.
Supported: VirusTotal v3 (IP, hash, URL, domain) + AbuseIPDB (IP).
Keys come from env vars: VIRUSTOTAL_API_KEY, ABUSEIPDB_API_KEY.
"""
import os
import base64
import logging
import threading

logger = logging.getLogger(__name__)

ELIGIBLE_TYPES = {'IPADRESS', 'HASH', 'URL', 'EMAIL'}


def _vt_key():
    return os.environ.get('VIRUSTOTAL_API_KEY', '')


def _abuse_key():
    return os.environ.get('ABUSEIPDB_API_KEY', '')


def _vt_get(path):
    key = _vt_key()
    if not key:
        return None
    try:
        import requests
        r = requests.get(
            f'https://www.virustotal.com/api/v3{path}',
            headers={'x-apikey': key},
            timeout=15,
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.debug('VT request failed: %s', e)
    return None


def _parse_stats(attrs):
    stats = attrs.get('last_analysis_stats', {})
    return {
        'malicious':  stats.get('malicious', 0),
        'suspicious': stats.get('suspicious', 0),
        'undetected': stats.get('undetected', 0),
        'harmless':   stats.get('harmless', 0),
        'total':      sum(stats.values()),
    }


def _vt_ip(ip):
    data = _vt_get(f'/ip_addresses/{ip}')
    if not data:
        return None
    attrs = data.get('data', {}).get('attributes', {})
    result = _parse_stats(attrs)
    result.update({
        'country':  attrs.get('country', ''),
        'asn':      attrs.get('asn', ''),
        'as_owner': attrs.get('as_owner', ''),
    })
    return result


def _vt_hash(file_hash):
    data = _vt_get(f'/files/{file_hash}')
    if not data:
        return None
    attrs = data.get('data', {}).get('attributes', {})
    result = _parse_stats(attrs)
    result.update({
        'meaningful_name':  attrs.get('meaningful_name', ''),
        'type_description': attrs.get('type_description', ''),
    })
    return result


def _vt_url(url_value):
    url_id = base64.urlsafe_b64encode(url_value.encode()).decode().rstrip('=')
    data = _vt_get(f'/urls/{url_id}')
    if not data:
        return None
    attrs = data.get('data', {}).get('attributes', {})
    return _parse_stats(attrs)


def _vt_domain(domain):
    data = _vt_get(f'/domains/{domain}')
    if not data:
        return None
    attrs = data.get('data', {}).get('attributes', {})
    result = _parse_stats(attrs)
    result['reputation'] = attrs.get('reputation', 0)
    return result


def _abuseipdb(ip):
    key = _abuse_key()
    if not key:
        return None
    try:
        import requests
        r = requests.get(
            'https://api.abuseipdb.com/api/v2/check',
            headers={'Key': key, 'Accept': 'application/json'},
            params={'ipAddress': ip, 'maxAgeInDays': 90},
            timeout=15,
        )
        if r.status_code == 200:
            d = r.json().get('data', {})
            return {
                'score':         d.get('abuseConfidenceScore', 0),
                'country':       d.get('countryCode', ''),
                'reports':       d.get('totalReports', 0),
                'last_reported': d.get('lastReportedAt', '') or '',
                'isp':           d.get('isp', ''),
                'domain':        d.get('domain', ''),
            }
    except Exception as e:
        logger.debug('AbuseIPDB request failed: %s', e)
    return None


def _compute_status(vt, abuse):
    score = 0
    if vt:
        score += vt.get('malicious', 0) + vt.get('suspicious', 0)
    if abuse:
        s = abuse.get('score', 0)
        if s >= 50:
            score += 3
        elif s >= 10:
            score += 1
    if score == 0:
        return 'clean'
    if score <= 5:
        return 'suspicious'
    return 'malicious'


def run_lookup(ioc_id):
    """Perform the lookup and persist result. Runs in a background thread."""
    from django.utils import timezone

    if not _vt_key() and not _abuse_key():
        return

    try:
        from opencirt.models import GenericIoc
        ioc = GenericIoc.objects.get(pk=ioc_id)
    except Exception:
        return

    t = ioc.type
    v = ioc.value.strip()

    vt_data    = None
    abuse_data = None

    if t == 'IPADRESS':
        if _vt_key():
            vt_data = _vt_ip(v)
        if _abuse_key():
            abuse_data = _abuseipdb(v)
    elif t == 'HASH':
        if _vt_key():
            vt_data = _vt_hash(v)
    elif t == 'URL':
        if _vt_key():
            vt_data = _vt_url(v)
    elif t == 'EMAIL':
        if _vt_key() and '@' in v:
            domain = v.split('@', 1)[1]
            vt_data = _vt_domain(domain)
    else:
        return

    if vt_data is None and abuse_data is None:
        return

    status = _compute_status(vt_data, abuse_data)
    payload = {'status': status, 'checked_at': timezone.now().isoformat()}
    if vt_data:
        payload['vt'] = vt_data
    if abuse_data:
        payload['abuseipdb'] = abuse_data

    try:
        GenericIoc.objects.filter(pk=ioc_id).update(reputation=payload)
    except Exception as e:
        logger.debug('Failed to persist reputation: %s', e)


def schedule_lookup(ioc_id):
    """Kick off a daemon thread to perform the threat intel lookup."""
    threading.Thread(target=run_lookup, args=(ioc_id,), daemon=True).start()
