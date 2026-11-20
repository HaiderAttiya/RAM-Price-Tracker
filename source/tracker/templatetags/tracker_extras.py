"""Small template helpers used across the site."""

from decimal import Decimal, InvalidOperation

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def money(value):
    """Format a price in Bahraini dinars."""
    if value is None or value == "":
        return "-"
    try:
        return f"{settings.CURRENCY_SYMBOL}{Decimal(value):,.3f}"
    except (InvalidOperation, TypeError, ValueError):
        return str(value)


@register.filter
def percent(value):
    """Decimal -> '12.5%' (one decimal place)."""
    if value is None:
        return "-"
    return f"{Decimal(value):.1f}%"


@register.filter
def abs_value(value):
    try:
        return abs(value)
    except TypeError:
        return value


@register.simple_tag(takes_context=True)
def nav_active(context, *url_names):
    """Return 'active' when the current URL name is one of url_names (for the navbar)."""
    match = getattr(context["request"], "resolver_match", None)
    return "active" if match and match.url_name in url_names else ""
