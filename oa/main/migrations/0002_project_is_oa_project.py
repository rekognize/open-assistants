# Generated by Django 5.1.1 on 2024-10-16 08:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="is_oa_project",
            field=models.BooleanField(default=False),
        ),
    ]
