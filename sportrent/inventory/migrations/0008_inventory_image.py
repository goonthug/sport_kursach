from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0007_city_and_pickup_point'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventory',
            name='image',
            field=models.ImageField(
                blank=True,
                help_text='Загрузите фотографию инвентаря. Рекомендуемый размер 800x600.',
                null=True,
                upload_to='inventory/',
                verbose_name='Фото инвентаря',
            ),
        ),
    ]
