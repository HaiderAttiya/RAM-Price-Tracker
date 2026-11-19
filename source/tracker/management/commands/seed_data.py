"""
python manage.py seed_data [--reset]

Loads realistic (but SYNTHETIC) sample data:
  * ~50 RAM kits across DDR3 / DDR4 / DDR5
  * ~120 days of price history per kit, from 3-5 retailers each
  * a few recent price drops so the "deal" logic has something to find
  * two demo users and a small watchlist

The generator is seeded, so the same command always produces the same
catalogue and the same price *shape* (dates are relative to "now").
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from tracker.models import RETAILER_NAMES, PriceRecord, Product, WatchlistItem
from tracker.sample_data import CATALOGUE, PROMOTIONS, RETAILER_OFFSET, WATCHLIST

HISTORY_DAYS = 120


def to_price(value):
    """Retail-style price: round to a whole number, then x.99 (e.g. 188.99)."""
    return Decimal(max(round(value), 2)) - Decimal("0.01")


class Command(BaseCommand):
    help = "Load sample products, price history, demo users and a demo watchlist."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing products, price records and watchlist entries first.")
        parser.add_argument("--seed", type=int, default=2026, help="Random seed (default 2026).")
        parser.add_argument("--admin-password", default="AdminPass123!", help="Password for the demo 'admin' superuser.")
        parser.add_argument("--demo-password", default="DemoPass123!", help="Password for the demo 'demo' user.")

    def handle(self, *args, **options):
        if Product.objects.exists() and not options["reset"]:
            raise CommandError("The catalogue already contains products. Run with --reset to replace them.")

        if options["reset"]:
            WatchlistItem.objects.all().delete()
            PriceRecord.objects.all().delete()
            Product.objects.all().delete()
            self.stdout.write("Existing catalogue deleted.")

        rng = random.Random(options["seed"])
        now = timezone.now()

        products = self.create_products()
        record_count = self.create_price_history(products, rng, now)
        for product in products:
            product.refresh_price_from_history()  # price column == best price in history
        users = self.create_users(options)
        watch_count = self.create_watchlist(users["demo"], products)

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(products)} products, {record_count} price records and {watch_count} watchlist entries."
        ))
        self.stdout.write(
            f"Demo logins:  admin / {options['admin_password']}  (superuser)   demo / {options['demo_password']}"
        )

    # ------------------------------------------------------------------
    def create_products(self):
        objs = [
            Product(
                brand=brand, model=model, ddr_generation=gen, capacity_gb=cap, modules=mods,
                speed_mhz=speed, cas_latency=cl, voltage=Decimal(volts),
                price=Decimal(price), best_retailer="Amazon",  # placeholders, recalculated from history below
            )
            for brand, model, gen, cap, mods, speed, cl, volts, price in CATALOGUE
        ]
        for obj in objs:
            obj.full_clean()  # make sure the sample data obeys the same rules as user input
        Product.objects.bulk_create(objs)
        # bulk_create gives every object its _id on MongoDB; reload in catalogue order.
        by_key = {(p.brand, p.model, p.capacity_gb, p.speed_mhz, p.cas_latency, p.ddr_generation): p for p in Product.objects.all()}
        return [by_key[(b, m, c, s, cl, g)] for b, m, g, c, _mods, s, cl, _v, _p in CATALOGUE]

    def market_trend(self, rng):
        """A daily price index over HISTORY_DAYS+1 days, normalised so today == 1.0."""
        drift = rng.uniform(-0.0008, 0.0012)
        level, series = 1.0, []
        for _ in range(HISTORY_DAYS + 1):
            level = min(1.25, max(0.80, level * (1 + rng.gauss(drift, 0.007))))
            series.append(level)
        return [value / series[-1] for value in series]  # index 0 = oldest, last = today

    def create_price_history(self, products, rng, now):
        key_to_index = {(c[0], c[1], c[3], c[5]): i for i, c in enumerate(CATALOGUE)}
        promo_by_index = {key_to_index[(b, m, cap, sp)]: disc for b, m, cap, sp, disc in PROMOTIONS}
        records = []
        for index, product in enumerate(products):
            typical = float(CATALOGUE[index][8])
            trend = self.market_trend(rng)
            retailers = ["Amazon"] + rng.sample([r for r in RETAILER_NAMES if r != "Amazon"], rng.randint(2, 4))

            promo_retailer = None
            if index in promo_by_index:
                # The cheapest-priced retailer for this kit runs the promotion.
                promo_retailer = min(retailers, key=lambda r: RETAILER_OFFSET[r])

            for retailer in retailers:
                offset = RETAILER_OFFSET[retailer] * rng.uniform(0.985, 1.015)
                # Walk backwards from "a day or two ago" in 3-8 day steps.
                age_days = rng.uniform(0.1, 2.0)
                ages = []
                while age_days < HISTORY_DAYS:
                    ages.append(age_days)
                    age_days += rng.uniform(3, 8)
                for position, age in enumerate(ages):
                    day_index = HISTORY_DAYS - int(age)
                    price = typical * trend[day_index] * offset * rng.uniform(0.988, 1.012)
                    if retailer == promo_retailer and position == 0:  # the newest record is the price drop
                        price *= 1 - promo_by_index[index]
                    records.append(PriceRecord(
                        product=product, retailer=retailer, price=to_price(price),
                        recorded_at=now - timedelta(days=age),
                    ))

        PriceRecord.objects.bulk_create(records, batch_size=500)
        return len(records)

    def create_users(self, options):
        User = get_user_model()
        users = {}
        for username, password, staff in (
            ("admin", options["admin_password"], True),
            ("demo", options["demo_password"], False),
        ):
            user = User.objects.filter(username=username).first()
            if user is None:
                user = User(username=username, email=f"{username}@example.com")
            user.is_staff = user.is_superuser = staff
            user.set_password(password)
            user.save()
            users[username] = user
        return users

    def create_watchlist(self, user, products):
        """A mix of reached and not-yet-reached targets for the demo user."""
        key_to_product = {(p.brand, p.model, p.capacity_gb, p.speed_mhz): p for p in products}
        count = 0
        for brand, model, capacity, speed, factor in WATCHLIST:
            product = key_to_product[(brand, model, capacity, speed)]
            product.refresh_from_db()
            target = (product.price * Decimal(str(factor))).quantize(Decimal("1")) - Decimal("0.01")
            WatchlistItem.objects.create(user=user, product=product, target_price=target)
            count += 1
        return count
