# Generated by Django 3.2.12 on 2022-04-01 13:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teslarent', '0003_alter_credentials_salt'),
    ]

    operations = [
        migrations.AlterField(
            model_name='credentials',
            name='current_token',
            field=models.CharField(max_length=3072),
        ),
        migrations.AlterField(
            model_name='credentials',
            name='refresh_token',
            field=models.CharField(max_length=3072),
        ),
    ]
