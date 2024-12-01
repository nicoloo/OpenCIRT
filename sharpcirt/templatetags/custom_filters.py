from django import template
from ..choices_processor import choices_context
from django.http import HttpRequest
import datetime

register = template.Library()

choices = choices_context(HttpRequest())

@register.filter
def duration_format(value):
    if isinstance(value, datetime.timedelta):
        total_seconds = int(value.total_seconds())
        days, remainder = divmod(total_seconds, 86400)  # 86400 seconds in a day
        weeks, days = divmod(days, 7)  # 7 days in a week
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        duration_parts = []
        if weeks > 0:
            duration_parts.append(f"{weeks}w")
        if days > 0:
            duration_parts.append(f"{days}d")
        if hours > 0:
            duration_parts.append(f"{hours}h")
        if minutes > 0:
            duration_parts.append(f"{minutes}min")
        if seconds > 0 and not (weeks or days or hours or minutes):  # Include seconds if it's the only part
            duration_parts.append(f"{seconds}sec")

        return ' '.join(duration_parts) if duration_parts else '0sec'
    
    return value


@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def pluck(value, arg):
    """Extracts a specific attribute from a list of objects."""
    return [getattr(item, arg) for item in value]


@register.filter
def label(value,c):
    for key,label in choices[c]:
        if value == key:
            return label

    return "toto"
    