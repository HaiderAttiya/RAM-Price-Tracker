from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from tracker.models import PriceRecord, Product, WatchlistItem

from .helpers import add_record, make_product, make_user, product_with_history

D = Decimal


def url(name, *args, **kwargs):
    return reverse(f"tracker:{name}", args=[str(a) for a in args], kwargs=kwargs or None)


VALID_PRODUCT = {
    "brand": "kingston", "model": "Fury Beast", "ddr_generation": "DDR5", "capacity_gb": "32", "modules": "2",
    "speed_mhz": "6000", "cas_latency": "36", "voltage": "1.35", "price": "159.99", "best_retailer": "Computia",
}


class PublicPageTests(TestCase):
    def test_public_pages_load(self):
        product = product_with_history([(100, 30), (100, 20), (100, 10), (70, 0)])
        for target in (url("home"), url("product_list"), url("product_detail", product.pk), url("deals"),
                       reverse("login"), reverse("signup")):
            with self.subTest(target=target):
                self.assertEqual(self.client.get(target).status_code, 200)

    def test_home_shows_counts_and_deals(self):
        product_with_history([(100, 30), (100, 20), (100, 10), (70, 0)])
        response = self.client.get(url("home"))
        self.assertEqual(response.context["product_count"], 1)
        self.assertEqual(response.context["record_count"], 4)
        self.assertEqual(response.context["deal_count"], 1)

    def test_unknown_url_uses_friendly_404(self):
        response = self.client.get("/definitely-not-here/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "We can not find that page", status_code=404)

    def test_missing_product_is_404(self):
        self.assertEqual(self.client.get(url("product_detail", "0" * 24)).status_code, 404)

    def test_malformed_product_id_is_404(self):
        self.assertEqual(self.client.get("/products/not-an-id/").status_code, 404)


class SearchAndFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = make_product(brand="Corsair", model="Vengeance", ddr_generation="DDR5", capacity_gb=32, price=D("200"))
        cls.b = make_product(brand="Corsair", model="Vengeance LPX", ddr_generation="DDR4", capacity_gb=16, speed_mhz=3200, cas_latency=16, voltage=D("1.35"), price=D("60"))
        cls.c = make_product(brand="G.Skill", model="Trident Z5", ddr_generation="DDR5", capacity_gb=64, price=D("380"))
        cls.d = make_product(brand="Kingston", model="Fury Beast", ddr_generation="DDR5", capacity_gb=32, price=D("150"))

    def names(self, **params):
        response = self.client.get(url("product_list"), params)
        self.assertEqual(response.status_code, 200)
        return {p.pk for p in response.context["products"]}, response

    def test_no_filters_lists_everything(self):
        found, _ = self.names()
        self.assertEqual(found, {self.a.pk, self.b.pk, self.c.pk, self.d.pk})

    def test_filter_by_brand(self):
        found, _ = self.names(brand="Corsair")
        self.assertEqual(found, {self.a.pk, self.b.pk})

    def test_filter_by_ddr_generation(self):
        found, _ = self.names(ddr_generation="DDR4")
        self.assertEqual(found, {self.b.pk})

    def test_filter_by_capacity(self):
        found, _ = self.names(capacity_gb="32")
        self.assertEqual(found, {self.a.pk, self.d.pk})

    def test_filter_by_price_range_is_inclusive(self):
        found, _ = self.names(min_price="150", max_price="200")
        self.assertEqual(found, {self.a.pk, self.d.pk})

    def test_combined_filters(self):
        found, _ = self.names(ddr_generation="DDR5", capacity_gb="32", max_price="170")
        self.assertEqual(found, {self.d.pk})

    def test_free_text_search_matches_brand_and_model_case_insensitively(self):
        found, _ = self.names(q="corsair lpx")
        self.assertEqual(found, {self.b.pk})
        found, _ = self.names(q="TRIDENT")
        self.assertEqual(found, {self.c.pk})

    def test_search_can_match_ddr_generation(self):
        found, _ = self.names(q="ddr4")
        self.assertEqual(found, {self.b.pk})

    def test_no_match_shows_empty_state(self):
        found, response = self.names(q="nonexistent-brand")
        self.assertEqual(found, set())
        self.assertContains(response, "No products found")

    def test_sort_price_ascending_and_descending(self):
        _, response = self.names(sort="price_asc")
        self.assertEqual([p.pk for p in response.context["products"]], [self.b.pk, self.d.pk, self.a.pk, self.c.pk])
        _, response = self.names(sort="price_desc")
        self.assertEqual([p.pk for p in response.context["products"]], [self.c.pk, self.a.pk, self.d.pk, self.b.pk])

    def test_min_greater_than_max_shows_error_and_ignores_the_bad_bound(self):
        found, response = self.names(min_price="300", max_price="100")
        self.assertContains(response, "Max price must be greater than or equal to min price")
        self.assertTrue(found)  # list still renders

    def test_garbage_input_does_not_crash(self):
        _, response = self.names(capacity_gb="abc", min_price="x", sort="evil", brand="Nope", ddr_generation="DDR9")
        self.assertEqual(response.status_code, 200)

    def test_pagination(self):
        for _ in range(14):
            make_product()
        response = self.client.get(url("product_list"))
        self.assertEqual(len(response.context["products"]), 12)
        self.assertEqual(response.context["total"], 18)
        response = self.client.get(url("product_list"), {"page": 2})
        self.assertEqual(len(response.context["products"]), 6)

    def test_filter_form_keeps_the_query_in_pagination_links(self):
        for _ in range(14):
            make_product(brand="Corsair")
        response = self.client.get(url("product_list"), {"brand": "Corsair"})
        self.assertContains(response, "brand=Corsair&amp;page=2")


class ProductDetailTests(TestCase):
    def test_detail_shows_chart_history_and_deal(self):
        product = product_with_history([(100, 30), (100, 20), (100, 10), (70, 0)])
        response = self.client.get(url("product_detail", product.pk))
        self.assertContains(response, "<svg")
        self.assertContains(response, "Great deal")
        self.assertEqual(response.context["record_total"], 4)
        self.assertEqual(response.context["deal"].level, "great")

    def test_invalid_range_falls_back_to_default(self):
        product = product_with_history([(100, 5)])
        response = self.client.get(url("product_detail", product.pk), {"range": "bogus"})
        self.assertEqual(response.context["range_key"], "90")

    def test_range_filter_limits_the_chart_not_the_table(self):
        product = product_with_history([(100, 200), (100, 100), (90, 5)])
        response = self.client.get(url("product_detail", product.pk), {"range": "30"})
        chart_points = sum(len(s["points"]) for s in response.context["chart"]["data"]["series"])
        self.assertEqual(chart_points, 1)
        self.assertEqual(response.context["record_total"], 3)
        response = self.client.get(url("product_detail", product.pk), {"range": "all"})
        self.assertEqual(sum(len(s["points"]) for s in response.context["chart"]["data"]["series"]), 3)

    def test_history_is_paginated_newest_first(self):
        product = product_with_history([(100 + i, i) for i in range(30)])
        response = self.client.get(url("product_detail", product.pk))
        page = response.context["history_page"]
        self.assertEqual(len(page), 12)
        dates = [r.recorded_at for r in page]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_anonymous_sees_login_prompts_not_edit_buttons(self):
        product = product_with_history([(100, 1)])
        response = self.client.get(url("product_detail", product.pk))
        self.assertNotContains(response, "Delete</a>")
        self.assertContains(response, "Log in to save this product")


class AccessControlTests(TestCase):
    def setUp(self):
        self.product = product_with_history([(100, 5), (95, 1)])
        self.record = self.product.price_records.first()

    def test_anonymous_users_are_redirected_to_login(self):
        targets = [
            url("product_create"), url("product_update", self.product.pk), url("product_delete", self.product.pk),
            url("price_create", self.product.pk), url("price_update", self.record.pk), url("price_delete", self.record.pk),
            url("watchlist"),
        ]
        for target in targets:
            with self.subTest(target=target):
                response = self.client.get(target)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith(reverse("login")), response["Location"])

    def test_anonymous_post_does_not_change_data(self):
        self.client.post(url("product_delete", self.product.pk))
        self.client.post(url("price_delete", self.record.pk))
        self.client.post(url("watchlist_add", self.product.pk), {"target_price": "50"})
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.assertEqual(PriceRecord.objects.count(), 2)
        self.assertEqual(WatchlistItem.objects.count(), 0)

    def test_watchlist_add_rejects_get(self):
        make_user(is_staff=True)
        self.client.login(username="alice", password="pw-Test-12345")
        self.assertEqual(self.client.get(url("watchlist_add", self.product.pk)).status_code, 405)


