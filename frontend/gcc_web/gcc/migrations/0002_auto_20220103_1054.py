# Generated by Django 3.2.7 on 2022-01-03 15:54

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("gcc", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="externalaccountcredentials",
            old_name="aws_secret_key",
            new_name="aws_secret_access_key",
        ),
        migrations.RenameField(
            model_name="externalaccountcredentials",
            old_name="drbx_access_token",
            new_name="drbx_refresh_token",
        ),
    ]