"""
Business logic that is not tied to a single view.

THE DEAL CALCULATION (used by the product pages, the Deals page and watchlist)
-----------------------------------------------------------------------------
For a product P whose best current price is C, offered by retailer R:

    baseline  B = average price of all of R's price records for P that were
                  recorded in the last DEAL_WINDOW_DAYS days   (default 90)
    N           = how many such records there are
    discount  D = (B - C) / B x 100    (compared exactly; shown truncated to 0.1 %)

    P is a "deal"       when N >= DEAL_MIN_RECORDS (3)  and  D >= DEAL_THRESHOLD_PERCENT (10)
    P is a "great deal" when N >= DEAL_MIN_RECORDS (3)  and  D >= 2 x the threshold (20)

Why compare a retailer with *its own* history?  Comparing the cheapest retailer
with the average of all retailers would always show a "discount" simply because
we are picking the minimum of several prices.  Using the same retailer's own
history means the discount is a genuine drop in that shop's price.

WATCHLIST RULE:  an item's target is reached when  best current price <= target price.

All thresholds live in settings.py so they can be tuned without touching code.
"""

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
LEVEL_UNKNOWN = "unknown"  # not enough history to judge


@dataclass(frozen=True)
class DealInfo:
    current_price: Decimal
    baseline_price: Decimal | None  # B
    record_count: int  # N
    window_low: Decimal | None  # cheapest record in the window (for display only)
    discount_percent: Decimal | None  # D, may be negative (price is above baseline)
    level: str

    @property
    def is_deal(self):
        return self.level in (LEVEL_DEAL, LEVEL_GREAT)


def _money(value):
    return Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def classify(current_price, baseline, record_count, window_low=None):
    """Pure function implementing the formula above (easy to unit-test)."""
    if baseline is None or record_count < settings.DEAL_MIN_RECORDS or baseline <= 0:
        return DealInfo(current_price, None, record_count, window_low, None, LEVEL_UNKNOWN)

    exact = (baseline - current_price) / baseline * 100
    threshold = Decimal(settings.DEAL_THRESHOLD_PERCENT)
    # The decision uses the EXACT discount, so 9.99% is not a deal.
    if exact >= threshold * 2:
        level = LEVEL_GREAT
    elif exact >= threshold:
        level = LEVEL_DEAL
    else:
        level = LEVEL_NONE
    # The figure shown to the user is truncated to 1 dp so it never overstates the discount.
    shown = exact.quantize(Decimal("0.1"), rounding=ROUND_DOWN)
    return DealInfo(current_price, _money(baseline), record_count, window_low, shown, level)


def deal_window_start():
    return timezone.now() - timedelta(days=settings.DEAL_WINDOW_DAYS)


def get_deal_infos(products):
    """
    Return {product.pk: DealInfo} for any iterable of products using ONE
    grouped query against price_records (MongoDB $group on product + retailer).
    """
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
    """All current deals, best discount first: [(product, DealInfo), ...]."""
    products = list(Product.objects.all())
    infos = get_deal_infos(products)
    deals = [(p, infos[p.pk]) for p in products if infos[p.pk].is_deal]
    deals.sort(key=lambda pair: pair[1].discount_percent, reverse=True)
    return deals


def best_value_flags(products):
    """
    For the comparison table: which product wins each row?
    Returns {row_name: set_of_product_pks}.  Ties all win.
    """

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
