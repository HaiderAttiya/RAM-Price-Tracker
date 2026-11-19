from django.apps import AppConfig


class TrackerConfig(AppConfig):
    # Required by django-mongodb-backend: ObjectId primary keys.
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "tracker"
    verbose_name = "RAM Price Tracker"
