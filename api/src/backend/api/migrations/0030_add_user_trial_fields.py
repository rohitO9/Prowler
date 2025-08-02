from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
    ('api', '0029_findings_check_index_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="trial_start",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="trial_end",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="is_trial_active",
            field=models.BooleanField(default=False),
        ),
    ] 