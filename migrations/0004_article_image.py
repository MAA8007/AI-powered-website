# Generated by Django 4.2.4 on 2024-08-19 08:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0003_delete_category_delete_website'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='image',
            field=models.URLField(default=None),
        ),
    ]
