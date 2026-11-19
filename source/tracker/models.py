"""
Data model for the RAM Price Tracker.

MongoDB collections (one Django model == one collection):

    products       Product         RAM kits (the catalogue)
    price_records  PriceRecord     price history; many records per product
    watchlist      WatchlistItem   a user's saved product + target price

Relationships (referencing, not embedding):

    Product  1 --- *  PriceRecord    (price_records.product_id -> products._id)
    Product  1 --- *  WatchlistItem  (watchlist.product_id     -> products._id)
    User     1 --- *  WatchlistItem  (watchlist.user_id        -> auth_user._id)

Price history is *referenced* rather than embedded in the product document
because it grows without bound (a new record every time a retailer changes its
price) and MongoDB documents are limited to 16 MB.  Referencing also lets us
index and query the history independently of the product.

Consistency rule
----------------
``Product.price`` is a denormalised copy of the product's *best current price*
(the lowest of each retailer's most recent price).  It makes list pages,
sorting and filtering cheap.  It is NEVER edited directly after creation: it is
recomputed from ``price_records`` every time a record is saved or deleted (see
``Product.refresh_price_from_history``), so the two can not drift apart.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

# ---------------------------------------------------------------------------
# Choice lists
# ---------------------------------------------------------------------------
DDR_CHOICES = [("DDR3", "DDR3"), ("DDR4", "DDR4"), ("DDR5", "DDR5")]

CAPACITY_CHOICES = [(gb, f"{gb} GB") for gb in (4, 8, 16, 24, 32, 48, 64, 96, 128)]

MODULE_CHOICES = [(1, "1 stick"), (2, "2 sticks (kit)"), (4, "4 sticks (kit)")]

RETAILER_CHOICES = [
    ("Amazon", "Amazon"),
    ("Newegg", "Newegg"),
    ("Best Buy", "Best Buy"),
    ("Micro Center", "Micro Center"),
    ("B&H Photo", "B&H Photo"),
]
RETAILER_NAMES = [value for value, _label in RETAILER_CHOICES]

# Plausible (min, max) ranges per DDR generation, used for validation.
SPEED_RANGE = {"DDR3": (800, 2400), "DDR4": (1600, 5600), "DDR5": (4000, 9600)}
CAS_RANGE = {"DDR3": (5, 16), "DDR4": (10, 28), "DDR5": (20, 70)}
VOLTAGE_RANGE = {
    "DDR3": (Decimal("1.20"), Decimal("1.80")),
    "DDR4": (Decimal("1.10"), Decimal("1.60")),
    "DDR5": (Decimal("1.00"), Decimal("1.50")),
}

PRICE_MIN = Decimal("0.01")
PRICE_MAX = Decimal("99999.99")


class Product(models.Model):
    """A RAM kit / module."""

    brand = models.CharField(max_length=50)
    model = models.CharField(
        "model / product line",
        max_length=100,
        help_text="For example: Vengeance RGB, Trident Z5, Fury Beast.",
    )
    ddr_generation = models.CharField("DDR generation", max_length=4, choices=DDR_CHOICES)
    capacity_gb = models.PositiveSmallIntegerField("total capacity", choices=CAPACITY_CHOICES)
    modules = models.PositiveSmallIntegerField("number of sticks", choices=MODULE_CHOICES, default=2)
    speed_mhz = models.PositiveIntegerField(
        "speed (MHz)",
        help_text="Marketed speed rating, e.g. 6000 for DDR5-6000.",
    )
    cas_latency = models.PositiveSmallIntegerField("CAS latency (CL)", help_text="e.g. 30 for CL30.")
    voltage = models.DecimalField("voltage (V)", max_digits=3, decimal_places=2, help_text="e.g. 1.35")

    # --- denormalised from price_records (see module docstring) -------------
    price = models.DecimalField(
        "best current price",
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(PRICE_MIN)],
    )
    best_retailer = models.CharField("best price at", max_length=30, choices=RETAILER_CHOICES)
    price_updated_at = models.DateTimeField(null=True, blank=True, editable=False)
    # -------------------------------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["brand", "model"]
        constraints = [
            # The same kit can not be catalogued twice.  This also creates a
            # unique index whose prefix (brand, model, ...) speeds up brand lookups.
            models.UniqueConstraint(
                fields=["brand", "model", "ddr_generation", "capacity_gb", "modules", "speed_mhz", "cas_latency"],
                name="product_variant_unique",
                violation_error_message=(
                    "This exact kit (brand, model, DDR generation, capacity, sticks, speed and CL) "
                    "is already in the catalogue."
                ),
            ),
        ]
        indexes = [
            # Supports the main filter/sort query: DDR generation + capacity,
            # then a price range / price ordering (equality, equality, range/sort).
            models.Index(fields=["ddr_generation", "capacity_gb", "price"], name="prod_ddr_cap_price_idx"),
        ]

    def __str__(self):
        return f"{self.brand} {self.model} {self.capacity_gb}GB {self.ddr_generation}-{self.speed_mhz} CL{self.cas_latency}"

    def get_absolute_url(self):
        return reverse("tracker:product_detail", kwargs={"pk": str(self.pk)})

    # --- validation ------------------------------------------------------------
    def clean(self):
        """Cross-field validation (ranges depend on the DDR generation)."""
        super().clean()
        gen = self.ddr_generation
        if gen not in SPEED_RANGE:
            return
        errors = {}
        if self.speed_mhz is not None:
            low, high = SPEED_RANGE[gen]
            if not low <= self.speed_mhz <= high:
                errors["speed_mhz"] = f"{gen} speeds are normally between {low} and {high} MHz."
        if self.cas_latency is not None:
            low, high = CAS_RANGE[gen]
            if not low <= self.cas_latency <= high:
                errors["cas_latency"] = f"{gen} CAS latency is normally between CL{low} and CL{high}."
        if self.voltage is not None:
            low, high = VOLTAGE_RANGE[gen]
            if not low <= self.voltage <= high:
                errors["voltage"] = f"{gen} voltage is normally between {low} V and {high} V."
        if self.capacity_gb and self.modules and self.capacity_gb % self.modules:
            errors["modules"] = f"{self.capacity_gb} GB can not be split evenly across {self.modules} sticks."
        if errors:
            raise ValidationError(errors)

    # --- derived values (calculated, never stored) -----------------------------
    @property
    def capacity_display(self):
        """'32 GB (2 x 16 GB)' or '16 GB' for a single stick."""
        if self.modules and self.modules > 1:
            return f"{self.capacity_gb} GB ({self.modules} × {self.capacity_gb // self.modules} GB)"
        return f"{self.capacity_gb} GB"

    @property
    def spec_summary(self):
        return f"{self.ddr_generation}-{self.speed_mhz}, CL{self.cas_latency}, {self.voltage} V"

    @property
    def latency_ns(self):
        """
        True (first-word) latency in nanoseconds:  CL x 2000 / speed(MHz).

        This is the standard way to compare kits with different speeds, e.g.
        DDR5-6000 CL30 -> 10.00 ns, DDR4-3200 CL16 -> 10.00 ns.
        """
        if not self.speed_mhz:
            return None
        return (Decimal(self.cas_latency) * 2000 / Decimal(self.speed_mhz)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def price_per_gb(self):
        if not self.capacity_gb or self.price is None:
            return None
        return (self.price / Decimal(self.capacity_gb)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # --- price synchronisation -------------------------------------------------
    def latest_prices_by_retailer(self):
        """Each retailer's most recent PriceRecord for this product, cheapest first."""
        latest = []
        for retailer in RETAILER_NAMES:
            record = self.price_records.filter(retailer=retailer).order_by("-recorded_at").first()
            if record is not None:
                latest.append(record)
        latest.sort(key=lambda r: (r.price, -r.recorded_at.timestamp()))
        return latest

    def refresh_price_from_history(self):
        """
        Recompute ``price`` / ``best_retailer`` / ``price_updated_at`` from the
        price_records collection.

        Rule: take each retailer's MOST RECENT record, then keep the cheapest.
        If the product has no records at all the stored values are left alone.
        Returns True when the product document was changed.
        """
        latest = self.latest_prices_by_retailer()
        if not latest:
            return False
        best = latest[0]
        newest = max(r.recorded_at for r in latest)
        if (self.price, self.best_retailer, self.price_updated_at) == (best.price, best.retailer, newest):
            return False
        self.price, self.best_retailer, self.price_updated_at = best.price, best.retailer, newest
        self.save(update_fields=["price", "best_retailer", "price_updated_at", "updated_at"])
        return True


