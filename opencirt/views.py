from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.contrib.auth import login, logout, authenticate
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required
from opencirt.models import Incident, Note, User, Message, GenericIoc, UserRole, Task, Action, Impact, SharedFile, AuditLog, PlatformSettings, CtiProvider
from . import models
from .utils import verify_permissions, user_is_incident_responder_orpublic, user_is_incident_responder, update_first_actions, get_incidents_by_day_and_severity
from .threat_intel import schedule_lookup, ELIGIBLE_TYPES as THREAT_INTEL_ELIGIBLE_TYPES
from django.contrib import messages
import json
import os
import re
import random
from datetime import timedelta, datetime
from django.utils import timezone
from .models import Incident
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
import os
from collections import Counter, defaultdict
from .report_generators import (
    parse_sections, parse_tlp, TLP_STYLES,
    DEFAULT_SECTIONS, ALL_SECTIONS,
    generate_markdown, generate_deep_json,
)
import csv
from io import StringIO
from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor

# ── Audit log helpers ─────────────────────────────────────────────────────────

def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')

def _audit(incident, request, action, object_type, description):
    """Create an AuditLog entry. Never raises — logs silently on error."""
    try:
        AuditLog.objects.create(
            incident=incident,
            user=request.user if request.user.is_authenticated else None,
            ip_address=_get_client_ip(request),
            action=action,
            object_type=object_type,
            description=description,
        )
    except Exception:
        pass

# TLP → python-docx RGBColor mapping (used by download_incident_word)
TLP_COLORS = {
    'WHITE': RGBColor(80, 80, 80),
    'GREEN': RGBColor(40, 167, 69),
    'AMBER': RGBColor(253, 126, 20),
    'RED':   RGBColor(220, 53, 69),
}

@login_required(login_url='login')
def home(request):
    # Get incidents where the user has a role OR the incident is public
    user_roles = UserRole.objects.filter(user=request.user).select_related('incident')
    
    user_incidents = Incident.objects.filter(
        id__in=[user_role.incident.id for user_role in user_roles]
    )
    public_incidents = Incident.objects.filter(is_public=True)
    # Combine both sets of incidents

    # Average KPI don't take into account the public incidents

    total_time_to_detect, total_time_to_respond, total_duration, total_genericiocs, incident_count = 0, 0, 0, 0, 0

    # Accumulate values for each incident, converting timedelta to seconds for simplicity
    for incident in user_incidents:
        if incident.time_to_detect:
            total_time_to_detect += incident.time_to_detect.total_seconds()
        if incident.time_to_respond:
            total_time_to_respond += incident.time_to_respond.total_seconds()
        if incident.duration:
            total_duration += incident.duration.total_seconds()
        total_genericiocs += incident.genericiocs.count()
        incident_count += 1

    # Calculate averages (avoid division by zero)
    kpis = [
        {'label': "Time to detect (TTD)",'value': timedelta(seconds=total_time_to_detect / incident_count) if incident_count else timedelta()},
        {'label': "Time to respond (TTR)",'value': timedelta(seconds=total_time_to_respond / incident_count) if incident_count else timedelta()},
        {'label': "Duration",'value': timedelta(seconds=total_duration / incident_count) if incident_count else timedelta()},
        {'label': 'Iocs found', 'value': total_genericiocs},
    ]


    incidents = (user_incidents | public_incidents).order_by('-created_at')


    
    # Prepare graphs data
    # Pie chart
    piechart_data = {
        'labels': list(Counter(incident.status for incident in incidents).keys()),
        'values': list(Counter(incident.status for incident in incidents).values()),
    }   
    # Get sorted unique dates
    timechart_data = get_incidents_by_day_and_severity()

    # Extract sorted dates
    dates = sorted(timechart_data.keys())

    # Extract unique severities
    severities = set()
    for sev_data in timechart_data.values():
        severities.update(sev_data.keys())
    severities = sorted(severities)  # Sort to maintain order

    # Prepare data for Chart.js
    severity_data = {sev: [timechart_data[date].get(sev, 0) for date in dates] for sev in severities}

    # Prepare dataset for Chart.js
    datasets = []
    for severity in severities:
        datasets.append({
            "label": severity,
            "data": severity_data[severity],
            # "borderColor": severity_colors.get(severity, "gray"),
        })

    context = {
        "labels": dates,
        "datasets": datasets
    }

    # Stats bar
    incidents_list = list(incidents)
    total_count = len(incidents_list)
    active_count = sum(1 for inc in incidents_list if inc.status in ('OPEN', 'IN_PROGRESS'))
    critical_count = sum(1 for inc in incidents_list if inc.severity == 'CRITICAL')
    total_iocs = sum(inc.genericiocs.count() for inc in incidents_list)

    # Severity distribution donut
    severity_counter = Counter(inc.severity for inc in incidents_list)
    severity_chart_data = {
        'labels': list(severity_counter.keys()),
        'values': list(severity_counter.values()),
    }

    return render(request, 'home.html', {
        'incidents': incidents_list,
        'user': request.user,
        'status_counts': piechart_data,
        'timechart_data': context,
        'kpis': kpis,
        'total_count': total_count,
        'active_count': active_count,
        'critical_count': critical_count,
        'total_iocs': total_iocs,
        'severity_chart_data': severity_chart_data,
    })


def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '/home')
            # Guard against open-redirect: only allow same-host relative URLs
            if not url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                next_url = '/home'
            return redirect(next_url)
        return render(request, 'login.html', {'error': 'Invalid username or password'})
    return render(request, 'login.html')

def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def about(request):
    return render(request,'about.html', {'user': request.user})


@login_required(login_url='login')
def profile(request):
    try:
        current_user = request.user
    except:
        return JsonResponse({'error': 'La galere'}, status=404)
 
    prefs = request.user.preferences if request.user.preferences else {}
    return render(request, 'profile.html', {
        'user': request.user,
        'prefs': prefs,
    })

@login_required
def profile_change_password(request):
    if request.method == 'POST':
        pass
    #     form = PasswordChangeForm(user=request.user, data=request.POST)
    #     if form.is_valid():
    #         user = form.save()
    #         update_session_auth_hash(request, user)
    #         messages.success(request, 'Your password has been updated!')
    #         return redirect('my_profile')
    #     else:
    #         messages.error(request, 'Please correct the errors below.')
    # else:
    #     form = PasswordChangeForm(user=request.user)
    return render(request, 'profile.html', {'form': form})



