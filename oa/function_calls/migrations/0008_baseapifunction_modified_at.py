# Generated by Django 5.1.2 on 2025-03-13 11:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('function_calls', '0007_remove_localapifunction_assistant_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='baseapifunction',
            name='modified_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
