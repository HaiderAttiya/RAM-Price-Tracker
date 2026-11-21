from django.conf import settings


def site_settings(request):
    return {
        "CURRENCY_SYMBOL": settings.CURRENCY_SYMBOL,
        "DEAL_THRESHOLD_PERCENT": settings.DEAL_THRESHOLD_PERCENT,
        "DEAL_WINDOW_DAYS": settings.DEAL_WINDOW_DAYS,
        "DEAL_MIN_RECORDS": settings.DEAL_MIN_RECORDS,
    }