class ProductCrudTests(TestCase):
    def setUp(self):
        self.user = make_user(is_staff=True)
        self.client.login(username="alice", password="pw-Test-12345")

    def test_create_product_also_creates_the_first_price_record(self):
        response = self.client.post(url("product_create"), dict(VALID_PRODUCT, brand="Kingston"))
        product = Product.objects.get()
        self.assertRedirects(response, product.get_absolute_url())
        self.assertEqual(product.brand, "Kingston")
        records = list(product.price_records.all())
        self.assertEqual(len(records), 1)
        self.assertEqual((records[0].price, records[0].retailer), (D("159.99"), "Computia"))
        self.assertEqual((product.price, product.best_retailer), (D("159.99"), "Computia"))

    def test_brand_spelling_reuses_the_existing_one(self):
        make_product(brand="Kingston", model="Other Line")
        self.client.post(url("product_create"), VALID_PRODUCT)  # "kingston"
        self.assertEqual(Product.objects.filter(model="Fury Beast").get().brand, "Kingston")

    def test_invalid_product_shows_errors_and_saves_nothing(self):
        bad = dict(VALID_PRODUCT, speed_mhz="1000", price="-5", voltage="3.3")
        response = self.client.post(url("product_create"), bad)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        for field in ("speed_mhz", "price", "voltage"):
            self.assertIn(field, form.errors)
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(PriceRecord.objects.count(), 0)

    def test_required_fields_enforced(self):
        response = self.client.post(url("product_create"), {})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.context["form"].errors), 8)

    def test_duplicate_product_rejected_with_clear_message(self):
        self.client.post(url("product_create"), VALID_PRODUCT)
        response = self.client.post(url("product_create"), VALID_PRODUCT)
        self.assertEqual(Product.objects.count(), 1)
        self.assertContains(response, "already in the catalogue")

    def test_edit_updates_specs_but_never_the_price(self):
        product = product_with_history([(150, 3)], price=D("150"))
        data = {k: v for k, v in VALID_PRODUCT.items() if k not in ("price", "best_retailer")}
        data.update(brand=product.brand, model="Renamed", price="1.00")  # a smuggled price must be ignored
        response = self.client.post(url("product_update", product.pk), data)
        self.assertRedirects(response, product.get_absolute_url())
        product.refresh_from_db()
        self.assertEqual(product.model, "Renamed")
        self.assertEqual(product.price, D("150.00"))

    def test_edit_form_has_no_price_field(self):
        product = make_product()
        response = self.client.get(url("product_update", product.pk))
        self.assertNotIn("price", response.context["form"].fields)

    def test_delete_requires_post_then_removes_product_and_history(self):
        product = product_with_history([(100, 5), (95, 1)])
        WatchlistItem.objects.create(user=self.user, product=product, target_price=D("80"))
        confirm = self.client.get(url("product_delete", product.pk))
        self.assertContains(confirm, "all 2 price records")
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())  # GET alone deletes nothing
        response = self.client.post(url("product_delete", product.pk))
        self.assertRedirects(response, url("product_list"))
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(PriceRecord.objects.count(), 0)
        self.assertEqual(WatchlistItem.objects.count(), 0)

    def test_success_messages_are_shown(self):
        response = self.client.post(url("product_create"), VALID_PRODUCT, follow=True)
        self.assertContains(response, "Its first price has been recorded")


