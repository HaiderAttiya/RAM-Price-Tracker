import django.core.validators
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pricerecord',
            name='price',
            field=models.DecimalField(decimal_places=3, max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.001'))]),
        ),
        migrations.AlterField(
            model_name='pricerecord',
            name='retailer',
            field=models.CharField(choices=[('Amazon', 'Amazon'), ('Computia', 'Computia'), ('Cazasouq', 'Cazasouq'), ('Advanti', 'Advanti')], max_length=30),
        ),
        migrations.AlterField(
            model_name='product',
            name='best_retailer',
            field=models.CharField(choices=[('Amazon', 'Amazon'), ('Computia', 'Computia'), ('Cazasouq', 'Cazasouq'), ('Advanti', 'Advanti')], max_length=30, verbose_name='best price at'),
        ),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(decimal_places=3, max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.001'))], verbose_name='best current price'),
        ),
        migrations.AlterField(
            model_name='watchlistitem',
            name='target_price',
            field=models.DecimalField(decimal_places=3, help_text='You will be flagged when the best price drops to this level or lower.', max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.001'))]),
        ),
    ]
