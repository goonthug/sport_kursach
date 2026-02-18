from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_add_block_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="passport_series",
            field=models.CharField(
                max_length=4,
                blank=True,
                null=True,
                verbose_name="Серия паспорта",
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="passport_number",
            field=models.CharField(
                max_length=6,
                blank=True,
                null=True,
                verbose_name="Номер паспорта",
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="passport_issue_date",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="Дата выдачи паспорта",
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="passport_department_code",
            field=models.CharField(
                max_length=7,
                blank=True,
                null=True,
                verbose_name="Код подразделения",
                help_text="В формате 000-000",
            ),
        ),
        migrations.RemoveField(
            model_name="client",
            name="passport_data",
        ),
    ]

