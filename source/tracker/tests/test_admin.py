from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from tracker.models import PriceRecord, Product, WatchlistItem

from .helpers import add_record, make_product, product_with_history


class AdminSiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser("root", "root@example.com", "Adm1n-pw-12345")
        cls.product = product_with_history([(100, 5), (90, 1)])
        WatchlistItem.objects.create(user=cls.admin, product=cls.product, target_price=Decimal("80"))

    def setUp(self):
        self.client.login(username="root", password="Adm1n-pw-12345")

    def test_non_staff_can_not_open_admin(self):
        self.client.logout()
        get_user_model().objects.create_user("pleb", password="pw-Test-12345")
        self.client.login(username="pleb", password="pw-Test-12345")
        self.assertEqual(self.client.get("/admin/tracker/product/").status_code, 302)

    def test_changelists_load(self):
        for model in ("product", "pricerecord", "watchlistitem"):
            with self.subTest(model=model):
                self.assertEqual(self.client.get(f"/admin/tracker/{model}/").status_code, 200)

    def test_product_change_page_has_inline_price_history_and_readonly_price(self):
        response = self.client.get(f"/admin/tracker/product/{self.product.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "price_records")
        self.assertNotIn("price", response.context["adminform"].form.fields)

    def test_admin_search_and_filter(self):
        response = self.client.get("/admin/tracker/product/", {"q": self.product.brand, "ddr_generation": "DDR5"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.model)

    def test_adding_a_product_in_admin_creates_its_first_price_record(self):
        data = {
            "brand": "Lexar", "model": "Ares", "ddr_generation": "DDR5", "capacity_gb": 32, "modules": 2,
            "speed_mhz": 6400, "cas_latency": 32, "voltage": "1.40", "price": "205.00", "best_retailer": "Amazon",
            "price_records-TOTAL_FORMS": 0, "price_records-INITIAL_FORMS": 0,
            "price_records-MIN_NUM_FORMS": 0, "price_records-MAX_NUM_FORMS": 1000,
        }
        response = self.client.post("/admin/tracker/product/add/", data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        product = Product.objects.get(brand="Lexar")
        self.assertEqual(product.price_records.count(), 1)

    def test_admin_bulk_delete_keeps_product_price_in_sync(self):
        # Delete the newest record through the admin action; the price must fall back to the older record.
        newest = self.product.price_records.order_by("-recorded_at").first()
        self.client.post("/admin/tracker/pricerecord/", {"action": "delete_selected", "_selected_action": [str(newest.pk)], "post": "yes"})
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("100.00"))
