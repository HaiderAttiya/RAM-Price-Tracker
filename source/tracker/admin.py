"""
Django admin configuration.

Prices follow the same rule as the rest of the app: a product's price fields
are read-only once it exists and change only through price records, which the
PriceRecord model keeps in sync.
"""

from django.contrib import admin, messages

from .models import PriceRecord, Product, WatchlistItem


class PriceRecordInline(admin.TabularInline):
    model = PriceRecord
    extra = 0
    fields = ("retailer", "price", "recorded_at", "retailer_url")
    ordering = ("-recorded_at",)
    show_change_link = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("brand", "model", "ddr_generation", "capacity_display", "speed_mhz", "cas_latency", "voltage", "price", "best_retailer")
    list_filter = ("ddr_generation", "brand", "capacity_gb", "best_retailer")
    search_fields = ("brand", "model")
    ordering = ("brand", "model")
    inlines = [PriceRecordInline]
    readonly_fields = ("price_updated_at", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        # On an existing product the denormalised price is derived data.
        if obj is not None:
            return self.readonly_fields + ("price", "best_retailer")
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            # A new product starts with one price record (history == price).
            PriceRecord.objects.create(product=obj, retailer=obj.best_retailer, price=obj.price)

    def save_formset(self, request, form, formset, change):
        # Inline price records: save one at a time so each save/delete re-syncs the product price.
        instances = formset.save(commit=False)  # also fills formset.deleted_objects
        for obj in formset.deleted_objects:
            obj.delete()
        for obj in instances:
            obj.save()
        formset.save_m2m()


@admin.register(PriceRecord)
class PriceRecordAdmin(admin.ModelAdmin):
    list_display = ("product", "retailer", "price", "recorded_at")
    list_filter = ("retailer",)
    ordering = ("-recorded_at",)
    raw_id_fields = ("product",)

    def delete_queryset(self, request, queryset):
        # QuerySet.delete() skips PriceRecord.delete(); delete one by one so the
        # product price is recalculated after each removal.
        for record in queryset:
            record.delete()


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "target_price", "created_at")
    search_fields = ("user__username",)
    raw_id_fields = ("user", "product")
