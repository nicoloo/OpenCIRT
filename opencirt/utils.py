from functools import wraps
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse, HttpRequest
from .models import UserRole, Incident
from django.db.models import Min, Max
from collections import defaultdict
from datetime import timedelta, datetime
from .choices_processor import choices_context

choices = choices_context(HttpRequest()) # Dummy request to initialize  choices

def _platform_role(user):
    """Return the user's platform_role string, or '' if the field doesn't exist yet."""
    return getattr(user, 'platform_role', '') or ''


def verify_permissions(required_role: list):
    """
    Decorator to verify if the logged-in user has the required role for a specific incident.
    Expects 'id' to be present in kwargs or args.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'User is not authenticated'}, status=401)

            # Superusers and SOC Leads have INCIDENT_LEAD-equivalent access everywhere.
            pr = _platform_role(request.user)
            if request.user.is_superuser or pr == 'SOC_LEAD':
                return view_func(request, *args, **kwargs)

            # SOC Analysts have RESPONDER-equivalent access.
            if pr == 'SOC_ANALYST':
                if 'RESPONDER' in required_role or 'INCIDENT_LEAD' not in required_role:
                    return view_func(request, *args, **kwargs)
                return JsonResponse({'error': 'Permission denied'}, status=403)

            incident_id = kwargs.get('id')
            if not incident_id and args:
                incident_id = args[0]

            if not incident_id:
                return JsonResponse({'error': 'Incident ID is required for permission verification'}, status=400)

            try:
                user_role = UserRole.objects.get(user=request.user, incident_id=incident_id)
                if user_role.role not in required_role:
                    return JsonResponse({'error': 'Permission denied'}, status=403)
            except UserRole.DoesNotExist:
                return JsonResponse({'error': 'Permission denied - no role assigned for this incident'}, status=403)

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator


def user_is_incident_responder_orpublic(view_func):
    @wraps(view_func)
    def wrapper(request, id, *args, **kwargs):
        incident = get_object_or_404(Incident, id=id)
        if request.user.is_authenticated:
            pr = _platform_role(request.user)
            if request.user.is_superuser or pr in ('SOC_ANALYST', 'SOC_LEAD'):
                return view_func(request, id, *args, **kwargs)
        if incident.is_public:
            return view_func(request, id, *args, **kwargs)
        is_responder = UserRole.objects.filter(incident_id=incident.id, user=request.user).exists()
        if not is_responder:
            if request.path.startswith('/api/'):
                return JsonResponse({'error': 'You do not have permission to access this incident.'}, status=403)
            return render(request, '403.html', {
                'reason': 'You are not a member of this incident.',
                'incident': incident,
            }, status=403)
        return view_func(request, id, *args, **kwargs)
    return wrapper


def user_is_incident_responder(view_func):
    @wraps(view_func)
    def wrapper(request, id, *args, **kwargs):
        if request.user.is_authenticated:
            pr = _platform_role(request.user)
            if request.user.is_superuser or pr in ('SOC_ANALYST', 'SOC_LEAD'):
                return view_func(request, id, *args, **kwargs)
        is_responder = UserRole.objects.filter(incident_id=id, user=request.user).exists()
        if not is_responder:
            incident = get_object_or_404(Incident, id=id)
            return render(request, '403.html', {
                'reason': 'You are not a member of this incident.',
                'incident': incident,
            }, status=403)
        return view_func(request, id, *args, **kwargs)
    return wrapper



def sync_incident_times(incident: Incident) -> None:
    """Set incident.starting_time to the earliest action time.
    When the incident is CLOSED, also set ending_time to the latest action time.
    """
    times = []
    for a in incident.actions.all():
        t = a.observed_at or a.starting_time
        if t:
            times.append(t)
    if not times:
        return
    fields_to_update = ['starting_time']
    incident.starting_time = min(times)
    if incident.status == 'CLOSED':
        incident.ending_time = max(times)
        fields_to_update.append('ending_time')
    incident.save(update_fields=fields_to_update)


def update_first_actions(incident: Incident):
    actions = incident.actions.all().order_by('observed_at', 'starting_time')  # Sort by observed_at or starting_time
    action_dates = {}

    for action in actions:
        # Determine the relevant datetime value
        action_time = action.observed_at or action.starting_time
        if not action_time:
            continue
        
        # Extract the date part of the datetime
        action_date = action_time.date()

        # Check if this is the first action for the day
        if action_date not in action_dates:
            action_dates[action_date] = action
            action.is_first_action_this_day = True
        else:
            action.is_first_action_this_day = False

        # Save the action with updated value
        action.save()    



    
def get_incidents_by_day_and_severity():
    # Get the range of dates based on the incidents
    incidents = Incident.objects.all()  # Query all incidents from the database
    
    # Get the earliest and latest incident dates
    date_range = incidents.aggregate(Min('created_at'), Max('created_at'))
    
    # Handle case when there are no incidents
    if date_range['created_at__min'] is None or date_range['created_at__max'] is None:
        return {}
    
    start_date = date_range['created_at__min'].date()
    end_date = date_range['created_at__max'].date()

    # Extract severity choices (just the keys)
    severities = [severity[0] for severity in choices["INCIDENT_SEVERITY_CHOICES"]]

    # Initialize the defaultdict to hold the data
    events_per_day = defaultdict(lambda: {severity: 0 for severity in severities})

    # Process each incident
    for incident in incidents:
        date_str = incident.created_at.strftime('%Y-%m-%d')
        severity = incident.severity.upper()  # Ensure uniform casing

        # Check if severity is valid (in case of bad data)
        if severity in events_per_day[date_str]:
            events_per_day[date_str][severity] += 1

    # Ensure all days within the range have an entry (with 0 for missing days)
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        if date_str not in events_per_day:
            events_per_day[date_str] = {severity: 0 for severity in severities}
        current_date += timedelta(days=1)
    return dict(events_per_day)
