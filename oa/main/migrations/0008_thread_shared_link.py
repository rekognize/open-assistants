# Generated by Django 5.1.2 on 2024-12-16 10:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_alter_thread_uuid_thread_openai_id_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='thread',
            name='shared_link',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='threads', to='main.sharedlink'),
        ),
    ]