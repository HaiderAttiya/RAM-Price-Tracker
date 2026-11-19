from django.urls import path, register_converter

from . import views
from .converters import ObjectIdConverter

register_converter(ObjectIdConverter, "objectid")

app_name = "tracker"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    # Products (CRUD)
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/add/", views.ProductCreateView.as_view(), name="product_create"),
    path("products/<objectid:pk>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("products/<objectid:pk>/edit/", views.ProductUpdateView.as_view(), name="product_update"),
    path("products/<objectid:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),
    # Price history
    path("products/<objectid:product_pk>/prices/add/", views.PriceRecordCreateView.as_view(), name="price_create"),
    path("prices/<objectid:pk>/edit/", views.PriceRecordUpdateView.as_view(), name="price_update"),
    path("prices/<objectid:pk>/delete/", views.PriceRecordDeleteView.as_view(), name="price_delete"),
    # Comparison and deals
    path("compare/", views.compare, name="compare"),
    path("deals/", views.DealsView.as_view(), name="deals"),
    # Watchlist
    path("watchlist/", views.WatchlistView.as_view(), name="watchlist"),
    path("watchlist/add/<objectid:product_pk>/", views.watchlist_add, name="watchlist_add"),
    path("watchlist/<objectid:pk>/edit/", views.WatchlistUpdateView.as_view(), name="watchlist_update"),
    path("watchlist/<objectid:pk>/delete/", views.WatchlistDeleteView.as_view(), name="watchlist_delete"),
]
