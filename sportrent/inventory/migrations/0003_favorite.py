import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('inventory', '0002_inventory_reviews_count'),
    ]

    operations = [
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('favorite_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')),
                ('client', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='favorites', to='users.client', verbose_name='Клиент')),
                ('inventory', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='favorited_by', to='inventory.inventory', verbose_name='Инвентарь')),
            ],
            options={
                'verbose_name': 'Избранное',
                'verbose_name_plural': 'Избранное',
                'db_table': 'inventory_favorites',
                'ordering': ['-created_date'],
                'unique_together': {('client', 'inventory')},
            },
        ),
        migrations.AddIndex(
            model_name='favorite',
            index=models.Index(fields=['client', 'inventory'], name='inventory_f_client__7e3cdb_idx'),
        ),
    ]
