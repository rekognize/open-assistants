# Generated by Django 5.1.1 on 2025-02-05 09:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('folders', '0002_alter_folder_uuid'),
        ('main', '0012_sharedlink_user_thread_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='folder',
            name='project',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='main.project'),
            preserve_default=False,
        ),
    ]
