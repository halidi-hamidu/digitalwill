# Generated by Django 5.2.3 on 2025-06-22 07:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0006_asset_asset_image_asset_instruction'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='asset_type',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='asset',
            name='location',
            field=models.TextField(blank=True, null=True),
        ),
    ]