class PriceRecordCrudTests(TestCase):
    def setUp(self):
        make_user(is_staff=True)
        self.client.login(username="alice", password="pw-Test-12345")
        self.product = product_with_history([(200, 10)])

    def post_price(self, **overrides):
        data = {"retailer": "Cazasouq", "price": "150.00", "recorded_at": "2026-11-19T10:00", "retailer_url": ""}
        data.update(overrides)
        return self.client.post(url("price_create", self.product.pk), data)

    def test_adding_a_lower_price_updates_the_product(self):
        self.post_price(recorded_at="2026-11-19T10:00")
        self.product.refresh_from_db()
        self.assertEqual((self.product.price, self.product.best_retailer), (D("150.00"), "Cazasouq"))
        self.assertEqual(self.product.price_records.count(), 2)

    def test_invalid_price_rejected(self):
        response = self.post_price(price="0")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.product.price_records.count(), 1)

    def test_future_date_rejected(self):
        response = self.post_price(recorded_at="2099-01-01T10:00")
        self.assertEqual(response.status_code, 200)
        self.assertIn("recorded_at", response.context["form"].errors)

    def test_bad_url_rejected(self):
        response = self.post_price(retailer_url="not a url")
        self.assertIn("retailer_url", response.context["form"].errors)

    def test_edit_record_resyncs_product_price(self):
        record = self.product.price_records.get()
        data = {"retailer": "Amazon", "price": "123.45", "recorded_at": "2026-11-01T09:30", "retailer_url": ""}
        self.client.post(url("price_update", record.pk), data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, D("123.45"))

    def test_delete_record_recalculates_price(self):
        self.post_price(price="150.00")  # cheaper, newest
        newest = self.product.price_records.order_by("-recorded_at").first()
        self.client.post(url("price_delete", newest.pk))
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, D("200.00"))

    def test_the_last_record_can_not_be_deleted(self):
        only = self.product.price_records.get()
        response = self.client.post(url("price_delete", only.pk), follow=True)
        self.assertContains(response, "needs at least one price record")
        self.assertEqual(self.product.price_records.count(), 1)


