# Generated by Django 3.2.12 on 2022-02-17 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teslarent', '0002_auto_20220216_2114'),
    ]

    operations = [
        migrations.AlterField(
            model_name='credentials',
            name='salt',
            field=models.CharField(max_length=32, verbose_name='Salt for KDF from secret to encryption key'),
        ),
    ]
