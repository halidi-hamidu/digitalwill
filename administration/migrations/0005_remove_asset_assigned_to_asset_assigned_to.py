# Generated by Django 5.2.3 on 2025-06-22 06:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0004_remove_confidentialinfo_account_type_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='asset',
            name='assigned_to',
        ),
        migrations.AddField(
            model_name='asset',
            name='assigned_to',
            field=models.ManyToManyField(blank=True, null=True, related_name='inherited_assets', to='administration.heir'),
        ),
    ]
