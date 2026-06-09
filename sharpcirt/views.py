from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.forms.models import model_to_dict
from sharpcirt.models import Incident, Note, User, Message, GenericIoc, UserRole, Task, Action, Impact
from . import models
from .utils import verify_permissions, user_is_incident_responder_orpublic, user_is_incident_responder, update_first_actions, get_incidents_by_day_and_severity
from django.contrib import messages
import json
import random
from datetime import timedelta, datetime
from django.utils import timezone
from .models import Incident
from django.template.loader import render_to_string
from crud.settings import BASE_DIR
from xhtml2pdf import pisa
from io import BytesIO
import os
from django.http import FileResponse
from collections import Counter, defaultdict

@login_required(login_url='login')
def index(request):
    # Get incidents where the user has a role OR the incident is public
    user_roles = UserRole.objects.filter(user=request.user).select_related('incident')
    user_incidents = Incident.objects.filter(
        id__in=[user_role.incident.id for user_role in user_roles]
    )
    public_incidents = Incident.objects.filter(is_public=True)

    # Combine both sets of incidents
    incidents = user_incidents | public_incidents
    return render(request, 'index.html', {
        'incidents': incidents,
        'user': request.user,
    })

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
        total_time_to_detect += incident.time_to_detect.total_seconds()
        total_time_to_respond += incident.time_to_respond.total_seconds()
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


    incidents = user_incidents | public_incidents


    
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
        try:
            username = request.POST['username']
            password = request.POST['password']
            user = User.objects.get(username=username)
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                next_url = request.GET.get('next') or '/'
                return redirect(next_url)
            else:
                return render(request, 'login.html', {'error': 'Invalid credentials'})
        except User.DoesNotExist:
            return render(request, 'login.html', {'error': 'User does not exists'})
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
 
    return render(request, 'profile.html', {
        'user': request.user
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

    return render(request, 'incidents/overview.html', {
        'incident': incident,
        'user': request.user,
        'current_user_role': user_role
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
    return render(request,'incidents/notes.html', {'incident': incident, 'user': request.user, 'current_user_role': user_role})

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
                text=f"{request.user.username} created note: {new_note.name}"
            )
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
            note.delete()
            return JsonResponse({"status": "success", "message": "Note deleted successfully", "note_id": note_id })
        except Note.DoesNotExist:
            return JsonResponse({'error': 'Note not found'}, status=404)        

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def responders(request, id):
    # Query all users
    try:
        incident = Incident.objects.get(pk=id)
        user_roles = UserRole.objects.filter(incident=incident)
        user_role = UserRole.objects.get(user=request.user, incident=incident)
    except UserRole.DoesNotExist:
        if incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")
    except Incident.DoesNotExist:
        my_object = None
    return render(request, 'incidents/responders.html', {'incident': incident, 'user': request.user, 'current_user_role': user_role})
    # return render(request,'incidents/responders.html')

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def report(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        user_role = UserRole.objects.get(user=request.user, incident=incident)
        
        templates_dir = os.path.join(BASE_DIR, 'sharpcirt', 'templates', 'report-templates')
        templates = []
        if os.path.exists(templates_dir):
            for template_file in os.listdir(templates_dir):
                if template_file.endswith('.html'):
                    template_type = 'html'
                elif template_file.endswith('.md'):
                    template_type = 'markdown'
                else:
                    continue
                templates.append({
                    'name': template_file, 
                    'type': template_type
                })

    except UserRole.DoesNotExist:
        if incident.is_public:
            user_role = UserRole(user=request.user, incident=incident, role="PUBLIC_VIEWER")
        else:
            return HttpResponseForbidden("You do not have permission to access this incident.")
    except Incident.DoesNotExist:
        my_object = None
    return render(request, 'incidents/report.html', {'incident': incident, 'user': request.user, 'current_user_role': user_role, 'templates': templates})
    # return render(request,'incidents/responders.html')

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def iocs(request, id):
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
    return render(request,'incidents/evidence.html', {'incident': incident, 'user': request.user, 'current_user_role': user_role})

@login_required(login_url='login')
@user_is_incident_responder_orpublic
def timeline(request, id):
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
        prefs['theme'] = request.POST.get('theme', 'light_mode')
        prefs['default_severity'] = request.POST.get('default_severity', 'MEDIUM')
        prefs['notify_assignment'] = 'notify_assignment' in request.POST
        prefs['notify_mention'] = 'notify_mention' in request.POST
        prefs['chart_period'] = request.POST.get('chart_period', '30d')
        user.preferences = prefs
        user.light_mode = prefs['theme']
        user.save()
        return redirect('/settings?saved=1')

    return render(request, 'settings.html', {
        'user': user,
        'prefs': prefs,
    })


@login_required(login_url='login')
def download_incident_json(request, id):
    try:
        incident = Incident.objects.get(pk=id)
        data = model_to_dict(incident)
        for key, value in data.items():
            if hasattr(value, 'isoformat'):
                data[key] = value.isoformat()
            elif isinstance(value, timedelta):
                data[key] = str(value)
        
        data['users'] = [ { 'id': userrole.user.id, 'username': userrole.user.username,'email': userrole.user.email, 'role': userrole.role} for userrole in UserRole.objects.filter(incident=incident)]

        response = HttpResponse(
            json.dumps(data, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="incident_{incident.id}.json"'
        return response
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

@login_required(login_url='login')
@user_is_incident_responder
def download_incident_markdown(request, id):
    try:
        incident = Incident.objects.get(pk=id)
    
        
        # Render the markdown template with the context
        markdown_content = render_to_string(
            'report-templates/report_template_1.md',
            {'incident': incident}
        )
        
        # Create a downloadable response
        response = HttpResponse(markdown_content, content_type='text/markdown')
        response['Content-Disposition'] = f'attachment; filename="INCIDENT_REPORT_{incident.id}.md"'
    
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)

    return response

@login_required(login_url='login')  
@user_is_incident_responder
def download_incident_pdf(request, id):
    try:
        # Fetch the incident by ID
        incident = Incident.objects.get(pk=id)
        

        # Render the HTML template with the incident data
        template_name = request.POST.get('template')

        html_content = render_to_string(f'report-templates/{template_name}', {'incident': incident})

        # Path to wkhtmltopdf executable
        wkhtmltopdf_path = "C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)

        # Configure wkhtmltopdf options (optional)
        pdf_options = {
            'page-size': 'A4',
            'encoding': 'UTF-8',
            'no-outline': None,
            'footer-left': f'{datetime.now().strftime("%d.%m.%Y")} | OpenCIRT Incident Report | TLP:GREEN' ,  # Custom footer content
            'footer-right': f'{incident.name.upper()} | [page] of [topage]',  # Custom footer content
            'footer-font-size': 10,
            'footer-font-name': 'TradeGothic',
            'footer-spacing': 5,
        }

        # Generate the PDF as a byte string
        pdf_content = pdfkit.from_string(html_content, output_path=False, options=pdf_options, configuration=config)

        # Return the PDF as an HTTP response for download
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{template_name}_incident_{id}.pdf"'
        return response

    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Incident not found'}, status=404)
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

    
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
            if msg.sender:
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
            Message.objects.create(
                incident=incident,
                sender=request.user,
                text=f"{request.user.username} added a new {ioc.get_type_display()} IoC: {ioc.value}"
            )
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
            action_tags = data.get('tag', '')
            action_observed_at = data.get('observed_at')
            action_starting_time = data.get('starting_time')
            action_ending_time = data.get('ending_time')

            action = Action.objects.create(
                incident = incident,
                title = action_title,
                description = action_description,
                type = action_type,
                created_by = request.user
            )
            if action_observed_at: 
                action.observed_at = action_observed_at
                action.save()
            elif action_starting_time and action_ending_time:
                action.starting_time = action_starting_time
                action.ending_time = action_ending_time
                action.save()
            else:
                return JsonResponse({'error': 'Invalid time sent'}, status=400)
            
            if action_tags:
                action.tags.set(action_tags)
                action.save()
            if action_iocs:
                action.iocs.set(action_iocs)
                action.save()
            update_first_actions(incident=incident)
            Message.objects.create(
                incident=incident,
                sender=request.user,
                text=f"{request.user.username} added timeline action: {action.title}"
            )
            return JsonResponse({"status": "success", "message": "Action added successfully"})
        else:
            return JsonResponse({'error': 'Invalid method'}, status=400)
    except Incident.DoesNotExist:
        return JsonResponse({'error': 'Invalid incident'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Other error :{e}'}, status=400)
        

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

            action.delete()
            update_first_actions(incident=action.incident)
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
                text=f"{request.user.username} created task: {task.title}"
            )
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

            task.delete()

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

            ioc.delete()
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
        return JsonResponse({"success": f"Role of {user.username} updated to {new_role}"}, status=200)

    if display_role:
        user_role.display_role = display_role
        user_role.save()
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


            userrole.delete()
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

            # Save the updated incident
            incident.save()

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

            # Save the updated user profile
            user.save()
            messages.success(request, "Profile updated successfully!")

            return render(request, 'profile.html')

        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
