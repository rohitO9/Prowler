# Generated manually for tenant configuration fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='contact_email',
            field=models.EmailField(blank=True, help_text='Primary contact email for the tenant', max_length=254, null=True),
        ),
        migrations.AddField(
            model_name='tenant',
            name='contact_phone',
            field=models.CharField(blank=True, help_text='Primary contact phone number', max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='tenant',
            name='address',
            field=models.TextField(blank=True, help_text='Company address', null=True),
        ),
        migrations.AddField(
            model_name='tenant',
            name='logo_url',
            field=models.URLField(blank=True, help_text='URL to company logo', max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='tenant',
            name='theme_color',
            field=models.CharField(default='#3B82F6', help_text='Primary theme color (hex code)', max_length=7),
        ),
        migrations.AddField(
            model_name='tenant',
            name='secondary_color',
            field=models.CharField(default='#1E40AF', help_text='Secondary theme color (hex code)', max_length=7),
        ),
        migrations.AddField(
            model_name='tenant',
            name='is_verified',
            field=models.BooleanField(default=False, help_text='Whether the tenant has been verified via email'),
        ),
        migrations.AddField(
            model_name='tenant',
            name='admin_user',
            field=models.ForeignKey(blank=True, help_text='The admin user who created this tenant', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_of_tenants', to='api.user'),
        ),
    ]
