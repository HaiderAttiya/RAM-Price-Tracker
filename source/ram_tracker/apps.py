"""
Custom AppConfig classes for Django's contrib apps.

django-mongodb-backend does not support Django's integer AutoField, so every
model must use ObjectIdAutoField as its primary key.  The contrib apps declare
their own default_auto_field, so the project-wide DEFAULT_AUTO_FIELD setting
does not override them.  Subclassing their AppConfigs (and listing the
subclasses in INSTALLED_APPS) is the documented fix.
"""

from django.contrib.admin.apps import AdminConfig
from django.contrib.auth.apps import AuthConfig
from django.contrib.contenttypes.apps import ContentTypesConfig


class MongoAdminConfig(AdminConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"


class MongoAuthConfig(AuthConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"


class MongoContentTypesConfig(ContentTypesConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
