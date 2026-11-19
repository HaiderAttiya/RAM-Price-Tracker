from decimal import Decimal

from django.test import TestCase, override_settings

from tracker.services import (
    LEVEL_DEAL,
    LEVEL_GREAT,
    LEVEL_NONE,
    LEVEL_UNKNOWN,
    best_value_flags,
    classify,
    find_deals,
    get_deal_info,
    get_deal_infos,
)

from .helpers import add_record, make_product, product_with_history

D = Decimal


class ClassifyFormulaTests(TestCase):
    """The pure formula: discount = (baseline - current) / baseline * 100."""

    def test_exactly_ten_percent_is_a_deal(self):
        info = classify(D("90.00"), D("100.00"), 5)
        self.assertEqual(info.discount_percent, D("10.0"))
        self.assertEqual(info.level, LEVEL_DEAL)
        self.assertTrue(info.is_deal)

    def test_just_under_threshold_is_not_a_deal(self):
        info = classify(D("90.01"), D("100.00"), 5)  # exactly 9.99% off
        self.assertEqual(info.level, LEVEL_NONE)
        self.assertEqual(info.discount_percent, D("9.9"))  # never rounded UP to 10.0

    def test_twenty_percent_is_a_great_deal(self):
        info = classify(D("80.00"), D("100.00"), 5)
        self.assertEqual(info.discount_percent, D("20.0"))
        self.assertEqual(info.level, LEVEL_GREAT)

    def test_price_above_baseline_gives_negative_discount(self):
        info = classify(D("110.00"), D("100.00"), 5)
        self.assertEqual(info.discount_percent, D("-10.0"))
        self.assertFalse(info.is_deal)

    def test_too_few_records_means_no_verdict(self):
        info = classify(D("50.00"), D("100.00"), 2)  # huge drop but only 2 records
        self.assertEqual(info.level, LEVEL_UNKNOWN)
        self.assertIsNone(info.discount_percent)

    def test_no_baseline_means_no_verdict(self):
        self.assertEqual(classify(D("50.00"), None, 0).level, LEVEL_UNKNOWN)

    @override_settings(DEAL_THRESHOLD_PERCENT=5)
    def test_threshold_comes_from_settings(self):
        self.assertEqual(classify(D("94.00"), D("100.00"), 5).level, LEVEL_DEAL)


class DealQueryTests(TestCase):
    def test_deal_uses_the_best_retailers_own_history(self):
        # Amazon: 100,100,100 then a drop to 80 (newest).  Newegg is steady at 120.
        product = make_product()
        for age, price in ((40, "100"), (30, "100"), (20, "100"), (1, "80")):
            add_record(product, price, retailer="Amazon", days_ago=age)
        for age in (35, 25, 10, 1):
            add_record(product, "120", retailer="Newegg", days_ago=age)
        product.refresh_from_db()
        self.assertEqual((product.price, product.best_retailer), (D("80.00"), "Amazon"))

        info = get_deal_info(product)
        # baseline = mean(100,100,100,80) = 95 -> NOT the 4 Newegg records
        self.assertEqual(info.baseline_price, D("95.00"))
        self.assertEqual(info.record_count, 4)
        self.assertEqual(info.discount_percent, D("15.7"))  # exact 15.789..., shown truncated
        self.assertEqual(info.level, LEVEL_DEAL)

    def test_records_outside_the_window_are_ignored(self):
        # three very old records at 200 must not inflate the baseline
        product = product_with_history([(200, 200), (200, 150), (200, 120), (100, 30), (100, 20), (100, 10), (100, 0)])
        info = get_deal_info(product)
        self.assertEqual(info.record_count, 4)
        self.assertEqual(info.baseline_price, D("100.00"))
        self.assertEqual(info.level, LEVEL_NONE)

    def test_batch_lookup_returns_one_entry_per_product(self):
        a = product_with_history([(100, 30), (100, 20), (100, 10), (70, 0)])
        b = product_with_history([(100, 30), (100, 20)])
        infos = get_deal_infos([a, b])
        self.assertEqual(set(infos), {a.pk, b.pk})
        self.assertTrue(infos[a.pk].is_deal)
        self.assertEqual(infos[b.pk].level, LEVEL_UNKNOWN)

    def test_empty_input(self):
        self.assertEqual(get_deal_infos([]), {})

    def test_find_deals_sorted_by_biggest_discount(self):
        small = product_with_history([(100, 30), (100, 20), (100, 10), (85, 0)])
        big = product_with_history([(100, 30), (100, 20), (100, 10), (60, 0)])
        steady = product_with_history([(100, 30), (100, 20), (100, 10), (100, 0)])
        deals = find_deals()
        self.assertEqual([p.pk for p, _ in deals], [big.pk, small.pk])
        self.assertNotIn(steady.pk, [p.pk for p, _ in deals])


class BestValueTests(TestCase):
    def test_winners_per_row_and_ties(self):
        cheap = make_product(price=D("90.00"), capacity_gb=16, speed_mhz=5200, cas_latency=40)
        fast = make_product(price=D("200.00"), capacity_gb=32, speed_mhz=6400, cas_latency=32)
        tie = make_product(price=D("200.00"), capacity_gb=32, speed_mhz=6400, cas_latency=32)
        best = best_value_flags([cheap, fast, tie])
        self.assertEqual(best["price"], {cheap.pk})
        self.assertEqual(best["capacity"], {fast.pk, tie.pk})           # ties share the win
        self.assertEqual(best["speed"], {fast.pk, tie.pk})
        self.assertEqual(best["latency"], {fast.pk, tie.pk})            # 10.00 ns beats 15.38 ns
        self.assertEqual(best["price_per_gb"], {cheap.pk})              # 90/16 = 5.63 beats 200/32 = 6.25
