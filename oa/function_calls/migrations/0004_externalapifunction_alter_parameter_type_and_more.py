# Generated by Django 5.1.1 on 2025-01-28 19:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('function_calls', '0003_function_slug'),
        ('main', '0012_sharedlink_user_thread_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalAPIFunction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(blank=True, max_length=100)),
                ('description', models.TextField()),
                ('endpoint', models.URLField(blank=True, null=True)),
                ('method', models.CharField(choices=[('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('DELETE', 'DELETE')], default='GET', max_length=10)),
                ('bearer_token', models.CharField(blank=True, max_length=200, null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='parameter',
            name='type',
            field=models.CharField(choices=[('o', 'object'), ('a', 'array'), ('s', 'string'), ('n', 'number'), ('b', 'boolean'), ('-', 'null')], max_length=1),
        ),
        migrations.CreateModel(
            name='CodeInterpreterScript',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assistant_id', models.CharField(db_index=True, max_length=50)),
                ('thread_id', models.CharField(db_index=True, max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('code', models.TextField()),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.project')),
            ],
        ),
        migrations.AlterField(
            model_name='parameter',
            name='function',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parameters', to='function_calls.externalapifunction'),
        ),
        migrations.CreateModel(
            name='ExternalAPIFunctionExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('arguments', models.JSONField(blank=True, default=dict)),
                ('result', models.JSONField(blank=True, default=dict)),
                ('time', models.DateTimeField()),
                ('function', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='function_calls.externalapifunction')),
            ],
        ),
        migrations.CreateModel(
            name='LocalFunction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assistant_id', models.CharField(db_index=True, max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('properties', models.JSONField()),
                ('code', models.TextField()),
                ('returns', models.JSONField()),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.project')),
            ],
        ),
        migrations.DeleteModel(
            name='Function',
        ),
    ]