class CompareTests(TestCase):
    def setUp(self):
        self.p = [make_product(price=D(str(100 + 10 * i))) for i in range(5)]

    def ids(self, *products):
        return [("ids", str(p.pk)) for p in products]

    def get(self, *products, extra=()):
        from urllib.parse import urlencode
        return self.client.get(url("compare") + "?" + urlencode(self.ids(*products) + list(extra)))

    def test_compare_two_to_four(self):
        for n in (2, 3, 4):
            response = self.get(*self.p[:n])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["products"]), n)

    def test_order_follows_selection(self):
        response = self.get(self.p[3], self.p[0])
        self.assertEqual([x.pk for x in response.context["products"]], [self.p[3].pk, self.p[0].pk])

    def test_fewer_than_two_redirects_with_message(self):
        response = self.client.get(url("compare") + f"?ids={self.p[0].pk}", follow=True)
        self.assertRedirects(response, url("product_list"))
        self.assertContains(response, "Tick at least two products")

    def test_more_than_four_is_truncated_with_message(self):
        response = self.get(*self.p, extra=())
        self.assertEqual(len(response.context["products"]), 4)
        self.assertContains(response, "up to 4 products")

    def test_invalid_and_duplicate_ids_are_ignored(self):
        from urllib.parse import urlencode
        query = urlencode([("ids", str(self.p[0].pk)), ("ids", str(self.p[0].pk)), ("ids", "garbage"), ("ids", str(self.p[1].pk)), ("ids", "f" * 24)])
        response = self.client.get(url("compare") + "?" + query)
        self.assertEqual(len(response.context["products"]), 2)

    def test_marks_the_cheapest_as_best(self):
        response = self.get(self.p[0], self.p[1])
        self.assertEqual(response.context["best"]["price"], {self.p[0].pk})
        self.assertContains(response, "best-tag")

    def test_remove_link_only_when_more_than_two(self):
        self.assertNotContains(self.get(self.p[0], self.p[1]), "compare-remove")
        self.assertContains(self.get(self.p[0], self.p[1], self.p[2]), "compare-remove")


class DealsPageTests(TestCase):
    def test_lists_only_real_deals_best_first(self):
        big = product_with_history([(100, 30), (100, 20), (100, 10), (60, 0)])
        small = product_with_history([(100, 30), (100, 20), (100, 10), (85, 0)])
        product_with_history([(100, 30), (100, 20), (100, 10), (100, 0)])
        response = self.client.get(url("deals"))
        self.assertEqual([p.pk for p, _ in response.context["deals"]], [big.pk, small.pk])

    def test_empty_state(self):
        make_product()
        self.assertContains(self.client.get(url("deals")), "No deals right now")


