# Generated by Django 2.2.6 on 2019-10-15 14:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_producttag_thumbnail'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='producttag',
            name='products',
        ),
        migrations.RemoveField(
            model_name='producttag',
            name='thumbnail',
        ),
        migrations.AddField(
            model_name='product',
            name='tags',
            field=models.ManyToManyField(blank=True, to='main.ProductTag'),
        ),
        migrations.AddField(
            model_name='productimage',
            name='thumbnail',
            field=models.ImageField(null=True, upload_to='product-thumbnails'),
        ),
    ]
