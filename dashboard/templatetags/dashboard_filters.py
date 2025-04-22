from django import template
from dashboard.models import Settings

register = template.Library()

def get_settings():
    """Helper function to get current settings"""
    settings, _ = Settings.objects.get_or_create(pk=1)
    return settings

@register.filter
def less_than(value, arg):
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
    try:
        value = float(value)
        settings = get_settings()
        return value < settings.temperature_min or value > settings.temperature_max
    except (ValueError, TypeError):
        return False 