class WatchlistTests(TestCase):
    def setUp(self):
        self.alice = make_user("alice")
        self.bob = make_user("bob")
        self.product = product_with_history([(100, 5), (100, 3), (100, 2), (90, 0)])
        self.client.login(username="alice", password="pw-Test-12345")

    def test_add_to_watchlist(self):
        response = self.client.post(url("watchlist_add", self.product.pk), {"target_price": "85.00"}, follow=True)
        item = WatchlistItem.objects.get()
        self.assertEqual((item.user, item.product.pk, item.target_price), (self.alice, self.product.pk, D("85.00")))
        self.assertContains(response, "Added to your watchlist")

    def test_adding_twice_updates_the_target_instead_of_duplicating(self):
        self.client.post(url("watchlist_add", self.product.pk), {"target_price": "85"})
        self.client.post(url("watchlist_add", self.product.pk), {"target_price": "80"})
        item = WatchlistItem.objects.get()
        self.assertEqual(item.target_price, D("80.00"))

    def test_invalid_target_rejected(self):
        for bad in ("0", "-5", "abc", ""):
            with self.subTest(bad=bad):
                response = self.client.post(url("watchlist_add", self.product.pk), {"target_price": bad}, follow=True)
                self.assertContains(response, "Enter a target price")
        self.assertEqual(WatchlistItem.objects.count(), 0)

    def test_watchlist_page_flags_reached_targets_first(self):
        other = product_with_history([(200, 5), (200, 3), (200, 2), (200, 0)])
        WatchlistItem.objects.create(user=self.alice, product=other, target_price=D("150"))        # waiting
        WatchlistItem.objects.create(user=self.alice, product=self.product, target_price=D("95"))  # reached (90 <= 95)
        response = self.client.get(url("watchlist"))
        rows = response.context["rows"]
        self.assertEqual([r["product"].pk for r in rows], [self.product.pk, other.pk])
        self.assertEqual(response.context["reached_count"], 1)
        self.assertContains(response, "Target reached")
        self.assertContains(response, "above target")

    def test_watchlist_shows_only_own_items(self):
        WatchlistItem.objects.create(user=self.bob, product=self.product, target_price=D("50"))
        self.assertEqual(self.client.get(url("watchlist")).context["rows"], [])

    def test_edit_target(self):
        item = WatchlistItem.objects.create(user=self.alice, product=self.product, target_price=D("85"))
        self.client.post(url("watchlist_update", item.pk), {"target_price": "70.50"})
        item.refresh_from_db()
        self.assertEqual(item.target_price, D("70.50"))

    def test_remove_from_watchlist_keeps_the_product(self):
        item = WatchlistItem.objects.create(user=self.alice, product=self.product, target_price=D("85"))
        self.client.post(url("watchlist_delete", item.pk))
        self.assertEqual(WatchlistItem.objects.count(), 0)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_users_can_not_touch_each_others_items(self):
        theirs = WatchlistItem.objects.create(user=self.bob, product=self.product, target_price=D("85"))
        self.assertEqual(self.client.get(url("watchlist_update", theirs.pk)).status_code, 404)
        self.assertEqual(self.client.post(url("watchlist_update", theirs.pk), {"target_price": "1"}).status_code, 404)
        self.assertEqual(self.client.post(url("watchlist_delete", theirs.pk)).status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.target_price, D("85.00"))

    def test_detail_page_shows_watch_state(self):
        item = WatchlistItem.objects.create(user=self.alice, product=self.product, target_price=D("95"))
        response = self.client.get(url("product_detail", self.product.pk))
        self.assertEqual(response.context["watch_item"].pk, item.pk)
        self.assertContains(response, "Target reached")

    def test_list_marks_watched_products(self):
        WatchlistItem.objects.create(user=self.alice, product=self.product, target_price=D("95"))
        response = self.client.get(url("product_list"))
        self.assertTrue(response.context["products"][0].is_watched)


class AccountTests(TestCase):
    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(reverse("signup"), {"username": "newbie", "email": "n@example.com", "password1": "Sup3r-Secret-pw", "password2": "Sup3r-Secret-pw"}, follow=True)
        self.assertRedirects(response, url("home"))
        self.assertTrue(get_user_model().objects.filter(username="newbie").exists())
        self.assertContains(response, "newbie")
        self.assertContains(response, "Welcome, newbie")

    def test_signup_validation(self):
        response = self.client.post(reverse("signup"), {"username": "x", "password1": "123", "password2": "456"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertTrue(response.context["form"].errors)

    def test_login_and_logout(self):
        make_user("carol")
        response = self.client.post(reverse("login"), {"username": "carol", "password": "pw-Test-12345"})
        self.assertRedirects(response, url("home"))
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, url("home"))
        self.assertEqual(self.client.get(url("watchlist")).status_code, 302)

    def test_bad_login_shows_message(self):
        make_user("carol")
        response = self.client.post(reverse("login"), {"username": "carol", "password": "wrong"})
        self.assertContains(response, "incorrect")

    def test_login_redirects_back_to_next(self):
        make_user("carol")
        response = self.client.post(reverse("login") + "?next=" + url("watchlist"), {"username": "carol", "password": "pw-Test-12345", "next": url("watchlist")})
        self.assertRedirects(response, url("watchlist"))
