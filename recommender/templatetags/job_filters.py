"""
Custom Django template filters for the JobMatch project.

Usage in templates:
    {% load job_filters %}
    {{ "Python, Django, SQL"|split:"," }}
    {{ "  python  "|trim }}
"""
from django import template

register = template.Library()


@register.filter(name="split")
def split_filter(value: str, delimiter: str = ",") -> list[str]:
    """
    Split a string by a delimiter and return a list.

    Example:
        {{ profile.skills|split:"," }}
    """
    if not value:
        return []
    return [item.strip() for item in str(value).split(delimiter) if item.strip()]


@register.filter(name="trim")
def trim_filter(value: str) -> str:
    """
    Strip leading/trailing whitespace from a string.

    Example:
        {{ skill|trim }}
    """
    return str(value).strip() if value else ""