class PriceRecord(models.Model):
    """One observed price for a product at one retailer at one moment."""

    # db_index=False: the compound index below already starts with "product".
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="price_records", db_index=False)
    retailer = models.CharField(max_length=30, choices=RETAILER_CHOICES)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(PRICE_MIN)])
    recorded_at = models.DateTimeField("recorded at", default=timezone.now)
    retailer_url = models.URLField("link to the offer", blank=True, max_length=500)

    class Meta:
        db_table = "price_records"
        ordering = ["-recorded_at"]
        indexes = [
            # Price history of one product, newest first (equality + sort).
            models.Index(fields=["product", "-recorded_at"], name="price_product_time_idx"),
            # Time-window scans (e.g. "everything in the last 90 days").
            models.Index(fields=["recorded_at"], name="price_time_idx"),
        ]

    def __str__(self):
        return f"{self.retailer}: {self.price} on {self.recorded_at:%Y-%m-%d}"

    def clean(self):
        super().clean()
        if self.recorded_at and self.recorded_at > timezone.now() + timedelta(minutes=5):
            raise ValidationError({"recorded_at": "A price can not be recorded in the future."})

    # Saving / deleting a record keeps Product.price in step with the history.
    # (QuerySet.delete() bypasses these hooks - used only for cascades when the
    # whole product is being deleted, where syncing would be pointless.)
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.refresh_price_from_history()

    def delete(self, *args, **kwargs):
        product = self.product
        result = super().delete(*args, **kwargs)
        product.refresh_price_from_history()
        return result


class WatchlistItem(models.Model):
    """A product a user is tracking, with the price they would like to pay."""

    # db_index=False: the unique (user, product) index below already starts with "user".
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlist_items", db_index=False
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="watchers")
    target_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(PRICE_MIN)],
        help_text="You will be flagged when the best price drops to this level or lower.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "watchlist"
        ordering = ["-created_at"]
        constraints = [
            # One entry per user per product; its index also serves
            # "show me this user's watchlist" (prefix = user).
            models.UniqueConstraint(
                fields=["user", "product"],
                name="watchlist_user_product_uniq",
                violation_error_message="This product is already on your watchlist.",
            ),
        ]

    def __str__(self):
        return f"{self.user} -> {self.product} @ {self.target_price}"

    @property
    def target_reached(self):
        return self.product.price <= self.target_price