@login_required(login_url='login')
@user_is_incident_responder_orpublic
def overview(request, id):
    incident = get_object_or_404(Incident, id=id)
    try:
        user_role = UserRole.objects.get(user=request.user, incident=incident)
    except UserRole.DoesNotExist:
        if incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")

    platform = PlatformSettings.get()
    return render(request, 'incidents/overview.html', {
        'incident':          incident,
        'user':              request.user,
        'current_user_role': user_role,
        'ai_configured':     platform.ai_provider != 'NONE' and bool(platform.ai_api_key),
    })

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def activity(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        user_role = UserRole.objects.get(user=request.user, incident=incident)
        incident_leads = User.objects.filter(id__in=UserRole.objects.filter(incident=incident, role="INCIDENT_LEAD").values_list('user_id', flat=True))
        
    except UserRole.DoesNotExist:
        if incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
            incident_leads = User.objects.filter(id__in=UserRole.objects.filter(incident=incident, role="INCIDENT_LEAD").values_list('user_id', flat=True))
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")
            
    except Incident.DoesNotExist:
        my_object = None
    return render(request,'incidents/activity.html', {'incident': incident, 'user': request.user,'current_user_role': user_role, 'incident_leads': incident_leads})

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def impacts(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        user_role = UserRole.objects.get(user=request.user, incident=incident)
        incident_leads = User.objects.filter(id__in=UserRole.objects.filter(incident=incident, role="INCIDENT_LEAD").values_list('user_id', flat=True))
        
    except UserRole.DoesNotExist:
        if incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
            incident_leads = User.objects.filter(id__in=UserRole.objects.filter(incident=incident, role="INCIDENT_LEAD").values_list('user_id', flat=True))
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")
            
    except Incident.DoesNotExist:
        my_object = None
    return render(request,'incidents/impacts.html', {'incident': incident, 'user': request.user,'current_user_role': user_role, 'incident_leads': incident_leads})

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def notes(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        user_role = UserRole.objects.get(user=request.user, incident=incident)

    except UserRole.DoesNotExist:
        if incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")
    except Incident.DoesNotExist:
        my_object = None
    shared_files = list(incident.shared_files.all().order_by('-created_at'))
    for sf in shared_files:
        sf.is_executable = _get_extension(sf.original_name) in _EXECUTABLE_EXTENSIONS
    return render(request, 'incidents/notes.html', {
        'incident':     incident,
        'user':         request.user,
        'current_user_role': user_role,
        'shared_files': shared_files,
    })

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def tasks(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        user_role = UserRole.objects.get(user=request.user, incident=incident)
    except UserRole.DoesNotExist:
        if incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")
    except Incident.DoesNotExist:
        my_object = None
    return render(request,'incidents/tasks.html', {'incident': incident, 'user': request.user, 'current_user_role': user_role})

@login_required(login_url='login')
@user_is_incident_responder
def add_note(request, id):

    try:
        if request.method == 'POST':
            incident = Incident.objects.get(pk=id)
            data = json.loads(request.body)
            name = data.get('name', 'My note')
            text = data.get('text', '')
            new_note = Note.objects.create(
            incident=incident,
            name=name,
            text=text,
            created_by = request.user
            )
            Message.objects.create(
                incident=incident,
                sender=request.user,
                text=f"{request.user.username} created note: {new_note.name}",
                is_bot=True,
                link=f"/incident/{incident.id}/notes"
            )
            _audit(incident, request, 'CREATE', 'Note', f'Created note "{new_note.name}"')
            return JsonResponse({
            'id': new_note.id,
            'name': new_note.name,
            'text': new_note.text
            })

    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url='login')
@user_is_incident_responder
def update_note(request, id):
    if request.method == 'POST':
        try:
            
            data = json.loads(request.body)
            note_id = data.get('note_id')
            note = Note.objects.get(id=note_id)
            note.name = data.get('name', 'My note')
            note.text = data.get('text', '')
            
            note.save()
            _audit(Incident.objects.get(pk=id), request, 'UPDATE', 'Note', f'Updated note "{note.name}"')
            return JsonResponse({'status': 'success', 'note_id': note_id})

        except Note.DoesNotExist:
            return JsonResponse({'error': 'Note not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url='login')
@user_is_incident_responder
def delete_note(request, id):
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            note_id = data.get('note_id')
            note = Note.objects.get(pk=note_id)
            note_name = note.name
            note.delete()
            _audit(Incident.objects.get(pk=id), request, 'DELETE', 'Note', f'Deleted note "{note_name}"')
            return JsonResponse({"status": "success", "message": "Note deleted successfully", "note_id": note_id })
        except Note.DoesNotExist:
            return JsonResponse({'error': 'Note not found'}, status=404)        

# ── File upload security ──────────────────────────────────────────────────────
# Extensions that can be executed server-side (PHP, ASP, CGI, shell scripts…).
# These are NEVER accepted — an attacker could trigger server-side execution if
# the web server ever serves them directly.
_BLOCKED_EXTENSIONS = frozenset([
    # Web-side scripts
    'php', 'php3', 'php4', 'php5', 'php7', 'php8', 'phtml', 'phar',
    'asp', 'aspx', 'asa', 'asax', 'ascx', 'ashx', 'asmx',
    'jsp', 'jspx', 'jws', 'cgi',
    # Unix/Linux shells (could run via CGI or misconfigured handler)
    'sh', 'bash', 'zsh', 'fish', 'ksh', 'csh', 'tcsh',
    # Interpreted languages runnable server-side
    'py', 'pyc', 'pyo', 'rb', 'pl', 'lua', 'tcl',
    # Web-server config overrides
    'htaccess', 'htpasswd',
])

# Client-side executables / binaries — safe for the server to store, but may
# be malicious in content.  Uploads are accepted; downloads require confirmation.
_EXECUTABLE_EXTENSIONS = frozenset([
    # Windows executables & installers
    'exe', 'com', 'scr', 'pif', 'msi', 'msp', 'msc', 'cpl',
    # Windows scripting
    'bat', 'cmd', 'vbs', 'vbe', 'js', 'jse', 'ws', 'wsf', 'wsc', 'wsh',
    'ps1', 'psm1', 'psd1', 'ps1xml', 'lnk', 'url', 'hta',
    # Compiled binaries / libraries
    'dll', 'so', 'dylib', 'elf',
    # JVM bytecode / packages
    'jar', 'war', 'ear', 'class',
    # Mobile packages
    'apk', 'ipa', 'xap',
])

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def _sanitize_filename(name):
    """
    Return a safe filename:
    - Strip any path components (defence against path traversal)
    - Remove null bytes and control characters
    - Truncate to 255 characters
    - Fall back to 'file' if nothing is left
    """
    name = os.path.basename(name.replace('\\', '/'))          # strip path
    name = re.sub(r'[\x00-\x1f\x7f/<>:"|?*]', '_', name)     # remove control chars & OS-reserved chars
    name = name.strip('. ')                                    # no leading/trailing dots or spaces
    return name[:255] or 'file'


def _get_extension(name):
    """Return lowercase extension without leading dot, e.g. 'pdf'."""
    return os.path.splitext(name)[1].lstrip('.').lower()


# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
@user_is_incident_responder
def upload_file(request, id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    incident = get_object_or_404(Incident, pk=id)
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file provided'}, status=400)

    # Size check
    if f.size > _MAX_UPLOAD_BYTES:
        return JsonResponse({'error': 'File too large (max 50 MB)'}, status=400)

    # Sanitize the filename — never trust user input for paths
    safe_name = _sanitize_filename(f.name)
    ext = _get_extension(safe_name)

    # Block server-side-executable scripts (PHP, ASP, shell, etc.)
    if ext in _BLOCKED_EXTENSIONS:
        return JsonResponse(
            {'error': f'File type ".{ext}" cannot be uploaded — server-side scripts are not permitted.'},
            status=400
        )

    # Overwrite the in-memory name so Django's FileField stores it safely
    f.name = safe_name

    shared = SharedFile.objects.create(
        incident=incident,
        uploaded_by=request.user,
        file=f,
        original_name=safe_name,
        size=f.size,
    )
    _audit(incident, request, 'CREATE', 'File', f'Uploaded file "{safe_name}" ({f.size} bytes)')
    return JsonResponse({
        'status': 'success',
        'id': shared.id,
        'name': shared.original_name,
        'size': shared.size,
        'url': shared.file.url,
        'uploaded_by': request.user.username,
        'created_at': shared.created_at.strftime('%d %b %Y, %H:%M'),
    })


@login_required(login_url='login')
@user_is_incident_responder
def delete_file(request, id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        file_id = data.get('file_id')
        incident = get_object_or_404(Incident, pk=id)
        shared = get_object_or_404(SharedFile, pk=file_id, incident=incident)
        file_name = shared.original_name
        shared.file.delete(save=False)
        shared.delete()
        _audit(incident, request, 'DELETE', 'File', f'Deleted file "{file_name}"')
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required(login_url='login')
@user_is_incident_responder_orpublic
def responders(request, id):
    from django.shortcuts import redirect
    return redirect('incident_settings', id=id)

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def incident_settings(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        user_role = UserRole.objects.get(user=request.user, incident=incident)
    except UserRole.DoesNotExist:
        if incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")
    except Incident.DoesNotExist:
        return HttpResponseNotFound("Incident not found.")
    platform = PlatformSettings.get()
    return render(request, 'incidents/incident_settings.html', {
        'incident':         incident,
        'user':             request.user,
        'current_user_role': user_role,
        'ai_configured':    platform.ai_provider != 'NONE' and bool(platform.ai_api_key),
    })

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def report_preview(request, id):
    """
    GET /api/incident/<id>/report-preview/?sections=executive_summary,iocs&tlp=AMBER
    Returns HTML string for iframe srcdoc.
    """
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return HttpResponse('<p style="padding:20px;color:#dc2626;">Incident not found.</p>', status=404)

    sections = parse_sections(request.GET)
    tlp = parse_tlp(request.GET)
    tlp_style = TLP_STYLES[tlp]

    html = render_to_string('reports/report_template.html', {
        'incident': incident,
        'sections': sections,
        'tlp': tlp,
        'tlp_style': tlp_style,
        'is_pdf': False,
        'generated_at': timezone.now().strftime('%d %B %Y, %H:%M'),
        'generated_by': request.user.username,
    })
    return HttpResponse(html, content_type='text/html; charset=utf-8')


@login_required(login_url='login')
@user_is_incident_responder_orpublic
def report(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        user_role = UserRole.objects.get(user=request.user, incident=incident)
    except UserRole.DoesNotExist:
        if incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")
    except Incident.DoesNotExist:
        return HttpResponse("Incident not found.", status=404)

    return render(request, 'incidents/report.html', {
        'incident': incident,
        'user': request.user,
        'current_user_role': user_role,
        'all_sections': list(ALL_SECTIONS),
        'default_sections': list(DEFAULT_SECTIONS),
    })

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def iocs(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        user_role = UserRole.objects.get(user=request.user, incident=incident)
    except UserRole.DoesNotExist:
        if request.user.is_superuser:
            user_role = UserRole(user=request.user, incident=incident, role="INCIDENT_LEAD")
        elif incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")
    except Incident.DoesNotExist:
        my_object = None
    cti_configured      = CtiProvider.objects.filter(enabled=True).exclude(api_key='').exists()
    supported_ioc_types = _cti_supported_types()
    return render(request, 'incidents/evidence.html', {
        'incident':            incident,
        'user':                request.user,
        'current_user_role':   user_role,
        'cti_configured':      cti_configured,
        'supported_ioc_types': supported_ioc_types,
    })

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def timeline(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        user_role = UserRole.objects.get(user=request.user, incident=incident)
    except UserRole.DoesNotExist:
        if request.user.is_superuser:
            user_role = UserRole(user=request.user, incident=incident, role="INCIDENT_LEAD")
        elif incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")
    except Incident.DoesNotExist:
        my_object = None
    return render(request,'incidents/timeline.html', {'incident': incident, 'user': request.user, 'current_user_role': user_role})

def join(request, id):
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return redirect('/home')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()

        # Validate invite code
        if incident.invite_code and code != incident.invite_code:
            return render(request, 'incidents/join.html', {
                'incident': incident,
                'error': 'Invalid code. Please check with your incident lead.',
                'user': request.user,
            })

        if request.user.is_authenticated:
            # Already logged in — just add to incident
            if not UserRole.objects.filter(user=request.user, incident=incident).exists():
                UserRole.objects.create(
                    user=request.user,
                    incident=incident,
                    role='READER',
                    display_role='Responder'
                )
            return redirect('overview', id=incident.id)
        else:
            # Create a new account
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()

            if not username or not password:
                return render(request, 'incidents/join.html', {
                    'incident': incident,
                    'error': 'Username and password are required.',
                })
            if User.objects.filter(username=username).exists():
                return render(request, 'incidents/join.html', {
                    'incident': incident,
                    'error': 'Username already taken. Please choose another.',
                })
            user = User.objects.create_user(username=username, email=email, password=password)
            UserRole.objects.create(
                user=user,
                incident=incident,
                role='READER',
                display_role='Responder'
            )
            login(request, user)
            return redirect('overview', id=incident.id)

    return render(request, 'incidents/join.html', {
        'incident': incident,
        'user': request.user,
    })


def welcome(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        inviter_name = request.user.username if request.user.is_authenticated else "Someone"
        if request.method == 'POST':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')

            if User.objects.filter(username=username).exists():
                return render(request, 'incidents/join.html', {
                    'incident': incident,
                    'inviter_name': inviter_name,
                    'error': 'Username already exists'
                })

            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            user.save()
            # Add the user to the incident
            UserRole.objects.create(user=user, incident=incident, role="INCIDENT_VIEWER", display_role="Incident Viewer")
            # Log the user in
            login(request, user)          
            return redirect('overview', id=incident.id)
        else:
            return render(request, 'incidents/join.html', {'incident': incident, 'inviter_name': inviter_name})
    except Incident.DoesNotExist:
        my_object = None
        return render(request,'incidents/join.html', {'incident': incident})

# ─────────────────────────────────────────────────────
# INVITE HELPERS
# ─────────────────────────────────────────────────────

def generate_invite_code():
    return str(random.randint(100000, 999999))


# ─────────────────────────────────────────────────────
# CREATE INCIDENT
# ─────────────────────────────────────────────────────

@login_required(login_url='login')
def create_incident(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        severity = request.POST.get('severity', 'MEDIUM')
        starting_time_str = request.POST.get('starting_time', '')
        is_public = request.POST.get('is_public') == 'on'

        if not name:
            return render(request, 'incidents/create_incident.html', {
                'user': request.user,
                'error': 'Incident name is required.',
                'form_data': request.POST,
            })

        # Parse start time
        if starting_time_str:
            try:
                starting_time = datetime.strptime(starting_time_str, '%Y-%m-%dT%H:%M')
                starting_time = timezone.make_aware(starting_time)
            except ValueError:
                starting_time = timezone.now()
        else:
            starting_time = timezone.now()

        invite_code = generate_invite_code()

        incident = Incident.objects.create(
            name=name,
            description=description,
            severity=severity,
            status='OPEN',
            starting_time=starting_time,
            ending_time=starting_time,
            duration=timedelta(0),
            time_to_detect=timedelta(0),
            time_to_respond=timedelta(0),
            executive_summary='',
            lessons_learned='',
            technical_details='',
            is_public=is_public,
            created_by=request.user,
            invite_code=invite_code,
        )

        UserRole.objects.create(
            user=request.user,
            incident=incident,
            role='INCIDENT_LEAD',
            display_role='Incident Lead',
        )

        return redirect('incident_invite', id=incident.id)

    return render(request, 'incidents/create_incident.html', {'user': request.user})


# ─────────────────────────────────────────────────────
# POST-CREATION INVITE SCREEN
# ─────────────────────────────────────────────────────

@login_required(login_url='login')
def incident_invite(request, id):
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return redirect('/home')

    if not incident.invite_code:
        incident.invite_code = generate_invite_code()
        incident.save()

    join_url = request.build_absolute_uri(f'/incident/{id}/join')

    return render(request, 'incidents/invite.html', {
        'incident': incident,
        'user': request.user,
        'join_url': join_url,
    })


@login_required(login_url='login')
def regenerate_invite(request, id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        incident = Incident.objects.get(pk=id)
        try:
            user_role = UserRole.objects.get(user=request.user, incident=incident)
            if user_role.role not in ('INCIDENT_LEAD', 'RESPONDER'):
                return JsonResponse({'error': 'Permission denied'}, status=403)
        except UserRole.DoesNotExist:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        incident.invite_code = generate_invite_code()
        incident.save()
        return JsonResponse({'status': 'success', 'code': incident.invite_code})
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)


# ─────────────────────────────────────────────────────
# SETTINGS PAGE
# ─────────────────────────────────────────────────────

@login_required(login_url='login')
def settings_view(request):
    user = request.user
    prefs = user.preferences if user.preferences else {}

    if request.method == 'POST':
        prefs['default_severity'] = request.POST.get('default_severity', 'MEDIUM')
        prefs['chart_period'] = request.POST.get('chart_period', '30d')
        user.preferences = prefs
        user.save()
        return redirect('/settings?saved=1')

    platform      = PlatformSettings.get()
    cti_providers = CtiProvider.objects.all().order_by('name')
    return render(request, 'settings.html', {
        'user':          user,
        'prefs':         prefs,
        'platform':      platform,
        'cti_providers': cti_providers,
    })


@login_required(login_url='login')
@user_is_incident_responder_orpublic
def download_incident_json(request, id):
    """
    GET /api/incident/<id>/download-json/
    Returns full deep JSON export (sections don't apply — always full).
    """
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    tlp = parse_tlp(request.GET)
    data = generate_deep_json(incident, generated_by=request.user.username, tlp=tlp)

    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type='application/json; charset=utf-8'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_full.json"'
    )
    return response


@login_required(login_url='login')
@user_is_incident_responder_orpublic
def download_incident_csv(request, id):
    """
    GET /api/incident/<id>/download-csv/
    Returns a CSV of all IoCs (sections don't apply).
    Columns: Type, Value, Status, Description, Created At, Linked Actions
    """
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Type', 'Value', 'Status', 'Threat Intel Verdict', 'Description', 'Created At', 'Linked Actions'])

    for ioc in (
        incident.genericiocs.all()
        .prefetch_related('actions')
        .select_related('created_by')
    ):
        linked = ', '.join(str(a.title) for a in ioc.actions.all())
        rep = ioc.reputation
        if rep:
            verdict = rep.get('status', 'unknown').upper()
            vt = rep.get('vt') or {}
            if vt.get('total'):
                verdict += f" ({vt.get('malicious', 0)}/{vt['total']} engines)"
        else:
            verdict = ''
        writer.writerow([
            ioc.get_type_display(),
            ioc.value,
            ioc.get_status_display(),
            verdict,
            ioc.description or '',
            ioc.created_at.strftime('%Y-%m-%d %H:%M') if ioc.created_at else '',
            linked,
        ])

    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_iocs.csv"'
    )
    return response


@login_required(login_url='login')
@user_is_incident_responder
def download_incident_html(request, id):
    """
    POST /api/incident/<id>/download-html/
    Body: sections=..., tlp=...
    Returns the report as a self-contained .html archive download.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    sections = parse_sections(request.POST)
    tlp = parse_tlp(request.POST)
    tlp_style = TLP_STYLES[tlp]

    html = render_to_string('reports/report_template.html', {
        'incident': incident,
        'sections': sections,
        'tlp': tlp,
        'tlp_style': tlp_style,
        'is_pdf': False,
        'generated_at': timezone.now().strftime('%d %B %Y, %H:%M'),
        'generated_by': request.user.username,
    })

    response = HttpResponse(html, content_type='text/html; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_report.html"'
    )
    return response

@login_required(login_url='login')
@user_is_incident_responder
def download_incident_markdown(request, id):
    """
    POST /api/incident/<id>/download-markdown/
    Body: sections=..., tlp=...
    Returns a .md file download.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    sections = parse_sections(request.POST)
    tlp = parse_tlp(request.POST)

    content = generate_markdown(incident, sections, tlp, request.user.username)

    response = HttpResponse(content, content_type='text/markdown; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_report.md"'
    )
    return response

@login_required(login_url='login')
@user_is_incident_responder
def download_incident_pdf(request, id):
    """
    POST /api/incident/<id>/download-pdf/
    Body: sections=..., tlp=...
    Returns a PDF file download using xhtml2pdf.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    sections = parse_sections(request.POST)
    tlp = parse_tlp(request.POST)
    tlp_style = TLP_STYLES[tlp]

    html = render_to_string('reports/report_template.html', {
        'incident': incident,
        'sections': sections,
        'tlp': tlp,
        'tlp_style': tlp_style,
        'is_pdf': True,
        'generated_at': timezone.now().strftime('%d %B %Y, %H:%M'),
        'generated_by': request.user.username,
    })

    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')

    if pisa_status.err:
        return HttpResponse(
            f'PDF generation error (xhtml2pdf code {pisa_status.err}). '
            f'Try the HTML export as a workaround.',
            status=500
        )

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_report.pdf"'
    )
    return response

    
@login_required(login_url='login')
@user_is_incident_responder
def download_incident_word(request, id):
    """
    POST /api/incident/<id>/download-word/
    Body: sections=..., tlp=...
    Returns a .docx file download.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    sections = parse_sections(request.POST)
    tlp = parse_tlp(request.POST)

    doc = DocxDocument()

    # ── Cover ──
    doc.add_heading(incident.name, 0)

    tlp_para = doc.add_paragraph()
    tlp_run = tlp_para.add_run(f'TLP:{tlp}')
    tlp_run.bold = True
    tlp_run.font.size = Pt(13)
    tlp_run.font.color.rgb = TLP_COLORS.get(tlp, RGBColor(80, 80, 80))

    meta_para = doc.add_paragraph()
    meta_run = meta_para.add_run(
        f'Generated {timezone.now().strftime("%d %B %Y, %H:%M")} by {request.user.username}'
    )
    meta_run.font.color.rgb = RGBColor(130, 130, 130)
    doc.add_paragraph()  # spacer

    # ── Executive Summary ──
    if 'executive_summary' in sections:
        doc.add_heading('Executive Summary', 1)
        doc.add_paragraph(incident.executive_summary or 'No executive summary provided.')

    # ── Metadata ──
    if 'metadata' in sections:
        doc.add_heading('Incident Metadata', 1)
        table = doc.add_table(rows=0, cols=2)
        table.style = 'Table Grid'
        for label, value in [
            ('Severity', incident.severity),
            ('Status', incident.get_status_display()),
            ('Start time', str(incident.starting_time)),
            ('End time', str(incident.ending_time)),
            ('Duration', str(incident.duration)),
            ('Time to detect', str(incident.time_to_detect)),
            ('Time to respond', str(incident.time_to_respond)),
            ('Created by', incident.created_by.username if incident.created_by else 'Unknown'),
            ('Public', 'Yes' if incident.is_public else 'No'),
        ]:
            row = table.add_row().cells
            row[0].text = label
            row[1].text = value

    # ── Responders ──
    if 'responders' in sections:
        doc.add_heading('Responders', 1)
        roles_qs = incident.incident_roles.all().select_related('user')
        if roles_qs.exists():
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Table Grid'
            for i, h in enumerate(['Username', 'Display Name', 'Role', 'Display Role']):
                table.rows[0].cells[i].text = h
            for ur in roles_qs:
                row = table.add_row().cells
                row[0].text = ur.user.username
                row[1].text = ur.user.displayname or '-'
                row[2].text = ur.get_role_display()
                row[3].text = ur.display_role or '-'
        else:
            doc.add_paragraph('No responders recorded.')

    # ── Timeline ──
    if 'timeline' in sections:
        doc.add_heading('Timeline', 1)
        actions_qs = incident.actions.all().order_by('observed_at').select_related('created_by')
        if not actions_qs.exists():
            doc.add_paragraph('No timeline events recorded.')
        else:
            for action in actions_qs:
                if action.observed_at:
                    time_str = action.observed_at.strftime('%d %b %Y %H:%M')
                elif action.starting_time:
                    time_str = action.starting_time.strftime('%d %b %Y %H:%M')
                else:
                    time_str = ''
                p = doc.add_paragraph(style='List Bullet')
                r = p.add_run(f'[{action.get_type_display()}] {action.title}')
                r.bold = True
                if time_str:
                    p.add_run(f'  —  {time_str}')
                if action.description:
                    doc.add_paragraph(action.description)

    # ── IoCs ──
    if 'iocs' in sections:
        doc.add_heading('IoC / Evidence', 1)
        iocs_qs = incident.genericiocs.all()
        if not iocs_qs.exists():
            doc.add_paragraph('No IoCs recorded.')
        else:
            table = doc.add_table(rows=1, cols=5)
            table.style = 'Table Grid'
            for i, h in enumerate(['Type', 'Value', 'Status', 'Threat Intel Verdict', 'Description']):
                table.rows[0].cells[i].text = h
            for ioc in iocs_qs:
                rep = ioc.reputation
                if rep:
                    verdict = rep.get('status', 'unknown').upper()
                    vt = rep.get('vt') or {}
                    if vt.get('total'):
                        verdict += f" ({vt.get('malicious', 0)}/{vt['total']} engines)"
                else:
                    verdict = '—'
                row = table.add_row().cells
                row[0].text = ioc.get_type_display()
                row[1].text = ioc.value
                row[2].text = ioc.get_status_display()
                row[3].text = verdict
                row[4].text = ioc.description or '-'

    # ── Tasks ──
    if 'tasks' in sections:
        doc.add_heading('Tasks', 1)
        tasks_qs = incident.tasks.all().select_related('assignee')
        if not tasks_qs.exists():
            doc.add_paragraph('No tasks recorded.')
        else:
            table = doc.add_table(rows=1, cols=5)
            table.style = 'Table Grid'
            for i, h in enumerate(['Priority', 'Title', 'Status', 'Assignee', 'Description']):
                table.rows[0].cells[i].text = h
            for task in tasks_qs:
                row = table.add_row().cells
                row[0].text = task.priority
                row[1].text = task.title
                row[2].text = task.status
                row[3].text = task.assignee.username if task.assignee else '-'
                row[4].text = task.description or '-'

    # ── Notes ──
    if 'notes' in sections:
        doc.add_heading('Notes', 1)
        notes_qs = incident.notes.all().select_related('created_by')
        if not notes_qs.exists():
            doc.add_paragraph('No notes recorded.')
        else:
            for note in notes_qs:
                doc.add_heading(note.name, 2)
                author = note.created_by.username if note.created_by else 'Unknown'
                p = doc.add_paragraph()
                p.add_run(
                    f'{author}  ·  {note.created_at.strftime("%d %b %Y %H:%M") if note.created_at else ""}'
                ).italic = True
                doc.add_paragraph(note.text)

    # ── Lessons Learned ──
    if 'lessons_learned' in sections:
        doc.add_heading('Lessons Learned', 1)
        ll = incident.lessons_learned
        doc.add_paragraph(
            ll if ll and ll != 'SOME STRING' else 'No lessons learned recorded.'
        )

    # ── Technical Details ──
    if 'technical_details' in sections:
        doc.add_heading('Technical Details', 1)
        td = incident.technical_details
        doc.add_paragraph(
            td if td and td != 'SOME STRING' else 'No technical details recorded.'
        )

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="incident_{incident.id}_report.docx"'
    )
    return response


@login_required
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
@user_is_incident_responder
def send_message(request, id):
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data.get('message')
        incident = Incident.objects.get(pk=id)
        
        # Create a new message in the database
        message = Message.objects.create(
            incident=incident,
            sender=request.user,
            text=text
        )

        return JsonResponse({
            'status': 'success',
            'message': message.text,
            'sender': message.sender.username,
            'timestamp': message.created_at
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required(login_url='login')
@user_is_incident_responder
def get_messages(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        msgs = incident.messages.all().order_by('created_at').select_related('sender')
        data = []
        for msg in msgs:
            if msg.is_bot:
                display, initial, username = 'System', 'S', None
            elif msg.sender:
                display = (msg.sender.displayname if hasattr(msg.sender, 'displayname') and msg.sender.displayname
                           else msg.sender.username)
                initial = display[0].upper() if display else '?'
                username = msg.sender.username
            else:
                display, initial, username = 'System', 'S', None
            data.append({
                'id': msg.id,
                'text': msg.text,
                'sender_username': username,
                'sender_display': display,
                'sender_initial': initial,
                'created_at': msg.created_at.strftime('%H:%M'),
                'is_bot': msg.is_bot,
                'link': msg.link,
            })
        return JsonResponse({'status': 'success', 'messages': data, 'current_user': request.user.username})
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)


@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def add_ioc(request, id):
    try:
        if request.method == 'POST':
            incident = Incident.objects.get(pk=id)
            ioc_type = request.POST.get('type')
            ioc_value = request.POST.get('value')
            ioc_description = request.POST.get('description', '')
            ioc_tags = request.POST.get('tag', '')

            # Create new IOC instance
            ioc = GenericIoc.objects.create(
                incident=incident,
                type=ioc_type,
                value=ioc_value,
                description=ioc_description,
                tag=ioc_tags
            )
            if ioc_type in THREAT_INTEL_ELIGIBLE_TYPES:
                schedule_lookup(ioc.id)
            Message.objects.create(
                incident=incident,
                sender=request.user,
                text=f"{request.user.username} added a new {ioc.get_type_display()} IoC: {ioc.value}",
                is_bot=True,
                link=f"/incident/{incident.id}/iocs"
            )
            _audit(incident, request, 'CREATE', 'IoC', f'Added {ioc.get_type_display()} IoC: {ioc.value}')
            supported = _cti_supported_types()
            if supported and ioc.type in supported:
                return redirect(f'/incident/{id}/iocs?check_new={ioc.id}')
            return redirect('/incident/' + str(id) + '/iocs')
        
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Invalid incident'}, status=400)
    except:
        return JsonResponse({'error': 'Invalid method'}, status=400)

@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def add_action(request, id):
    try:
        if request.method == 'POST':
            incident = Incident.objects.get(pk=id)
            data = json.loads(request.body)

            action_title =  data.get('title')
            action_description =  data.get('description')
            action_type =  data.get('type')
            action_iocs =  data.get('iocs', '')
            action_tags = data.get('tags', '')
            action_observed_at = data.get('observed_at')
            action_starting_time = data.get('starting_time')
            action_ending_time = data.get('ending_time')

            # Validate timing BEFORE creating anything, otherwise a bad request
            # leaves an orphan action behind while still returning an error.
            if not action_observed_at and not (action_starting_time and action_ending_time):
                return JsonResponse(
                    {'error': 'Please provide an Observed time, or both a Starting and Ending time.'},
                    status=400,
                )

            action = Action.objects.create(
                incident = incident,
                title = action_title,
                description = action_description,
                type = action_type,
                created_by = request.user,
                observed_at = action_observed_at or None,
                starting_time = None if action_observed_at else action_starting_time,
                ending_time = None if action_observed_at else action_ending_time,
            )

            if action_tags:
                action.tags.set(action_tags)
            if action_iocs:
                action.iocs.set(action_iocs)
            update_first_actions(incident=incident)
            Message.objects.create(
                incident=incident,
                sender=request.user,
                text=f"{request.user.username} added timeline action: {action.title}",
                is_bot=True,
                link=f"/incident/{incident.id}/timeline"
            )
            _audit(incident, request, 'CREATE', 'Timeline', f'Added timeline event "{action.title}"')
            return JsonResponse({"status": "success", "message": "Action added successfully"})
        else:
            return JsonResponse({'error': 'Invalid method'}, status=400)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Invalid incident'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Other error :{e}'}, status=400)


# ── Bulk CSV import ────────────────────────────────────────────────────────
MAX_IMPORT_BYTES = 2 * 1024 * 1024  # 2 MB


def _read_csv_rows(request):
    """Return (rows, fieldmap, error_response). Shared CSV decoding for imports."""
    f = request.FILES.get('file')
    if not f:
        return None, None, JsonResponse({'error': 'No CSV file uploaded.'}, status=400)
    if f.size > MAX_IMPORT_BYTES:
        return None, None, JsonResponse({'error': 'File too large (max 2 MB).'}, status=400)
    try:
        text = f.read().decode('utf-8-sig')
    except (UnicodeDecodeError, AttributeError):
        return None, None, JsonResponse({'error': 'File must be a UTF-8 encoded CSV.'}, status=400)

    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        return None, None, JsonResponse({'error': 'CSV is empty or has no header row.'}, status=400)
    fieldmap = {(h or '').strip().lower(): h for h in reader.fieldnames}
    return list(reader), fieldmap, None


def _import_parse_dt(s):
    """Parse an ISO-ish datetime string to an aware datetime, or None if blank/invalid."""
    from django.utils.dateparse import parse_datetime, parse_date
    s = (s or '').strip()
    if not s:
        return None
    dt = parse_datetime(s)
    if dt is None:
        d = parse_date(s)
        if d:
            dt = datetime(d.year, d.month, d.day)
    if dt is not None and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def import_iocs(request, id):
    """Bulk-create IoCs from an uploaded CSV (columns: type, value, description, status)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Invalid incident'}, status=400)

    rows, fieldmap, err = _read_csv_rows(request)
    if err:
        return err
    if 'value' not in fieldmap:
        return JsonResponse({'error': "CSV must have a 'value' column. Expected columns: type, value, description, status."}, status=400)

    valid_types = {c[0] for c in GenericIoc._meta.get_field('type').choices}
    valid_status = {c[0] for c in GenericIoc._meta.get_field('status').choices}

    def cell(row, col):
        h = fieldmap.get(col)
        return (row.get(h) or '').strip() if h else ''

    created, skipped, errors = 0, 0, []
    for i, row in enumerate(rows, start=2):  # row 1 is the header
        value = cell(row, 'value')
        if not value:
            skipped += 1
            continue
        ioc_type = cell(row, 'type').upper()
        ioc_type = {'IPV4': 'IPADRESS', 'IPV6': 'IPADRESS', 'IP': 'IPADRESS'}.get(ioc_type, ioc_type)
        if ioc_type not in valid_types:
            ioc_type = 'OTHER'
        status = cell(row, 'status').upper()
        if status not in valid_status:
            status = 'SAFE'
        try:
            ioc = GenericIoc.objects.create(
                incident=incident,
                type=ioc_type,
                value=value,
                description=cell(row, 'description'),
                status=status,
                created_by=request.user,
                tag='',
            )
            created += 1
            if ioc.type in THREAT_INTEL_ELIGIBLE_TYPES:
                schedule_lookup(ioc.id)
        except Exception as e:
            errors.append(f'Row {i}: {e}')

    if created:
        Message.objects.create(
            incident=incident, sender=request.user, is_bot=True,
            text=f"{request.user.username} imported {created} IoC(s) from CSV",
            link=f"/incident/{incident.id}/iocs",
        )
        _audit(incident, request, 'CREATE', 'IoC', f'Bulk-imported {created} IoC(s) from CSV')

    return JsonResponse({'status': 'success', 'created': created, 'skipped': skipped, 'errors': errors[:20]})


@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def import_actions(request, id):
    """Bulk-create timeline actions from an uploaded CSV.

    Columns: title, description, type, observed_at (or starting_time + ending_time).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    try:
        incident = Incident.objects.get(pk=id)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Invalid incident'}, status=400)

    rows, fieldmap, err = _read_csv_rows(request)
    if err:
        return err
    if 'title' not in fieldmap:
        return JsonResponse({'error': "CSV must have a 'title' column. Expected columns: title, description, type, observed_at."}, status=400)

    valid_types = {c[0] for c in Action._meta.get_field('type').choices}

    def cell(row, col):
        h = fieldmap.get(col)
        return (row.get(h) or '').strip() if h else ''

    created, skipped, errors = 0, 0, []
    for i, row in enumerate(rows, start=2):
        title = cell(row, 'title')
        if not title:
            skipped += 1
            continue
        atype = cell(row, 'type').upper()
        if atype not in valid_types:
            atype = 'OTHER'
        observed_raw = cell(row, 'observed_at') or cell(row, 'time') or cell(row, 'date')
        starting_raw = cell(row, 'starting_time')
        ending_raw = cell(row, 'ending_time')
        if not observed_raw and not (starting_raw and ending_raw):
            errors.append(f'Row {i}: missing time (need observed_at, or both starting_time and ending_time)')
            skipped += 1
            continue
        try:
            if observed_raw:
                observed = _import_parse_dt(observed_raw)
                if observed is None:
                    raise ValueError(f"could not parse observed_at '{observed_raw}'")
                starting = ending = None
            else:
                observed = None
                starting = _import_parse_dt(starting_raw)
                ending = _import_parse_dt(ending_raw)
                if starting is None or ending is None:
                    raise ValueError('could not parse starting_time/ending_time')
            Action.objects.create(
                incident=incident,
                title=title[:200],
                description=cell(row, 'description'),
                type=atype,
                created_by=request.user,
                observed_at=observed,
                starting_time=starting,
                ending_time=ending,
            )
            created += 1
        except Exception as e:
            errors.append(f'Row {i}: {e}')

    if created:
        update_first_actions(incident=incident)
        Message.objects.create(
            incident=incident, sender=request.user, is_bot=True,
            text=f"{request.user.username} imported {created} timeline action(s) from CSV",
            link=f"/incident/{incident.id}/timeline",
        )
        _audit(incident, request, 'CREATE', 'Timeline', f'Bulk-imported {created} timeline action(s) from CSV')

    return JsonResponse({'status': 'success', 'created': created, 'skipped': skipped, 'errors': errors[:20]})


@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def update_action(request, id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action_id = data.get('id')
            
            if not action_id:
                return JsonResponse({'error': 'Action ID is required'}, status=400)

            action = Action.objects.get(pk=action_id)

            if action.incident.id != id:
                return JsonResponse({'error': 'Action is not associated with the specified incident'}, status=403)

            action.title = data.get('title')
            action.description = data.get('description')
            action.type = data.get('type')
            if data.get('observed_at'):
                action.observed_at = data.get('observed_at')
                action.starting_time = None
                action.ending_time = None
            else:
                action.starting_time = data.get('starting_time')
                action.ending_time = data.get('ending_time')
                action.observed_at = None
            action.iocs.set(data.get('iocs'))
            action.tags.set(data.get('tags'))
            
            action.save()
            update_first_actions(incident=action.incident)
            _audit(action.incident, request, 'UPDATE', 'Timeline', f'Updated timeline event "{action.title}"')
            return JsonResponse({"status": "success", "message": "Action updated successfully"})

        except Action.DoesNotExist:
            return JsonResponse({'error': 'Action not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def delete_action(request, id):
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            action_id = data.get('id')
            
            if not action_id:
                return JsonResponse({'error': 'Action ID is required'}, status=400)

            action = Action.objects.get(pk=action_id)

            if action.incident.id != id:
                return JsonResponse({'error': 'Action is not associated with the specified incident'}, status=403)

            incident = action.incident
            action_title = action.title
            action.delete()
            update_first_actions(incident=incident)
            _audit(incident, request, 'DELETE', 'Timeline', f'Deleted timeline event "{action_title}"')
            return JsonResponse({"status": "success", "message": "Action deleted successfully"})

        except Action.DoesNotExist:
            return JsonResponse({'error': 'Action not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def get_action(request, id, action_id):
    if request.method == 'GET':
        try:
            if not action_id:
                return JsonResponse({'error': 'Action ID is required'}, status=400)
            
            action = Action.objects.get(pk=action_id)
            if action.incident.id != id:
                return JsonResponse({'error': 'Action is not associated with the specified incident'}, status=403)

            action_data = {
                "id": action.id,
                "type": action.type,
                "title": action.title,
                "description": action.description,
                "created_at": action.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "updated_at": action.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                "observed_at": action.observed_at.strftime('%Y-%m-%d %H:%M:%S') if action.observed_at else "",
                "starting_time": action.starting_time.strftime('%Y-%m-%d %H:%M:%S') if action.starting_time else "",
                "ending_time": action.ending_time.strftime('%Y-%m-%d %H:%M:%S') if action.ending_time else "",
                "created_by": action.created_by.username if action.created_by else "Unknown",
                "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in action.tags.all()],
                "iocs": [{"id": ioc.id, "value": ioc.value, "description": ioc.description, "type": ioc.type, "created_at": ioc.created_at.strftime('%Y-%m-%d %H:%M:%S')} for ioc in action.iocs.all()]
            }
            
            return JsonResponse({"status": "success", "data": action_data})

        except Action.DoesNotExist:
            return JsonResponse({'error': 'Action not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)



@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def add_task(request, id):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
            incident = Incident.objects.get(pk=id)
            task_title = data.get('title')
            task_description = data.get('description')
            task_status = data.get('status')
            task_priority = data.get('priority')
            task_assignee = data.get('assignee')
            task_external_reference = data.get('external_reference')
            task_tags = data.get('tags')
            task = Task.objects.create(
                incident=incident,
                title=task_title,
                description=task_description,
                status=task_status,
                priority=task_priority,
                external_reference=task_external_reference,
                created_by = request.user

            )
            if task_assignee:
                user = User.objects.filter(id=task_assignee).first()
                if user:
                    task.assignee = user
                    task.save()

            if task_tags:
                task.tags.set(task_tags)
                task.save()

            Message.objects.create(
                incident=incident,
                sender=request.user,
                text=f"{request.user.username} created task: {task.title}",
                is_bot=True,
                link=f"/incident/{incident.id}/tasks"
            )
            _audit(incident, request, 'CREATE', 'Task', f'Created task "{task.title}" [{task.priority} / {task.status}]')
            return redirect('/incident/' + str(id) + '/tasks')
        
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Invalid incident'}, status=400)
    except:
        return JsonResponse({'error': 'Invalid method'}, status=400)

@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def update_task(request, id):
    try:
        if request.method == 'POST':
            
            data = json.loads(request.body)
            incident = Incident.objects.get(pk=id)
            task_id = data.get('id')
            task = Task.objects.get(id=task_id)
            task.title = data.get('title')
            task.description = data.get('description')
            task.status = data.get('status')
            task.priority = data.get('priority')            
            task.external_reference = data.get('external_reference')
            task.tags.set(data.get('tags'))
            
            if data.get('assignee'):
                task.assignee = User.objects.get(pk=data.get('assignee'))
            else: 
                task.assignee = None
            task.save()
            _audit(incident, request, 'UPDATE', 'Task', f'Updated task "{task.title}"')
            return redirect('/incident/' + str(id) + '/tasks')

    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Invalid incident'}, status=400)
    except:
        return JsonResponse({'error': 'Invalid method'}, status=400)

@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def delete_task(request, id):
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            task_id = data.get('id')
            
            if not task_id:
                return JsonResponse({'error': 'Task ID is required'}, status=400)

            task = Task.objects.get(pk=task_id)

            if task.incident.id != id:
                return JsonResponse({'error': 'Task is not associated with the specified incident'}, status=403)

            incident = task.incident
            task_title = task.title
            task.delete()
            _audit(incident, request, 'DELETE', 'Task', f'Deleted task "{task_title}"')
            return JsonResponse({"status": "success", "message": "Task deleted successfully"})

        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def delete_ioc(request, id):
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            ioc_id = data.get('ioc_id')
            
            if not ioc_id:
                return JsonResponse({'error': 'IoC ID is required'}, status=400)

            ioc = GenericIoc.objects.get(pk=ioc_id)

            if ioc.incident.id != id:
                return JsonResponse({'error': 'IoC is not associated with the specified incident'}, status=403)

            incident = ioc.incident
            ioc_value = ioc.value
            ioc.delete()
            _audit(incident, request, 'DELETE', 'IoC', f'Deleted IoC: {ioc_value}')
            return JsonResponse({"status": "success", "message": "IoC deleted successfully"})

        except GenericIoc.DoesNotExist:
            return JsonResponse({'error': 'IoC not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required(login_url='login')
@user_is_incident_responder_orpublic
def get_all_iocs(request, id):
    if request.method == 'GET':
        try:
            incident = Incident.objects.get(pk=id)
            iocs = GenericIoc.objects.filter(incident=incident)
            
            ioc_list = [
                {
                    "id": ioc.id,
                    "value": ioc.value,
                    "type": ioc.type,
                    "description": ioc.description,
                    "status": ioc.status,
                    "reputation": ioc.reputation,
                }
                for ioc in iocs
            ]
            
            return JsonResponse({"status": "success", "iocs": ioc_list}, status=200)
            
        except Incident.DoesNotExist:
            return JsonResponse({'error': 'Incident not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required(login_url='login')
@user_is_incident_responder_orpublic
def get_ioc(request, id, ioc_id):
    if request.method == 'GET':
        try:
            if not ioc_id:
                return JsonResponse({'error': 'IoC ID is required'}, status=400)
            
            ioc = GenericIoc.objects.get(pk=ioc_id)
            if ioc.incident.id != id:
                return JsonResponse({'error': 'IoC is not associated with the specified incident'}, status=403)


            ioc_data = {
                "id": ioc.id,
                "value": ioc.value,
                "type": ioc.type,
                "description": ioc.description,
                "status": ioc.status,
                "reputation": ioc.reputation,
                "created_at": ioc.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "updated_at": ioc.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                "created_by": ioc.created_by.username if ioc.created_by else "Unknown",
                "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in ioc.tags.all()],
                "actions": [{"id": action.id, "title": action.title, "description": action.description, "created_at": action.created_at.strftime('%Y-%m-%d %H:%M:%S')} for action in ioc.actions.all()]
            }
            
            return JsonResponse({"status": "success", "data": ioc_data})

        except GenericIoc.DoesNotExist:
            return JsonResponse({'error': 'IoC not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def get_impact(request, id, impact_id):
    if request.method == 'GET':
        try:
            if not impact_id:
                return JsonResponse({'error': 'Impact ID is required'}, status=400)
            
            impact = Impact.objects.get(pk=impact_id)
            if impact.incident.id != id:
                return JsonResponse({'error': 'Impact is not associated with the specified incident'}, status=403)


            impact_data = {
                "id": impact.id,
                "title": impact.title,
                "type": impact.type,
                "description": impact.description,
                "status": impact.status,
                "severity": impact.severity,
                "description": impact.description,
                "external_reference": impact.external_reference,
                "starting_time": impact.starting_time.strftime("%Y-%m-%dT%H:%M"),
                "ending_time": impact.ending_time.strftime("%Y-%m-%dT%H:%M"),
                "created_at": impact.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "updated_at": impact.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                "created_by": impact.created_by.username if impact.created_by else "Unknown",
                "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in impact.tags.all()]
            }
            
            return JsonResponse({"status": "success", "data": impact_data})

        except Impact.DoesNotExist:
            return JsonResponse({'error': 'Impact not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

        
@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def update_ioc(request, id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            body = json.loads(request.body.decode('utf-8'))
            ioc_id = body.get('ioc_id')
            ioc = GenericIoc.objects.get(id=ioc_id)
            
            ioc.type = body.get('type')
            ioc.value = body.get('value')
            ioc.description = body.get('description')
            ioc.save()
            _audit(ioc.incident, request, 'UPDATE', 'IoC', f'Updated IoC: {ioc.value}')
            return JsonResponse({'status': 'success', id: id})

        except GenericIoc.DoesNotExist:
            return JsonResponse({'error': 'Ioc not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def update_impact(request, id):
    if request.method == 'POST':
        try:

            data = json.loads(request.body)['data']
            impact_id = data['id']
            impact = Impact.objects.get(id=impact_id)
            print(data)
            for field, value in data.items():
                if hasattr(impact, field):
                    setattr(impact, field, value)

            impact.duration = datetime.strptime(impact.ending_time, "%Y-%m-%dT%H:%M") - datetime.strptime(impact.starting_time, "%Y-%m-%dT%H:%M")
            print(impact.duration)
            impact.save()
            
            return JsonResponse({'status': 'success', id: impact_id})

        except Impact.DoesNotExist as e:
            return JsonResponse({'error': f'Impact not found {e}'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required(login_url='login')
@user_is_incident_responder
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def delete_impact(request, id):
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            ioc_id = data.get('ioc_id')
            
            if not ioc_id:
                return JsonResponse({'error': 'IoC ID is required'}, status=400)

            ioc = GenericIoc.objects.get(pk=ioc_id)

            if ioc.incident.id != id:
                return JsonResponse({'error': 'IoC is not associated with the specified incident'}, status=403)

            ioc.delete()
            return JsonResponse({"status": "success", "message": "IoC deleted successfully"})

        except GenericIoc.DoesNotExist:
            return JsonResponse({'error': 'IoC not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)



@login_required(login_url='login')
@verify_permissions(['INCIDENT_LEAD'])
def update_role(request, id):
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request method"}, status=403)
    incident = get_object_or_404(Incident, id=id)
    body = json.loads(request.body.decode('utf-8'))
    user_id = body.get('user_id')

    new_role = body.get('role')
    display_role = body.get('display_role')
    
    if not user_id and not (new_role or display_role):
        return JsonResponse({"error": "Missing user_id or role or display_role"}, status=400)
    
    user = get_object_or_404(User, id=user_id)
    user_role, created = UserRole.objects.get_or_create(user=user, incident=incident)
    if new_role:
        if new_role not in dict(USER_ROLES_CHOICES):
            return JsonResponse({"error": "Invalid role selected"}, status=400)
        user_role.role = new_role
        user_role.save()
        _audit(incident, request, 'UPDATE', 'Team', f'Changed role of {user.username} to {new_role}')
        return JsonResponse({"success": f"Role of {user.username} updated to {new_role}"}, status=200)

    if display_role:
        user_role.display_role = display_role
        user_role.save()
        _audit(incident, request, 'UPDATE', 'Team', f'Set display role of {user.username} to "{display_role}"')
        return JsonResponse({"success": f"Display Role of {user.username} updated to {display_role}"}, status=200)

@login_required(login_url='login')
@verify_permissions(['INCIDENT_LEAD'])
def delete_role(request, id):
    if request.method == 'POST':
        try:
            incident = get_object_or_404(Incident, id=id)

            body = json.loads(request.body.decode('utf-8'))
            user_id = body.get('user_id')
            userrole = UserRole.objects.get(incident=incident, user=user_id)

            # Check if the role being deleted is INCIDENT_LEAD
            if userrole.role == 'INCIDENT_LEAD':
                incident_id = userrole.incident.id
                
                # Count other INCIDENT_LEAD roles in the same incident
                incident_lead_count = UserRole.objects.filter(
                    incident_id=incident_id, 
                    role='INCIDENT_LEAD'
                ).exclude(id=userrole.id).count()
                
                if incident_lead_count == 0:
                    return JsonResponse({
                        'error': 'You must designate another Incident Lead before deleting this one.'
                    }, status=400)


            removed_user = userrole.user.username
            userrole.delete()
            _audit(incident, request, 'DELETE', 'Team', f'Removed responder {removed_user}')
            return JsonResponse({"status": "success", "message": "Responder deleted successfully"})
        except UserRole.DoesNotExist:
            return JsonResponse({'error': 'Responder not found'}, status=404)    
        
@login_required(login_url='login')
@verify_permissions(['INCIDENT_LEAD', 'RESPONDER'])
def update_incident(request, id):
    if request.method == 'POST':
        try:
            # Fetch the incident object
            incident = Incident.objects.get(id=id)
            data = json.loads(request.body)

            # Verify the user role inside the update_incident function
            user_role = UserRole.objects.get(user=request.user, incident_id=id).role

            if user_role == 'INCIDENT_LEAD':
                # If user is INCIDENT_LEAD, they can modify the title as well
                if 'title' in data:
                    incident.name = data['title']
            elif user_role == 'RESPONDER':
                # If user is RESPONDER, they can't modify the title, status, or severity
                if 'title' in data:
                    return JsonResponse({'error': 'Permission denied: You cannot modify the title'}, status=403)
                if 'status' in data:
                    return JsonResponse({'error': 'Permission denied: You cannot modify the status'}, status=403)
                if 'severity' in data:
                    return JsonResponse({'error': 'Permission denied: You cannot modify the severity'}, status=403)

            # Allow modification of other fields for both roles
            if 'description' in data:
                incident.description = data['description']
            if 'executive_summary' in data:
                incident.executive_summary = data['executive_summary']
            if 'lessons_learned' in data:
                incident.lessons_learned = data['lessons_learned']
            if 'technical_details' in data:
                incident.technical_details = data['technical_details']
            if 'external_reference' in data:
                incident.external_reference = (data['external_reference'] or '')[:255]
            if 'status' in data:
                incident.status = data['status']
            if 'severity' in data:
                incident.severity = data['severity']
            if 'export_include_timeline' in data:
                incident.export_include_timeline = data['export_include_timeline']
            if 'export_include_iocs' in data:
                incident.export_include_iocs = data['export_include_iocs']
            if 'export_include_attachements' in data:
                incident.export_include_attachements = data['export_include_attachements']
            if 'tlp' in data:
                valid_tlp = ('CLEAR', 'GREEN', 'AMBER', 'RED')
                if data['tlp'] in valid_tlp:
                    incident.tlp = data['tlp']
            if 'is_public' in data and user_role == 'INCIDENT_LEAD':
                incident.is_public = bool(data['is_public'])
            if 'ai_rephrase_enabled' in data and user_role == 'INCIDENT_LEAD':
                incident.ai_rephrase_enabled = bool(data['ai_rephrase_enabled'])

            # Save the updated incident
            incident.save()

            # Describe what changed for the audit log
            changed = [k for k in ('title','status','severity','tlp','is_public',
                                   'description','executive_summary','lessons_learned',
                                   'technical_details','external_reference') if k in data]
            if changed:
                _audit(incident, request, 'UPDATE', 'Settings',
                       f'Updated incident fields: {", ".join(changed)}')

            return JsonResponse({'status': 'success', 'message': 'Incident updated successfully'})
        except Incident.DoesNotExist:
            return JsonResponse({'error': 'Incident not found'}, status=404)
        

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password

@login_required(login_url='login') 
def update_profile(request):
    if request.method == 'POST':
        try:
            user = request.user
            new_username = request.POST.get("username", user.username)

            # Check if the username is already taken by another user
            if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                return JsonResponse({'error': "This username is already taken"}, status=403)

            user.displayname = request.POST.get("displayname", user.displayname)
            user.email = request.POST.get("email", user.email)
            user.light_mode = request.POST.get("light_mode")

            # Handle profile picture upload
            if "profile_picture" in request.FILES:
                profile_picture = request.FILES["profile_picture"]
                ext = os.path.splitext(profile_picture.name)[1].lower()
                if ext not in [".jpg", ".jpeg", ".png"]:
                    return JsonResponse({'error': "You ain't uploading any webshells on my app you dirty cow. Only JPG and PNG are allowed"}, status=403)

                user.profile_picture.save(profile_picture.name, profile_picture)

            # Handle password change
            current_password = request.POST.get("current_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if current_password and new_password and confirm_password:
                if not check_password(current_password, user.password):
                    return JsonResponse({'error': "Current password is incorrect"}, status=403)
                
                if new_password != confirm_password:
                    return JsonResponse({'error': "New passwords do not match"}, status=403)

                user.set_password(new_password)  # Securely update password
                update_session_auth_hash(request, user)  # Keep the user logged in

            # Save notification preferences
            prefs = user.preferences if user.preferences else {}
            prefs['notify_assignment'] = 'notify_assignment' in request.POST
            prefs['notify_mention'] = 'notify_mention' in request.POST
            user.preferences = prefs

            # Save the updated user profile
            user.save()

            return render(request, 'profile.html', {
                'user': request.user,
                'prefs': prefs,
                'success': 'Profile updated successfully!',
            })

        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)


# ── Audit log API ─────────────────────────────────────────────────────────────

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def get_audit_logs(request, id):
    """Return the last 500 audit log entries for an incident as JSON."""
    incident = get_object_or_404(Incident, pk=id)
    logs = (
        AuditLog.objects
        .filter(incident=incident)
        .select_related('user')
        .order_by('-timestamp')[:500]
    )
    data = [
        {
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'user':      log.user.username if log.user else '—',
            'ip':        log.ip_address or '—',
            'action':    log.action,
            'type':      log.object_type,
            'description': log.description,
        }
        for log in logs
    ]
    return JsonResponse({'logs': data})


@login_required(login_url='login')
@user_is_incident_responder_orpublic
def export_audit_logs(request, id):
    """Download audit logs as CSV."""
    incident = get_object_or_404(Incident, pk=id)
    logs = (
        AuditLog.objects
        .filter(incident=incident)
        .select_related('user')
        .order_by('-timestamp')
    )
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(['Timestamp (UTC)', 'User', 'IP Address', 'Action', 'Type', 'Description'])
    for log in logs:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.user.username if log.user else '',
            log.ip_address,
            log.action,
            log.object_type,
            log.description,
        ])
    _audit(incident, request, 'EXPORT', 'Audit Log', 'Exported audit log as CSV')
    response = HttpResponse(buf.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="audit_log_incident_{id}.csv"'
    )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# AI REPHRASE
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def ai_rephrase(request, id):
    """
    POST  /api/incident/<id>/ai-rephrase/
    Body: { "field": "description" | "executive_summary" | "technical_details" | "lessons_learned" }

    Generates text for the requested field using Anthropic Claude (preferred)
    or OpenAI GPT depending on which API key is configured on the server.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    incident = get_object_or_404(Incident, pk=id)

    if not incident.ai_rephrase_enabled:
        return JsonResponse({'error': 'AI rephrase is not enabled for this incident.'}, status=403)

    # Restrict to write-capable roles
    try:
        user_role = UserRole.objects.get(user=request.user, incident_id=id).role
        if user_role in ('READER', 'PUBLIC_VIEWER'):
            return JsonResponse({'error': 'Permission denied: read-only role.'}, status=403)
    except UserRole.DoesNotExist:
        pass  # Public incident — logged-in non-responder; allow (already passed decorator)

    try:
        body = json.loads(request.body)
        field = body.get('field', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    valid_fields = ('description', 'executive_summary', 'technical_details', 'lessons_learned')
    if field not in valid_fields:
        return JsonResponse(
            {'error': f'Invalid field. Must be one of: {", ".join(valid_fields)}'},
            status=400,
        )

    # Resolve provider and API key — DB takes priority, env vars are fallback
    anthropic_key = ''
    openai_key    = ''
    ps = PlatformSettings.get()

    if ps.ai_provider == 'ANTHROPIC' and ps.ai_api_key:
        anthropic_key = ps.ai_api_key
    elif ps.ai_provider == 'OPENAI' and ps.ai_api_key:
        openai_key = ps.ai_api_key
    else:
        # Fallback: environment / settings.py (dev convenience)
        from django.conf import settings as _settings
        _ant = getattr(_settings, 'ANTHROPIC_API_KEY', '') or os.environ.get('ANTHROPIC_API_KEY', '')
        _oai = getattr(_settings, 'OPENAI_API_KEY',    '') or os.environ.get('OPENAI_API_KEY',    '')
        if _ant:
            anthropic_key = _ant
        elif _oai:
            openai_key = _oai

    if not anthropic_key and not openai_key:
        return JsonResponse(
            {'error': 'AI is not configured. An administrator must set the AI provider '
                      'and API key in Platform Settings.'},
            status=503,
        )

    # ── Build incident context ────────────────────────────────────────────
    actions = incident.actions.all().order_by('observed_at', 'starting_time')
    iocs    = incident.genericiocs.all()
    tasks   = incident.tasks.all()

    def _fmt(dt):
        return dt.strftime('%Y-%m-%d %H:%M') if dt else 'unknown'

    action_lines = [
        f"  [{_fmt(a.observed_at or a.starting_time)}] {a.type}: {a.title} — {a.description or '(no description)'}"
        for a in actions
    ] or ['  (no events recorded)']

    ioc_lines = [
        f"  {ioc.type}: {ioc.value} — {ioc.description or '(no description)'}"
        for ioc in iocs
    ] or ['  (no IoCs recorded)']

    task_lines = [
        f"  [{t.status}] {t.title}: {t.description or '(no description)'}"
        for t in tasks
    ] or ['  (no tasks recorded)']

    FIELD_INSTRUCTIONS = {
        'description': (
            'Write a concise incident description (2–4 sentences). '
            'Summarise what happened: incident type, initial vector if known, affected systems, and scope. '
            'Use factual, neutral language. Plain text only — no markdown, no headings.'
        ),
        'executive_summary': (
            'Write a professional executive summary (3–5 sentences) for a non-technical audience. '
            'Focus on business impact, what was affected, the response taken, and current status. '
            'Avoid technical jargon. Plain text only — no markdown, no headings.'
        ),
        'technical_details': (
            'Write a detailed technical analysis. '
            'Cover the attack vector, techniques observed (reference specific IoCs and timeline events), '
            'affected systems, and containment actions taken. '
            'Be precise and technical. Plain text only — no markdown, no headings.'
        ),
        'lessons_learned': (
            'Write a lessons learned section covering: what detection gaps existed, what response actions worked well, '
            'what could have been improved, and 3–5 concrete recommendations to prevent recurrence. '
            'Be actionable. Plain text only — no markdown, no headings.'
        ),
    }

    field_display = field.replace('_', ' ').title()

    prompt = (
        f'You are a senior incident response analyst writing a professional security incident report.\n\n'
        f'Based on the incident data below, write ONLY the "{field_display}" section.\n'
        f'Do NOT include a heading or section title. Output plain prose only — no markdown, '
        f'no bullet points, no bold/italic formatting.\n\n'
        f'INCIDENT: {incident.name}\n'
        f'STATUS: {incident.status} | SEVERITY: {incident.severity} | TLP: {incident.tlp}\n'
        f'STARTED: {_fmt(incident.starting_time)} | '
        f'ENDED: {_fmt(incident.ending_time) if incident.ending_time else "ongoing"}\n\n'
        f'TIMELINE ({actions.count()} events):\n' + '\n'.join(action_lines) + '\n\n'
        f'INDICATORS OF COMPROMISE ({iocs.count()} IoCs):\n' + '\n'.join(ioc_lines) + '\n\n'
        f'TASKS ({tasks.count()} tasks):\n' + '\n'.join(task_lines) + '\n\n'
        f'INSTRUCTION: {FIELD_INSTRUCTIONS[field]}'
    )

    # ── Call AI provider ──────────────────────────────────────────────────
    try:
        if anthropic_key:
            import anthropic as _anthropic_sdk
            client  = _anthropic_sdk.Anthropic(api_key=anthropic_key)
            message = client.messages.create(
                model='claude-3-5-haiku-20241022',
                max_tokens=1024,
                messages=[{'role': 'user', 'content': prompt}],
            )
            generated = message.content[0].text.strip()
            provider  = 'Anthropic'
        else:
            from openai import OpenAI as _OpenAI
            client   = _OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model='gpt-4o-mini',
                max_tokens=1024,
                messages=[{'role': 'user', 'content': prompt}],
            )
            generated = response.choices[0].message.content.strip()
            provider  = 'OpenAI'

        _audit(incident, request, 'UPDATE', 'AI Rephrase',
               f'AI-generated "{field_display}" via {provider}')
        return JsonResponse({'text': generated, 'field': field, 'provider': provider})

    except Exception as exc:
        return JsonResponse({'error': f'AI generation failed: {exc}'}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# THREAT INTEL
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def refresh_ioc_reputation(request, id, ioc_id):
    """POST — re-trigger threat intel lookup for an IoC."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    ioc = get_object_or_404(GenericIoc, pk=ioc_id, incident_id=id)
    if ioc.type in THREAT_INTEL_ELIGIBLE_TYPES:
        schedule_lookup(ioc.id)
        return JsonResponse({'status': 'queued'})
    return JsonResponse({'status': 'skipped', 'reason': 'type not eligible'})


# ─────────────────────────────────────────────────────────────────────────────
# WAR ROOM
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def warroom(request, id):
    incident = get_object_or_404(Incident, pk=id)
    try:
        user_role = UserRole.objects.get(user=request.user, incident=incident)
    except UserRole.DoesNotExist:
        if incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role='PUBLIC_VIEWER')
        else:
            return HttpResponseForbidden('You do not have permission to access this incident.')
    return render(request, 'incidents/warroom.html', {
        'incident': incident,
        'user': request.user,
        'current_user_role': user_role,
    })


@login_required(login_url='login')
@user_is_incident_responder_orpublic
def warroom_data(request, id):
    """GET — JSON snapshot for the war room auto-refresh."""
    incident = get_object_or_404(Incident, pk=id)

    # Timeline — last 10 events
    actions_qs = (
        incident.actions.all()
        .order_by('-observed_at', '-starting_time')
        .select_related('created_by')[:10]
    )
    timeline = []
    for a in actions_qs:
        ts = a.observed_at or a.starting_time
        timeline.append({
            'id': a.id,
            'type': a.type,
            'title': a.title,
            'description': a.description,
            'ts': ts.strftime('%d %b %H:%M') if ts else '',
            'created_by': a.created_by.username if a.created_by else '',
        })

    # Messages — last 10
    msgs_qs = (
        incident.messages.all()
        .order_by('-created_at')
        .select_related('sender')[:10]
    )
    messages_data = []
    for m in reversed(list(msgs_qs)):
        if m.is_bot:
            sender = 'System'
        elif m.sender:
            sender = m.sender.displayname or m.sender.username
        else:
            sender = 'System'
        messages_data.append({
            'id': m.id,
            'text': m.text,
            'sender': sender,
            'is_bot': m.is_bot,
            'ts': m.created_at.strftime('%H:%M'),
        })

    # KPIs
    total_iocs   = incident.genericiocs.count()
    tasks_all    = list(incident.tasks.values('id', 'status'))
    open_tasks   = sum(1 for t in tasks_all if t['status'] in ('OPEN', 'IN_PROGRESS'))
    total_tasks  = len(tasks_all)
    responders   = list(
        incident.incident_roles.select_related('user')
        .exclude(role='PUBLIC_VIEWER')
    )

    # Open tasks detail
    open_tasks_qs = (
        incident.tasks.filter(status__in=('OPEN', 'IN_PROGRESS'))
        .select_related('assignee')
        .order_by('priority', 'created_at')[:20]
    )
    open_tasks_list = [
        {
            'id': t.id,
            'title': t.title,
            'status': t.status,
            'priority': t.priority,
            'assignee': t.assignee.username if t.assignee else None,
        }
        for t in open_tasks_qs
    ]

    # Critical IoCs (reputation malicious)
    critical_iocs = [
        {
            'id': ioc.id,
            'type': ioc.type,
            'value': ioc.value,
            'reputation': ioc.reputation,
        }
        for ioc in incident.genericiocs.all()
        if ioc.reputation and ioc.reputation.get('status') == 'malicious'
    ]

    # Responders list
    responders_list = [
        {
            'username': ur.user.username,
            'display': ur.user.displayname or ur.user.username,
            'role': ur.role,
            'display_role': ur.display_role or ur.get_role_display(),
        }
        for ur in responders
    ]

    return JsonResponse({
        'incident': {
            'id': incident.id,
            'name': incident.name,
            'severity': incident.severity,
            'status': incident.status,
            'starting_time': incident.starting_time.isoformat() if incident.starting_time else None,
        },
        'timeline': timeline,
        'messages': messages_data,
        'kpis': {
            'total_iocs': total_iocs,
            'open_tasks': open_tasks,
            'total_tasks': total_tasks,
            'responders': len(responders),
        },
        'open_tasks': open_tasks_list,
        'critical_iocs': critical_iocs,
        'responders': responders_list,
    })


# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM SETTINGS (admin-only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def save_platform_settings(request):
    """
    POST  /api/platform-settings/
    Admin-only. Saves platform-wide AI provider / API key.
    Body: { "ai_provider": "ANTHROPIC"|"OPENAI"|"NONE", "ai_api_key": "..." }
    Leave ai_api_key empty (or omit) to keep the existing key unchanged.
    """
    if not request.user.is_admin:
        return JsonResponse({'error': 'Admin access required.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    valid_providers = ('NONE', 'ANTHROPIC', 'OPENAI')
    provider = body.get('ai_provider', '').upper()
    if provider not in valid_providers:
        return JsonResponse({'error': f'Invalid provider. Must be one of: {valid_providers}'}, status=400)

    ps = PlatformSettings.get()
    ps.ai_provider = provider

    new_key = body.get('ai_api_key', '').strip()
    if new_key:                # only overwrite if a value was submitted
        ps.ai_api_key = new_key

    if provider == 'NONE':     # if disabled, clear the stored key too
        ps.ai_api_key = ''

    ps.save()
    return JsonResponse({
        'status':      'saved',
        'ai_provider': ps.ai_provider,
        'key_set':     bool(ps.ai_api_key),
    })


# ─────────────────────────────────────────────────────────────────────────────
# CTI PROVIDERS (admin-only management)
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def save_cti_provider(request):
    """
    POST /api/cti-providers/
    Upsert (create or update) a CTI provider for the platform.
    Body: { name, api_key, base_url, enabled }
    Leaving api_key blank keeps the existing key.
    """
    if not request.user.is_admin:
        return JsonResponse({'error': 'Admin access required.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    name = body.get('name', '').upper()
    valid = [c[0] for c in CtiProvider.PROVIDER_CHOICES]
    if name not in valid:
        return JsonResponse({'error': f'Unknown provider. Valid: {valid}'}, status=400)

    provider, _ = CtiProvider.objects.get_or_create(name=name)

    new_key = body.get('api_key', '').strip()
    if new_key:
        provider.api_key = new_key

    base_url = body.get('base_url', '').strip()
    if base_url:
        provider.base_url = base_url

    if 'enabled' in body:
        provider.enabled = bool(body['enabled'])

    provider.save()
    return JsonResponse({
        'status':  'saved',
        'name':    provider.name,
        'enabled': provider.enabled,
        'key_set': bool(provider.api_key),
    })


@login_required(login_url='login')
def delete_cti_provider(request):
    """POST /api/cti-providers/delete/  Body: { name }"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Admin access required.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    name = body.get('name', '').upper()
    CtiProvider.objects.filter(name=name).delete()
    return JsonResponse({'status': 'deleted', 'name': name})


# ─────────────────────────────────────────────────────────────────────────────
# IOC REPUTATION LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

def _cti_supported_types():
    """Return the set of GenericIoc.type values that have at least one enabled CTI integration."""
    types = set()
    if CtiProvider.objects.filter(name='VIRUSTOTAL', enabled=True).exclude(api_key='').exists():
        types.update({'IPADRESS', 'DOMAIN', 'HASH', 'FILE', 'URL'})
    # Future: AbuseIPDB / Shodan → 'IPADRESS'
    return types


def _vt_lookup(ioc, api_key):
    """Query VirusTotal v3 for a GenericIoc. Returns a result dict or None."""
    import httpx, base64

    base    = 'https://www.virustotal.com/api/v3'
    headers = {'x-apikey': api_key}
    itype   = ioc.type
    value   = ioc.value.strip()

    if itype == 'IPADRESS':
        endpoint = f'{base}/ip_addresses/{value}'
        gui_path = f'ip-address/{value}'
    elif itype == 'DOMAIN':
        endpoint = f'{base}/domains/{value}'
        gui_path = f'domain/{value}'
    elif itype in ('HASH', 'FILE'):
        endpoint = f'{base}/files/{value}'
        gui_path = f'file/{value}'
    elif itype == 'URL':
        url_id   = base64.urlsafe_b64encode(value.encode()).decode().rstrip('=')
        endpoint = f'{base}/urls/{url_id}'
        gui_path = f'url/{url_id}'
    else:
        return None   # type not supported by VT

    try:
        resp = httpx.get(endpoint, headers=headers, timeout=10)
    except Exception as exc:
        return {'provider': 'VirusTotal', 'verdict': 'error', 'detail': str(exc), 'link': None}

    if resp.status_code == 404:
        return {'provider': 'VirusTotal', 'verdict': 'unknown',
                'detail': 'Not found in VirusTotal database', 'link': None}
    if resp.status_code == 401:
        return {'provider': 'VirusTotal', 'verdict': 'error',
                'detail': 'Invalid API key', 'link': None}
    if resp.status_code != 200:
        return {'provider': 'VirusTotal', 'verdict': 'error',
                'detail': f'HTTP {resp.status_code}', 'link': None}

    attrs      = resp.json().get('data', {}).get('attributes', {})
    stats      = attrs.get('last_analysis_stats', {})
    malicious  = stats.get('malicious',  0)
    suspicious = stats.get('suspicious', 0)
    harmless   = stats.get('harmless',   0)
    undetected = stats.get('undetected', 0)
    total      = sum(stats.values())

    if malicious > 0:
        verdict = 'malicious'
    elif suspicious > 0:
        verdict = 'suspicious'
    elif total == 0:
        verdict = 'unknown'
    else:
        verdict = 'clean'

    result = {
        'provider':   'VirusTotal',
        'verdict':    verdict,
        'score':      f'{malicious}/{total}',
        'malicious':  malicious,
        'suspicious': suspicious,
        'harmless':   harmless,
        'undetected': undetected,
        'total':      total,
        'link':       f'https://www.virustotal.com/gui/{gui_path}',
    }
    # Extra contextual fields (IP/domain/file)
    for field in ('country', 'asn', 'as_owner', 'meaningful_name', 'type_description',
                  'network', 'last_analysis_date'):
        val = attrs.get(field)
        if val is not None:
            result[field] = val
    return result


@login_required(login_url='login')
@user_is_incident_responder_orpublic
def ioc_reputation(request, id, ioc_id):
    """
    GET /api/incident/<id>/ioc/<ioc_id>/reputation/
    Query all enabled CTI providers, persist results, return JSON for the UI.
    Response: { status: 'ok', reputation: { status, checked_at, vt: {...} } }
    """
    from django.utils import timezone as tz
    incident = get_object_or_404(Incident, pk=id)
    ioc      = get_object_or_404(GenericIoc, pk=ioc_id, incident=incident)

    providers = CtiProvider.objects.filter(enabled=True).exclude(api_key='')
    if not providers.exists():
        return JsonResponse({'status': 'error', 'error': 'No CTI providers configured.'}, status=503)

    raw_results = []
    for p in providers:
        if p.name == 'VIRUSTOTAL':
            r = _vt_lookup(ioc, p.api_key)
            if r:
                raw_results.append(r)
        # Future providers: ABUSEIPDB, SHODAN, OTXALIENVAULT, MISP …

    if not raw_results:
        return JsonResponse({
            'status': 'error',
            'error':  'No configured provider supports this IoC type.',
        }, status=422)

    # Determine worst verdict across all providers
    SEVERITY = {'malicious': 3, 'suspicious': 2, 'unknown': 1, 'clean': 0, 'error': -1}
    worst_verdict = max(
        (r.get('verdict', 'error') for r in raw_results),
        key=lambda v: SEVERITY.get(v, -1),
    )
    # Map 'error' → 'unknown' for display
    status = worst_verdict if worst_verdict in SEVERITY and worst_verdict != 'error' else 'unknown'

    # Build reputation object in the shape renderRepModal expects
    reputation = {
        'status':     status,
        'checked_at': tz.now().isoformat(),
    }
    for r in raw_results:
        if r.get('provider') == 'VirusTotal':
            reputation['vt'] = {k: v for k, v in r.items()
                                if k not in ('provider', 'verdict', 'score')}

    # Persist to the ioc record
    ioc.reputation = reputation
    ioc.save(update_fields=['reputation'])
    _audit(incident, request, 'UPDATE', 'IoC', f'Reputation checked for IoC #{ioc.id} ({ioc.value}) — verdict: {status}')

    return JsonResponse({'status': 'ok', 'reputation': reputation})
