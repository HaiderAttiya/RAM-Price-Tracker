"""
Views (the "V" in Django's MVT).

Class-based generic views are used for plain CRUD; small function views are
used where the logic is custom (comparison, watchlist add).  Anything that
changes data requires a logged-in user; browsing, searching and comparing is
open to everyone.
"""

import re
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from .charts import build_price_chart
from .forms import (
    SORT_FIELDS,
    PriceRecordForm,
    ProductCreateForm,
    ProductEditForm,
    ProductFilterForm,
    SignUpForm,
    WatchlistForm,
)
from .models import CAS_RANGE, SPEED_RANGE, VOLTAGE_RANGE, PriceRecord, Product, WatchlistItem
from .services import best_value_flags, find_deals, get_deal_info, get_deal_infos

OBJECT_ID_RE = re.compile(r"^[0-9a-f]{24}$")
MAX_COMPARE = 4
CHART_RANGES = {"30": 30, "90": 90, "180": 180, "all": None}


def spec_ranges():
    """Accepted spec ranges per DDR generation, shown next to the product form."""
    return [
        {"generation": gen, "speed": SPEED_RANGE[gen], "cas": CAS_RANGE[gen], "voltage": VOLTAGE_RANGE[gen]}
        for gen in ("DDR3", "DDR4", "DDR5")
    ]


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
class HomeView(TemplateView):
    template_name = "tracker/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        deals = find_deals()
        ctx["deals"] = deals[:5]
        ctx["deal_count"] = len(deals)
        ctx["product_count"] = Product.objects.count()
        ctx["record_count"] = PriceRecord.objects.count()
        ctx["recent_products"] = Product.objects.order_by("-price_updated_at")[:6]
        return ctx


