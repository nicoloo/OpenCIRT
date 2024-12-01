# Incident Report: {{ incident.name }}

**Description:**  
{{ incident.description }}

**Created At:** {{ incident.created_at }}
**Updated At:** {{ incident.updated_at }}

## Responders
{% for user in incident.users.all %}
- **{{ responder.username }}** ({{ user.email }})
{% endfor %}

## Additional Details
- Status: {{ incident.status }}
- Priority: {{ incident.severity }}
