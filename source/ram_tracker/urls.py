from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.templatetags.static import static
from django.urls import include, path
from django.views.generic import RedirectView

from tracker.views import SignUpView

admin.site.site_header = "RAM Price Tracker administration"
admin.site.site_title = "RAM Price Tracker admin"
admin.site.index_title = "Manage products, price records and watchlists"

urlpatterns = [
    path("admin/", admin.site.urls),
    # Authentication (Django's built-in views; templates live in templates/registration/)
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("favicon.ico", RedirectView.as_view(url=static("favicon.svg"), permanent=True)),
    path("", include("tracker.urls")),
]

handler404 = "tracker.views.page_not_found"
