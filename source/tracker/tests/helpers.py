from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from tracker.models import PriceRecord, Product

_counter = {"n": 0}


def make_product(**overrides):
    _counter["n"] += 1
    data = dict(
        brand="Corsair", model=f"Vengeance {_counter['n']}", ddr_generation="DDR5", capacity_gb=32, modules=2,
        speed_mhz=6000, cas_latency=30, voltage=Decimal("1.35"), price=Decimal("200.00"), best_retailer="Amazon",
    )
    data.update(overrides)
    return Product.objects.create(**data)


def add_record(product, price, retailer="Amazon", days_ago=0, **kwargs):
    return PriceRecord.objects.create(
        product=product, retailer=retailer, price=Decimal(str(price)),
        recorded_at=timezone.now() - timedelta(days=days_ago), **kwargs,
    )


def make_user(username="alice", password="pw-Test-12345", **kwargs):
    return get_user_model().objects.create_user(username=username, password=password, **kwargs)


def product_with_history(prices_by_age, retailer="Amazon", **overrides):
    
    product = make_product(**overrides)
    for price, age in sorted(prices_by_age, key=lambda pair: -pair[1]):
        add_record(product, price, retailer=retailer, days_ago=age)
    product.refresh_from_db()
    return product
