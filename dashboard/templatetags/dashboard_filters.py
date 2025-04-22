from django import template
from dashboard.models import Settings
from datetime import datetime, timedelta
from django.template.defaultfilters import floatformat

register = template.Library()

def get_settings():
    """Helper function to get current settings"""
    settings, _ = Settings.objects.get_or_create(pk=1)
    return settings

@register.filter
def less_than(value, arg):
    """Check if value is less than arg"""
    try:
        return float(value) < float(arg)
    except (ValueError, TypeError):
        return False

@register.filter
def greater_than(value, arg):
    try:
        return float(value) > float(arg)
    except (ValueError, TypeError):
        return False

@register.filter
def is_abnormal_heart_rate(value):
    """Check if heart rate is abnormal"""
    try:
        value = float(value)
        settings = get_settings()
        return value < settings.heart_rate_min or value > settings.heart_rate_max
    except (ValueError, TypeError):
        return False

@register.filter
def is_low_spo2(value):
    try:
        value = float(value)
        settings = get_settings()
        return value < settings.spo2_min
    except (ValueError, TypeError):
        return False

@register.filter
def is_abnormal_temperature(value):
    """Check if temperature is abnormal"""
    try:
        value = float(value)
        settings = get_settings()
        return value < settings.temperature_min or value > settings.temperature_max
    except (ValueError, TypeError):
        return False

@register.filter
def add_hours(value, hours):
    """Add hours to a datetime value"""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value + timedelta(hours=hours)
    return value

@register.filter
def get_range(value):
    """Generate a range of numbers from 1 to value"""
    return range(1, int(value) + 1) 