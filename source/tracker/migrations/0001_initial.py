import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import django_mongodb_backend.fields
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                (
                    "id",
                    django_mongodb_backend.fields.ObjectIdAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("brand", models.CharField(max_length=50)),
                (
                    "model",
                    models.CharField(
                        help_text="For example: Vengeance RGB, Trident Z5, Fury Beast.",
                        max_length=100,
                        verbose_name="model / product line",
                    ),
                ),
                (
                    "ddr_generation",
                    models.CharField(
                        choices=[("DDR3", "DDR3"), ("DDR4", "DDR4"), ("DDR5", "DDR5")],
                        max_length=4,
                        verbose_name="DDR generation",
                    ),
                ),
                (
                    "capacity_gb",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (4, "4 GB"),
                            (8, "8 GB"),
                            (16, "16 GB"),
                            (24, "24 GB"),
                            (32, "32 GB"),
                            (48, "48 GB"),
                            (64, "64 GB"),
                            (96, "96 GB"),
                            (128, "128 GB"),
                        ],
                        verbose_name="total capacity",
                    ),
                ),
                (
                    "modules",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "1 stick"),
                            (2, "2 sticks (kit)"),
                            (4, "4 sticks (kit)"),
                        ],
                        default=2,
                        verbose_name="number of sticks",
                    ),
                ),
                (
                    "speed_mhz",
                    models.PositiveIntegerField(
                        help_text="Marketed speed rating, e.g. 6000 for DDR5-6000.",
                        verbose_name="speed (MHz)",
                    ),
                ),
                (
                    "cas_latency",
                    models.PositiveSmallIntegerField(
                        help_text="e.g. 30 for CL30.", verbose_name="CAS latency (CL)"
                    ),
                ),
                (
                    "voltage",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="e.g. 1.35",
                        max_digits=3,
                        verbose_name="voltage (V)",
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=8,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                        verbose_name="best current price",
                    ),
                ),
                (
                    "best_retailer",
                    models.CharField(
                        choices=[
                            ("Amazon", "Amazon"),
                            ("Newegg", "Newegg"),
                            ("Best Buy", "Best Buy"),
                            ("Micro Center", "Micro Center"),
                            ("B&H Photo", "B&H Photo"),
                        ],
                        max_length=30,
                        verbose_name="best price at",
                    ),
                ),
                (
                    "price_updated_at",
                    models.DateTimeField(blank=True, editable=False, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "products",
                "ordering": ["brand", "model"],
                "indexes": [
                    models.Index(
                        fields=["ddr_generation", "capacity_gb", "price"],
                        name="prod_ddr_cap_price_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=(
                            "brand",
                            "model",
                            "ddr_generation",
                            "capacity_gb",
                            "modules",
                            "speed_mhz",
                            "cas_latency",
                        ),
                        name="product_variant_unique",
                        violation_error_message="This exact kit (brand, model, DDR generation, capacity, sticks, speed and CL) is already in the catalogue.",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="PriceRecord",
            fields=[
                (
                    "id",
                    django_mongodb_backend.fields.ObjectIdAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "retailer",
                    models.CharField(
                        choices=[
                            ("Amazon", "Amazon"),
                            ("Newegg", "Newegg"),
                            ("Best Buy", "Best Buy"),
                            ("Micro Center", "Micro Center"),
                            ("B&H Photo", "B&H Photo"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=8,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                (
                    "recorded_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="recorded at"
                    ),
                ),
                (
                    "retailer_url",
                    models.URLField(
                        blank=True, max_length=500, verbose_name="link to the offer"
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="price_records",
                        to="tracker.product",
                    ),
                ),
            ],
            options={
                "db_table": "price_records",
                "ordering": ["-recorded_at"],
                "indexes": [
                    models.Index(
                        fields=["product", "-recorded_at"],
                        name="price_product_time_idx",
                    ),
                    models.Index(fields=["recorded_at"], name="price_time_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="WatchlistItem",
            fields=[
                (
                    "id",
                    django_mongodb_backend.fields.ObjectIdAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "target_price",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="You will be flagged when the best price drops to this level or lower.",
                        max_digits=8,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="watchers",
                        to="tracker.product",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="watchlist_items",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "watchlist",
                "ordering": ["-created_at"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "product"),
                        name="watchlist_user_product_uniq",
                        violation_error_message="This product is already on your watchlist.",
                    )
                ],
            },
        ),
    ]
