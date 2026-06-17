from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from django.http import HttpRequest  # Import HttpRequest
from .choices_processor import choices_context

choices = choices_context(HttpRequest())
    
class User(AbstractUser):
    is_admin = models.BooleanField(default=False)
    first_connection_time = models.DateTimeField(auto_now_add=True)
    last_connection_time = models.DateTimeField(null=True, blank=True)
    displayname = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg')
    light_mode = models.CharField(max_length=15, default='light_mode')
    preferences = models.JSONField(default=dict, blank=True)
    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_groups',
        blank=True,
        help_text='The groups this user belongs to.'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.'
    )


class IncidentCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#796FA7')

    def __str__(self):
        return self.name


class Incident(models.Model):
    id = models.AutoField(primary_key=True)  # Auto-generated primary key
    name = models.CharField(max_length=255)  # Name of the incident
    description = models.TextField() 
    status = models.CharField(
        max_length=20, 
        choices=choices["INCIDENT_STATUS_CHOICES"],
        default='OPEN'
    )  # Status of the incident
    severity = models.CharField(
        max_length=10, 
        choices=choices["INCIDENT_SEVERITY_CHOICES"], 
        default='MEDIUM'
    )  # Severity level of the incident
    executive_summary = models.TextField()
    # business_impact = models.TextField(default='SOME STRING')
    # systems_impact = models.TextField(default='SOME STRING')
    lessons_learned = models.TextField(default='')
    technical_details = models.TextField(default='')
    external_reference = models.CharField(max_length=255, blank=True, default='')
    export_include_timeline = models.BooleanField(default=True)
    export_include_iocs = models.BooleanField(default=True)
    export_include_attachements = models.BooleanField(default=True)
    starting_time = models.DateTimeField()
    ending_time = models.DateTimeField()
    duration = models.DurationField()
    time_to_detect = models.DurationField()
    time_to_respond = models.DurationField()
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for creation
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='incident_created')
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp for updates
    is_public = models.BooleanField(default=False)
    iocs_shared = models.BooleanField(default=False)
    invite_code = models.CharField(max_length=6, blank=True, default='')
    TLP_CHOICES = [('CLEAR','CLEAR'),('GREEN','GREEN'),('AMBER','AMBER'),('RED','RED')]
    tlp = models.CharField(max_length=10, choices=TLP_CHOICES, default='CLEAR')
    ai_rephrase_enabled = models.BooleanField(default=False)
    categories = models.ManyToManyField(IncidentCategory, blank=True, related_name='incidents')

    def __str__(self):
        return self.name
    
    def sorted_actions(self):
        return self.actions.all().order_by('observed_at')  # Sort in ascending order


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='incident_roles')
    role = models.CharField(max_length=20, choices=choices['USER_ROLES_CHOICES'])
    display_role = models.CharField(max_length=30,default='')
    
    class Meta:
        unique_together = ('user', 'incident')
    
    def __str__(self):
        return f'{self.user.username} - {self.role} in {self.incident.name}'

class Message(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages_sent')
    text = models.TextField()
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='messages', null=True,)
    is_bot = models.BooleanField(default=False)
    link = models.CharField(max_length=255, null=True, blank=True)

class SharedFile(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_files')
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='shared_files')
    file = models.FileField(upload_to='incident_files/')
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)

class Tag(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tags_created')
    name = models.CharField(max_length=30, default='')
    color = models.CharField(max_length=7, default='#000000')
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='tags')

class Ioc(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ioc_created')
    tag = models.TextField()
    status = models.CharField(max_length=30, choices=choices['GENERIC_IOC_STATUS_CHOICES'], default='SAFE')
    description = models.TextField()
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='iocs')
    tags = models.ManyToManyField(Tag, related_name='ioc_tags')

    class Meta:
        abstract = True


class GenericIoc(Ioc):
    value = models.TextField()
    type = models.CharField(max_length=20, choices=choices["GENERIC_IOC_TYPE_CHOICES"], default='OTHER')
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='genericiocs')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='genericioc_created')
    reputation = models.JSONField(null=True, blank=True)

    @property
    def reputation_summary(self):
        rep = self.reputation
        if not rep:
            return 'No threat intel data'
        parts = []
        vt = rep.get('vt')
        if vt:
            parts.append(f"VT: {vt.get('malicious', 0)} malicious, {vt.get('suspicious', 0)} suspicious, {vt.get('harmless', 0)} harmless")
        abuse = rep.get('abuseipdb')
        if abuse:
            parts.append(f"AbuseIPDB: score {abuse.get('score', 0)}% ({abuse.get('country', '?')}, {abuse.get('reports', 0)} reports)")
        return ' | '.join(parts) if parts else f"Status: {rep.get('status', 'unknown')}"

