from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from tracker.models import PriceRecord, Product, WatchlistItem

from .helpers import add_record, make_product, make_user


class ProductValidationTests(TestCase):
    def full_clean(self, **overrides):
        data = dict(
            brand="Kingston", model="Fury Beast", ddr_generation="DDR5", capacity_gb=32, modules=2,
            speed_mhz=6000, cas_latency=36, voltage=Decimal("1.35"), price=Decimal("150"), best_retailer="Amazon",
        )
        data.update(overrides)
        Product(**data).full_clean()

    def test_valid_product_passes(self):
        self.full_clean()

    def test_ddr5_speed_below_range_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self.full_clean(speed_mhz=2400)
        self.assertIn("speed_mhz", ctx.exception.message_dict)

    def test_ddr4_voltage_out_of_range_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self.full_clean(ddr_generation="DDR4", speed_mhz=3200, cas_latency=16, voltage=Decimal("1.80"))
        self.assertIn("voltage", ctx.exception.message_dict)

    def test_cas_latency_out_of_range_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self.full_clean(cas_latency=10)  
        self.assertIn("cas_latency", ctx.exception.message_dict)

    def test_capacity_must_divide_between_sticks(self):
        
        product = Product(ddr_generation="DDR4", capacity_gb=6, modules=4, speed_mhz=3200, cas_latency=16, voltage=Decimal("1.35"))
        with self.assertRaises(ValidationError) as ctx:
            product.clean()
        self.assertIn("modules", ctx.exception.message_dict)

    def test_price_must_be_positive(self):
        with self.assertRaises(ValidationError) as ctx:
            self.full_clean(price=Decimal("0"))
        self.assertIn("price", ctx.exception.message_dict)

    def test_duplicate_variant_rejected_by_unique_constraint(self):
        make_product(brand="Kingston", model="Fury Beast")
        with self.assertRaises(ValidationError) as ctx:
            self.full_clean(brand="Kingston", model="Fury Beast", cas_latency=30)  
        self.assertIn("already in the catalogue", str(ctx.exception))


class ProductCalculationTests(TestCase):
    def test_true_latency_ns(self):
        
        self.assertEqual(make_product(speed_mhz=6000, cas_latency=30).latency_ns, Decimal("10.00"))
        self.assertEqual(make_product(ddr_generation="DDR4", speed_mhz=3200, cas_latency=16, voltage=Decimal("1.35")).latency_ns, Decimal("10.00"))

    def test_price_per_gb(self):
        self.assertEqual(make_product(capacity_gb=32, price=Decimal("192.00")).price_per_gb, Decimal("6.00"))

    def test_capacity_display(self):
        self.assertEqual(make_product(capacity_gb=32, modules=2).capacity_display, "32 GB (2 × 16 GB)")
        self.assertEqual(make_product(capacity_gb=16, modules=1, model="Single").capacity_display, "16 GB")


class PriceSynchronisationTests(TestCase):

    def setUp(self):
        self.product = make_product(price=Decimal("999.00"))

    def reload(self):
        self.product.refresh_from_db()
        return self.product

    def test_first_record_sets_price_and_retailer(self):
        add_record(self.product, "180.00", retailer="Computia")
        p = self.reload()
        self.assertEqual((p.price, p.best_retailer), (Decimal("180.00"), "Computia"))
        self.assertIsNotNone(p.price_updated_at)

    def test_cheapest_retailer_wins(self):
        add_record(self.product, "200.00", retailer="Amazon", days_ago=2)
        add_record(self.product, "185.00", retailer="Cazasouq", days_ago=1)
        p = self.reload()
        self.assertEqual((p.price, p.best_retailer), (Decimal("185.00"), "Cazasouq"))

    def test_only_each_retailers_latest_record_counts(self):
        add_record(self.product, "100.00", retailer="Amazon", days_ago=10)   
        add_record(self.product, "190.00", retailer="Amazon", days_ago=1)   
        add_record(self.product, "195.00", retailer="Computia", days_ago=1)
        p = self.reload()
        self.assertEqual((p.price, p.best_retailer), (Decimal("190.00"), "Amazon"))

    def test_back_dated_record_does_not_change_current_price(self):
        add_record(self.product, "190.00", retailer="Amazon", days_ago=1)
        add_record(self.product, "50.00", retailer="Amazon", days_ago=30) 
        self.assertEqual(self.reload().price, Decimal("190.00"))

    def test_deleting_the_newest_record_recalculates(self):
        add_record(self.product, "190.00", retailer="Amazon", days_ago=5)
        newest = add_record(self.product, "170.00", retailer="Amazon", days_ago=1)
        self.assertEqual(self.reload().price, Decimal("170.00"))
        newest.delete()
        self.assertEqual(self.reload().price, Decimal("190.00"))

    def test_deleting_every_record_leaves_last_price_unchanged(self):
        only = add_record(self.product, "175.00")
        only.delete()
        self.assertEqual(self.reload().price, Decimal("175.00"))

    def test_future_record_rejected(self):
        record = PriceRecord(product=self.product, retailer="Amazon", price=Decimal("10"), recorded_at=timezone.now() + timedelta(days=2))
        with self.assertRaises(ValidationError) as ctx:
            record.full_clean()
        self.assertIn("recorded_at", ctx.exception.message_dict)


class CascadeTests(TestCase):
    def test_deleting_a_product_removes_its_records_and_watchlist_entries(self):
        product = make_product()
        other = make_product()
        add_record(product, "150.00")
        add_record(other, "160.00")
        user = make_user()
        WatchlistItem.objects.create(user=user, product=product, target_price=Decimal("120"))
        WatchlistItem.objects.create(user=user, product=other, target_price=Decimal("120"))

        deleted_pk = product.pk  
        product.delete()

        self.assertEqual(PriceRecord.objects.filter(product_id=deleted_pk).count(), 0)
        self.assertEqual(WatchlistItem.objects.filter(product_id=deleted_pk).count(), 0)
        # ...but nothing belonging to other products is touched
        self.assertEqual(PriceRecord.objects.filter(product=other).count(), 1)
        self.assertEqual(WatchlistItem.objects.filter(product=other).count(), 1)


class WatchlistModelTests(TestCase):
    def test_one_entry_per_user_per_product(self):
        product, user = make_product(), make_user()
        WatchlistItem.objects.create(user=user, product=product, target_price=Decimal("100"))
        with self.assertRaises(ValidationError):
            WatchlistItem(user=user, product=product, target_price=Decimal("90")).full_clean()

    def test_target_reached(self):
        product = make_product(price=Decimal("150.00"))
        user = make_user()
        self.assertTrue(WatchlistItem(user=user, product=product, target_price=Decimal("150.00")).target_reached)
        self.assertTrue(WatchlistItem(user=user, product=product, target_price=Decimal("160.00")).target_reached)
        self.assertFalse(WatchlistItem(user=user, product=product, target_price=Decimal("149.99")).target_reached)
