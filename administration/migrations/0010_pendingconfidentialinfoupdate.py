# Generated by Django 5.2.3 on 2025-06-24 17:59

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0009_remove_confidentialinfo_assigned_to_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingConfidentialInfoUpdate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('instructions', models.TextField()),
                ('uploaded_file', models.FileField(blank=True, null=True, upload_to='pending_confidential_files/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('assigned_to', models.ManyToManyField(blank=True, to='administration.heir')),
                ('confidential_info', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='administration.confidentialinfo')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