class Action(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    observed_at = models.DateTimeField(null=True)
    starting_time = models.DateTimeField(null=True)
    ending_time = models.DateTimeField(null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='actions_created')
    title = models.CharField(max_length=200, default='')
    description = models.TextField(default='')
    type = models.CharField(max_length=20, choices=choices["GENERIC_ACTION_CHOICES"], default='OTHER')
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='actions')
    iocs = models.ManyToManyField(GenericIoc, related_name='actions')
    is_first_action_this_day = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, related_name='action_tags')


class Note(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='note_created')
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='notes')
    name = models.CharField(max_length=50)
    text = models.TextField()


class Task(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='task_created')
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=50)
    external_reference = models.CharField(max_length=50)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=choices["TASK_STATUS_CHOICES"], default='OPEN')
    priority = models.CharField(max_length=20, choices=choices["TASK_PRIORITY_CHOICES"], default='MEDIUM')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='task_assignee')
    tags = models.ManyToManyField(Tag, related_name='tags_task')


class Impact(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='impact_created')
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='impacts')
    title = models.CharField(max_length=50)
    external_reference = models.CharField(max_length=50)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=choices["IMPACT_STATUS_CHOICES"], default='IN_PROGRESS')
    severity = models.CharField(max_length=20, choices=choices["IMPACT_SEVERITY_CHOICES"], default='MEDIUM')
    type = models.CharField(max_length=20, choices=choices["IMPACT_TYPES_CHOICES"], default='N/A')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='impact_assignee')
    tags = models.ManyToManyField(Tag, related_name='tags_impact')
    action = models.ManyToManyField(Action, related_name='impacts')
    starting_time = models.DateTimeField(null=True)
    ending_time = models.DateTimeField(null=True)
    duration = models.DurationField(null=True)


class CtiProvider(models.Model):
    """One row per enabled threat-intelligence source."""
    PROVIDER_CHOICES = [
        ('VIRUSTOTAL',    'VirusTotal'),
        ('ABUSEIPDB',     'AbuseIPDB'),
        ('SHODAN',        'Shodan'),
        ('OTXALIENVAULT', 'OTX AlienVault'),
        ('MISP',          'MISP'),
    ]
    name     = models.CharField(max_length=30, choices=PROVIDER_CHOICES, unique=True)
    api_key  = models.CharField(max_length=512, blank=True, default='')
    base_url = models.CharField(max_length=255, blank=True, default='',
                                help_text='Required for self-hosted sources (e.g. MISP).')
    enabled  = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.get_name_display()} ({"on" if self.enabled else "off"})'


class PlatformSettings(models.Model):
    """Singleton — platform-wide configuration. Always use PlatformSettings.get()."""
    AI_PROVIDER_CHOICES = [
        ('NONE',      'Disabled'),
        ('ANTHROPIC', 'Anthropic (Claude)'),
        ('OPENAI',    'OpenAI (GPT)'),
    ]
    ai_provider = models.CharField(max_length=20, choices=AI_PROVIDER_CHOICES, default='NONE')
    ai_api_key  = models.CharField(max_length=512, blank=True, default='')

    class Meta:
        verbose_name = 'Platform Settings'

    @classmethod
    def get(cls):
        """Return the singleton row, creating it with defaults if absent."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'Platform Settings (AI: {self.ai_provider})'


class AuditLog(models.Model):
    """Records every significant action performed within an incident."""
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('EXPORT', 'Export'),
        ('ACCESS', 'Access'),
    ]
    incident    = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='audit_logs')
    timestamp   = models.DateTimeField(auto_now_add=True)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    ip_address  = models.CharField(max_length=45, blank=True, default='')
    action      = models.CharField(max_length=10, choices=ACTION_CHOICES)
    object_type = models.CharField(max_length=50)   # IoC, Task, Note, File, Timeline, Settings…
    description = models.TextField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.action} {self.object_type} by {self.user}"