# ---------------------------------------------------------------------------
# Products: list / search / filter
# ---------------------------------------------------------------------------
class ProductListView(ListView):
    template_name = "tracker/product_list.html"
    context_object_name = "products"
    paginate_by = settings.PRODUCTS_PER_PAGE

    def get_queryset(self):
        self.filter_form = ProductFilterForm(self.request.GET)
        self.filter_form.is_valid()  # populates cleaned_data; invalid fields are simply left out
        data = self.filter_form.cleaned_data
        qs = Product.objects.all()

        for term in (data.get("q") or "").split():
            qs = qs.filter(
                Q(brand__icontains=term) | Q(model__icontains=term) | Q(ddr_generation__icontains=term)
            )
        if data.get("brand"):
            qs = qs.filter(brand=data["brand"])
        if data.get("ddr_generation"):
            qs = qs.filter(ddr_generation=data["ddr_generation"])
        if data.get("capacity_gb"):
            qs = qs.filter(capacity_gb=data["capacity_gb"])
        if data.get("min_price") is not None:
            qs = qs.filter(price__gte=data["min_price"])
        if data.get("max_price") is not None:
            qs = qs.filter(price__lte=data["max_price"])
        return qs.order_by(*SORT_FIELDS.get(data.get("sort") or "name"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        products = list(ctx["page_obj"].object_list)
        infos = get_deal_infos(products)
        for product in products:
            product.deal = infos[product.pk]
        watched = set()
        if self.request.user.is_authenticated and products:
            watched = set(
                WatchlistItem.objects.filter(user=self.request.user, product__in=[p.pk for p in products])
                .values_list("product_id", flat=True)
            )
        for product in products:
            product.is_watched = product.pk in watched
        ctx["products"] = products
        ctx["filter_form"] = self.filter_form
        ctx["total"] = ctx["paginator"].count
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        ctx["has_filters"] = any(self.request.GET.get(k) for k in ("q", "brand", "ddr_generation", "capacity_gb", "min_price", "max_price"))
        ctx["max_compare"] = MAX_COMPARE
        return ctx


# ---------------------------------------------------------------------------
# Products: detail
# ---------------------------------------------------------------------------
class ProductDetailView(DetailView):
    model = Product
    template_name = "tracker/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.object
        request = self.request

        # --- chart (range filter) ---
        range_key = request.GET.get("range", "90")
        if range_key not in CHART_RANGES:
            range_key = "90"
        history = product.price_records.all()
        days = CHART_RANGES[range_key]
        if days:
            history = history.filter(recorded_at__gte=timezone.now() - timedelta(days=days))
        ctx["chart"] = build_price_chart(history)
        ctx["range_key"] = range_key
        ctx["range_options"] = [("30", "30 days"), ("90", "90 days"), ("180", "180 days"), ("all", "All")]

        # --- full history table, paginated (newest first; uses price_product_time_idx) ---
        paginator = Paginator(product.price_records.order_by("-recorded_at"), 12)
        ctx["history_page"] = paginator.get_page(request.GET.get("history"))
        ctx["record_total"] = paginator.count

        # --- other data ---
        ctx["deal"] = get_deal_info(product)
        ctx["retailer_prices"] = product.latest_prices_by_retailer()
        if request.user.is_authenticated:
            item = WatchlistItem.objects.filter(user=request.user, product=product).first()
            ctx["watch_item"] = item
            suggested = (product.price * Decimal("0.90")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            ctx["watch_form"] = WatchlistForm(
                initial={"target_price": item.target_price if item else suggested}
            )
        return ctx


# ---------------------------------------------------------------------------
# Products: create / edit / delete
# ---------------------------------------------------------------------------
class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only administrators can access management pages."""

    def test_func(self):
        return self.request.user.is_staff
class ProductCreateView(AdminRequiredMixin, CreateView):
    model = Product
    form_class = ProductCreateForm
    template_name = "tracker/product_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        # Every product starts with one price record so history and price agree.
        PriceRecord.objects.create(
            product=self.object,
            retailer=self.object.best_retailer,
            price=self.object.price,
            recorded_at=timezone.now(),
        )
        messages.success(self.request, f"Added {self.object}. Its first price has been recorded.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(heading="Add a RAM product", submit_label="Add product", ranges=spec_ranges())
        return ctx


class ProductUpdateView(AdminRequiredMixin, UpdateView):
    model = Product
    form_class = ProductEditForm
    template_name = "tracker/product_form.html"

    def form_valid(self, form):
        messages.success(self.request, f"Saved changes to {self.object}.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(heading=f"Edit {self.object}", submit_label="Save changes", editing=True, ranges=spec_ranges())
        return ctx


class ProductDeleteView(AdminRequiredMixin, DeleteView):
    model = Product
    template_name = "tracker/product_confirm_delete.html"
    success_url = reverse_lazy("tracker:product_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["record_count"] = self.object.price_records.count()
        ctx["watcher_count"] = self.object.watchers.count()
        return ctx

    def form_valid(self, form):
        name = str(self.object)
        messages.success(self.request, f"Deleted {name}, its price history and any watchlist entries for it.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Price records
# ---------------------------------------------------------------------------
class PriceRecordCreateView(AdminRequiredMixin, CreateView):
    model = PriceRecord
    form_class = PriceRecordForm
    template_name = "tracker/pricerecord_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs["product_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = PriceRecord(product=self.product)
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Recorded {settings.CURRENCY_SYMBOL}{form.cleaned_data['price']} at {form.cleaned_data['retailer']}.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("tracker:product_detail", kwargs={"pk": str(self.product.pk)}) + "#history"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(product=self.product, heading="Record a new price", submit_label="Save price")
        return ctx


class PriceRecordUpdateView(AdminRequiredMixin, UpdateView):
    model = PriceRecord
    form_class = PriceRecordForm
    template_name = "tracker/pricerecord_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Price record updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("tracker:product_detail", kwargs={"pk": str(self.object.product_id)}) + "#history"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(product=self.object.product, heading="Edit price record", submit_label="Save changes")
        return ctx


class PriceRecordDeleteView(AdminRequiredMixin, DeleteView):
    model = PriceRecord
    template_name = "tracker/pricerecord_confirm_delete.html"

    def get_success_url(self):
        return reverse("tracker:product_detail", kwargs={"pk": str(self.object.product_id)}) + "#history"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_only_record"] = self.object.product.price_records.count() <= 1
        return ctx

    def form_valid(self, form):
        if self.object.product.price_records.count() <= 1:
            messages.error(self.request, "A product needs at least one price record, so the last one can not be deleted.")
            return redirect(self.get_success_url())
        messages.success(self.request, "Price record deleted. The product's best price has been recalculated.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------
def compare(request):
    """Side-by-side comparison of 2-4 products chosen with ?ids=<id>&ids=<id>..."""
    ids = []
    for raw in request.GET.getlist("ids"):
        if OBJECT_ID_RE.match(raw) and raw not in ids:
            ids.append(raw)

    if len(ids) < 2:
        messages.warning(request, "Tick at least two products on the list, then press Compare.")
        return redirect("tracker:product_list")
    if len(ids) > MAX_COMPARE:
        messages.warning(request, f"You can compare up to {MAX_COMPARE} products at once. Showing the first {MAX_COMPARE}.")
        ids = ids[:MAX_COMPARE]

    found = {str(p.pk): p for p in Product.objects.filter(pk__in=ids)}
    products = [found[i] for i in ids if i in found]  # keep the order the user picked
    if len(products) < 2:
        messages.error(request, "Some of the selected products no longer exist.")
        return redirect("tracker:product_list")

    infos = get_deal_infos(products)
    for product in products:
        product.deal = infos[product.pk]
        product.remove_url = (
            reverse("tracker:compare") + "?" + "&".join(f"ids={p.pk}" for p in products if p.pk != product.pk)
            if len(products) > 2
            else ""
        )
    return render(request, "tracker/compare.html", {"products": products, "best": best_value_flags(products)})


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------
class DealsView(TemplateView):
    template_name = "tracker/deals.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["deals"] = find_deals()
        return ctx


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------
class WatchlistView(LoginRequiredMixin, TemplateView):
    template_name = "tracker/watchlist.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        items = list(WatchlistItem.objects.filter(user=self.request.user))
        products = Product.objects.in_bulk([i.product_id for i in items])
        by_id = {str(k): v for k, v in products.items()}
        rows = []
        infos = get_deal_infos(by_id.values())
        for item in items:
            product = by_id.get(str(item.product_id))
            if product is None:
                continue
            item.product = product
            gap = product.price - item.target_price
            rows.append({"item": item, "product": product, "deal": infos[product.pk], "gap": gap})
        # Items whose target is reached first, then the closest to their target.
        rows.sort(key=lambda r: (r["gap"] > 0, r["gap"]))
        ctx["rows"] = rows
        ctx["reached_count"] = sum(1 for r in rows if r["gap"] <= 0)
        ctx["waiting_count"] = len(rows) - ctx["reached_count"]
        return ctx


@login_required
@require_POST
def watchlist_add(request, product_pk):
    """Add a product to the watchlist, or change the target if it is already there."""
    product = get_object_or_404(Product, pk=product_pk)
    form = WatchlistForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a target price greater than zero. " + " ".join(form.errors.get("target_price", [])))
        return redirect(product)
    target = form.cleaned_data["target_price"]
    item = WatchlistItem.objects.filter(user=request.user, product=product).first()
    if item:
        item.target_price = target
        item.save()
        messages.success(request, f"Target price updated to {settings.CURRENCY_SYMBOL}{target}.")
    else:
        WatchlistItem.objects.create(user=request.user, product=product, target_price=target)
        messages.success(request, f"Added to your watchlist with a target of {settings.CURRENCY_SYMBOL}{target}.")
    return redirect(product)


class OwnWatchlistItemMixin(LoginRequiredMixin):
    """Users can only see and change their own watchlist entries (others give 404)."""

    model = WatchlistItem

    def get_queryset(self):
        return WatchlistItem.objects.filter(user=self.request.user)


class WatchlistUpdateView(OwnWatchlistItemMixin, UpdateView):
    form_class = WatchlistForm
    template_name = "tracker/watchlist_form.html"
    success_url = reverse_lazy("tracker:watchlist")

    def form_valid(self, form):
        messages.success(self.request, "Target price updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["product"] = self.object.product
        return ctx


class WatchlistDeleteView(OwnWatchlistItemMixin, DeleteView):
    template_name = "tracker/watchlist_confirm_delete.html"
    success_url = reverse_lazy("tracker:watchlist")

    def form_valid(self, form):
        messages.success(self.request, "Removed from your watchlist.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("tracker:home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("tracker:home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, f"Welcome, {self.object.username}. Your account is ready.")
        return response
