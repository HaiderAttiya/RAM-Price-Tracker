from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from tracker.models import PriceRecord, Product, WatchlistItem
from tracker.services import find_deals


class SeedCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        pass

    def run_seed(self, *args):
        out = StringIO()
        call_command("seed_data", *args, stdout=out)
        return out.getvalue()

    def test_seed_creates_consistent_data(self):
        self.run_seed("--reset")
        self.assertGreaterEqual(Product.objects.count(), 45)
        self.assertGreater(PriceRecord.objects.count(), 3000)
        self.assertEqual(WatchlistItem.objects.count(), 5)

        # CONSISTENCY: every product's stored price is the cheapest of its retailers' newest records.
        for product in Product.objects.all():
            latest = product.latest_prices_by_retailer()
            self.assertTrue(latest, f"{product} has no price history")
            self.assertEqual((product.price, product.best_retailer), (latest[0].price, latest[0].retailer), str(product))

    def test_every_product_has_enough_history_for_the_deal_rule(self):
        self.run_seed("--reset")
        for product in Product.objects.all():
            self.assertGreaterEqual(product.price_records.count(), 12, str(product))

    def test_seed_produces_a_demo_worth_of_deals(self):
        self.run_seed("--reset")
        levels = [info.level for _p, info in find_deals()]
        self.assertGreaterEqual(len(levels), 5)
        self.assertIn("great", levels)

    def test_seed_refuses_to_duplicate(self):
        self.run_seed("--reset")
        with self.assertRaises(CommandError):
            self.run_seed()

    def test_reset_replaces_rather_than_duplicates(self):
        self.run_seed("--reset")
        first = Product.objects.count()
        self.run_seed("--reset")
        self.assertEqual(Product.objects.count(), first)

    def test_same_seed_gives_same_catalogue_and_shape(self):
        self.run_seed("--reset", "--seed", "7")
        snapshot = sorted((str(p), p.price_records.count()) for p in Product.objects.all())
        self.run_seed("--reset", "--seed", "7")
        again = sorted((str(p), p.price_records.count()) for p in Product.objects.all())
        self.assertEqual(snapshot, again)
