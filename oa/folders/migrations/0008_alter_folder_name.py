# Generated by Django 5.1.1 on 2025-02-24 19:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('folders', '0007_folder_file_ids_delete_folderfile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='folder',
            name='name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
