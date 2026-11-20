"""Django forms (the validation layer between the browser and MongoDB)."""

from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from .models import (
    CAPACITY_CHOICES,
    DDR_CHOICES,
    PRICE_MAX,
    PRICE_MIN,
    PriceRecord,
    Product,
    WatchlistItem,
)

DATETIME_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"


class BootstrapFormMixin:
    """Give every widget the right Bootstrap 5 CSS class."""

    def _style_widgets(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_widgets()

    def full_clean(self):
        """
        Validate, then mark invalid fields so Bootstrap shows them in red.

        This must happen here and NOT in __init__: touching self.errors in
        __init__ would validate the form before subclasses finish setting up
        (e.g. the database-driven brand choices of ProductFilterForm).
        """
        super().full_clean()
        for name in self._errors or {}:
            if name in self.fields:
                widget = self.fields[name].widget
                if "is-invalid" not in widget.attrs.get("class", ""):
                    widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
class ProductEditForm(BootstrapFormMixin, forms.ModelForm):
    """Edit the specifications of a product (not its price - see ProductCreateForm)."""

    class Meta:
        model = Product
        fields = ["brand", "model", "ddr_generation", "capacity_gb", "modules", "speed_mhz", "cas_latency", "voltage"]
        widgets = {
            "voltage": forms.NumberInput(attrs={"step": "0.01", "min": "1.00", "max": "1.80"}),
            "speed_mhz": forms.NumberInput(attrs={"step": "1", "min": "800"}),
            "cas_latency": forms.NumberInput(attrs={"step": "1", "min": "5"}),
        }

    def clean_brand(self):
        """Collapse whitespace and reuse the existing spelling of a brand (corsair -> Corsair)."""
        brand = " ".join(self.cleaned_data["brand"].split())
        existing = Product.objects.filter(brand__iexact=brand).values_list("brand", flat=True).first()
        return existing or brand

    def clean_model(self):
        return " ".join(self.cleaned_data["model"].split())


class ProductCreateForm(ProductEditForm):
    """
    Create a product.  A product always starts with one price record, so the
    form also asks for the first price and where it was seen.  After creation
    prices are changed only by adding price records.
    """

    class Meta(ProductEditForm.Meta):
        fields = ProductEditForm.Meta.fields + ["price", "best_retailer"]
        labels = {"price": "Starting price", "best_retailer": "Seen at (retailer)"}
        widgets = {
            **ProductEditForm.Meta.widgets,
            "price": forms.NumberInput(attrs={"step": "0.001", "min": str(PRICE_MIN), "max": str(PRICE_MAX)}),
        }
        help_texts = {
            "price": "This becomes the first entry in the price history.",
            "best_retailer": "",
        }


# ---------------------------------------------------------------------------
# Price records
# ---------------------------------------------------------------------------
class PriceRecordForm(BootstrapFormMixin, forms.ModelForm):
    recorded_at = forms.DateTimeField(
        label="Recorded at",
        input_formats=[DATETIME_LOCAL_FORMAT, "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DATETIME_LOCAL_FORMAT),
    )

    class Meta:
        model = PriceRecord
        fields = ["retailer", "price", "recorded_at", "retailer_url"]
        widgets = {
            "price": forms.NumberInput(attrs={"step": "0.001", "min": str(PRICE_MIN), "max": str(PRICE_MAX)}),
            "retailer_url": forms.URLInput(attrs={"placeholder": "https://… (optional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.instance.pk:
            self.initial["recorded_at"] = timezone.localtime().replace(second=0, microsecond=0)
        elif not self.is_bound and self.instance.pk:
            self.initial["recorded_at"] = timezone.localtime(self.instance.recorded_at).replace(
                second=0, microsecond=0
            )


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------
class WatchlistForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = WatchlistItem
        fields = ["target_price"]
        labels = {"target_price": "Target price"}
        widgets = {
            "target_price": forms.NumberInput(attrs={"step": "0.001", "min": str(PRICE_MIN), "max": str(PRICE_MAX)}),
        }


# ---------------------------------------------------------------------------
# Search / filter (a plain Form: it is read from the query string, never saved)
# ---------------------------------------------------------------------------
SORT_CHOICES = [
    ("name", "Name (A–Z)"),
    ("price_asc", "Price: low to high"),
    ("price_desc", "Price: high to low"),
    ("capacity_desc", "Capacity: high to low"),
    ("speed_desc", "Speed: high to low"),
    ("recent", "Recently updated"),
]
SORT_FIELDS = {
    "name": ["brand", "model", "capacity_gb"],
    "price_asc": ["price", "brand"],
    "price_desc": ["-price", "brand"],
    "capacity_desc": ["-capacity_gb", "price"],
    "speed_desc": ["-speed_mhz", "price"],
    "recent": ["-price_updated_at", "brand"],
}


class ProductFilterForm(BootstrapFormMixin, forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Brand or model, e.g. corsair vengeance"}),
    )
    brand = forms.ChoiceField(required=False, label="Brand")
    ddr_generation = forms.ChoiceField(required=False, label="DDR generation", choices=[("", "Any")] + DDR_CHOICES)
    capacity_gb = forms.TypedChoiceField(
        required=False, label="Capacity", coerce=int, empty_value=None, choices=[("", "Any")] + CAPACITY_CHOICES
    )
    min_price = forms.DecimalField(
        required=False, label="Min price", min_value=Decimal("0"), max_digits=8, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "1", "min": "0", "placeholder": "0"}),
    )
    max_price = forms.DecimalField(
        required=False, label="Max price", min_value=Decimal("0"), max_digits=8, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "1", "min": "0", "placeholder": "Any"}),
    )
    sort = forms.ChoiceField(required=False, label="Sort by", choices=SORT_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        brands = sorted(set(Product.objects.order_by().values_list("brand", flat=True).distinct()), key=str.lower)
        self.fields["brand"].choices = [("", "Any")] + [(b, b) for b in brands]

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("min_price"), cleaned.get("max_price")
        if low is not None and high is not None and low > high:
            self.add_error("max_price", "Max price must be greater than or equal to min price.")
        return cleaned


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
class SignUpForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=False, help_text="Optional.")

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")
