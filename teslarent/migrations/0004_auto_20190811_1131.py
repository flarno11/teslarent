# Generated by Django 2.1.9 on 2019-08-11 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teslarent', '0003_auto_20190526_1813'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rental',
            name='price_brutto',
            field=models.FloatField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name='rental',
            name='price_netto',
            field=models.FloatField(blank=True, default=None, null=True),
        ),
    ]