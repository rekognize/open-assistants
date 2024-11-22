# Generated by Django 5.1.1 on 2024-11-22 13:17

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_rename_thread_id_sharedlink_assistant_id_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='key',
            field=models.CharField(max_length=255),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.UniqueConstraint(fields=('user', 'key'), name='unique_key_per_user'),
        ),
    ]
