from django.test import TestCase

from tracker.charts import RETAILER_COLORS, build_price_chart

from .helpers import add_record, make_product


class ChartTests(TestCase):
    def test_no_records_returns_none(self):
        self.assertIsNone(build_price_chart([]))

    def test_single_record_still_renders(self):
        product = make_product()
        add_record(product, "150.00")
        chart = build_price_chart(product.price_records.all())
        self.assertIn("<svg", chart["svg"])
        self.assertEqual(len(chart["data"]["series"]), 1)

    def test_one_line_per_retailer_with_fixed_colours(self):
        product = make_product()
        add_record(product, "150.00", retailer="Newegg", days_ago=9)
        add_record(product, "155.00", retailer="Newegg", days_ago=2)
        add_record(product, "160.00", retailer="Best Buy", days_ago=5)
        chart = build_price_chart(product.price_records.all())
        names = [s["name"] for s in chart["data"]["series"]]
        self.assertEqual(names, ["Newegg", "Best Buy"])  # fixed retailer order, not data order
        for series in chart["data"]["series"]:
            self.assertEqual(series["color"], RETAILER_COLORS[series["name"]])
        self.assertEqual(chart["svg"].count("<path"), 2)
        self.assertEqual(chart["svg"].count("<circle"), 2)  # one end-dot per line

    def test_chart_is_accessible_and_has_data_points_in_order(self):
        product = make_product()
        for days in (30, 20, 10):
            add_record(product, "150.00", days_ago=days)
        chart = build_price_chart(product.price_records.all())
        self.assertIn('role="img"', chart["svg"])
        self.assertIn("aria-label", chart["svg"])
        times = [pt[0] for pt in chart["data"]["series"][0]["points"]]
        self.assertEqual(times, sorted(times))
