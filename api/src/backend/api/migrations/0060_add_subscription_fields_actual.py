from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0059_remove_complianceoverview_rls_on_complianceoverview_and_more'),
    ]

    operations = [
        # These were added manually via SQL, just tracking in migrations
        migrations.RunSQL(
            sql="""
                -- Fields already added via raw SQL
                SELECT 1;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]