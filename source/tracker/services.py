

from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db.models import Avg, Count, Min
from django.utils import timezone

from .models import PriceRecord, Product

LEVEL_GREAT = "great"
LEVEL_DEAL = "deal"
LEVEL_NONE = "none"
LEVEL_UNKNOWN = "unknown"  


@dataclass(frozen=True)
class DealInfo:
    current_price: Decimal
    baseline_price: Decimal | None  # B
    record_count: int  # N
    window_low: Decimal | None 
    discount_percent: Decimal | None  
    level: str

    @property
    def is_deal(self):
        return self.level in (LEVEL_DEAL, LEVEL_GREAT)


def _money(value):
    return Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def classify(current_price, baseline, record_count, window_low=None):
    if baseline is None or record_count < settings.DEAL_MIN_RECORDS or baseline <= 0:
        return DealInfo(current_price, None, record_count, window_low, None, LEVEL_UNKNOWN)

    exact = (baseline - current_price) / baseline * 100
    threshold = Decimal(settings.DEAL_THRESHOLD_PERCENT)
    
    if exact >= threshold * 2:
        level = LEVEL_GREAT
    elif exact >= threshold:
        level = LEVEL_DEAL
    else:
        level = LEVEL_NONE
    
    shown = exact.quantize(Decimal("0.1"), rounding=ROUND_DOWN)
    return DealInfo(current_price, _money(baseline), record_count, window_low, shown, level)


def deal_window_start():
    return timezone.now() - timedelta(days=settings.DEAL_WINDOW_DAYS)


def get_deal_infos(products):
    
    products = list(products)
    if not products:
        return {}
    rows = (
        PriceRecord.objects.filter(product__in=[p.pk for p in products], recorded_at__gte=deal_window_start())
        .values("product_id", "retailer")
        .annotate(avg_price=Avg("price"), n=Count("pk"), low=Min("price"))
    )
    stats = {(row["product_id"], row["retailer"]): row for row in rows}

    infos = {}
    for product in products:
        row = stats.get((product.pk, product.best_retailer))
        if row is None:
            infos[product.pk] = classify(product.price, None, 0)
        else:
            infos[product.pk] = classify(product.price, row["avg_price"], row["n"], row["low"])
    return infos


def get_deal_info(product):
    return get_deal_infos([product])[product.pk]


def find_deals():
    products = list(Product.objects.all())
    infos = get_deal_infos(products)
    deals = [(p, infos[p.pk]) for p in products if infos[p.pk].is_deal]
    deals.sort(key=lambda pair: pair[1].discount_percent, reverse=True)
    return deals


def best_value_flags(products):
   

    def winners(key, lowest=True):
        values = {p.pk: key(p) for p in products if key(p) is not None}
        if not values:
            return set()
        target = min(values.values()) if lowest else max(values.values())
        return {pk for pk, value in values.items() if value == target}

    return {
        "price": winners(lambda p: p.price),
        "price_per_gb": winners(lambda p: p.price_per_gb),
        "capacity": winners(lambda p: p.capacity_gb, lowest=False),
        "speed": winners(lambda p: p.speed_mhz, lowest=False),
        "latency": winners(lambda p: p.latency_ns),
    }
