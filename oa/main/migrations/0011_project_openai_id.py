# Generated by Django 5.1.2 on 2024-12-27 14:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_remove_project_user_project_users'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='openai_id',
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True),
        ),
    ]
