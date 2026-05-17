import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_add_passport_nda'),
        ('inventory', '0007_city_and_pickup_point'),  # City создаётся там
    ]

    operations = [
        migrations.AddField(
            model_name='owner',
            name='home_city',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='owners',
                to='inventory.city',
                verbose_name='Город',
            ),
        ),
    ]
