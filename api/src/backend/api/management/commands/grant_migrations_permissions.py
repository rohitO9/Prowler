"""
Grant the app database user (e.g. prowler_user) permission to access django_migrations.

Run this with the admin/superuser database connection so the GRANT succeeds.
Example:
  python manage.py grant_migrations_permissions --database admin

If your settings use a single DB user, run the SQL in scripts/grant_django_migrations.sql
as a PostgreSQL superuser instead.
"""
from django.core.management.base import BaseCommand
from django.conf import settings

from api.db_utils import DB_PROWLER_USER, psycopg_connection


class Command(BaseCommand):
    help = (
        "Grant the app DB user (prowler_user) SELECT/INSERT/UPDATE on django_migrations. "
        "Use --database admin so the command connects as an admin user that can GRANT."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default="admin",
            help="Database alias to use for the connection (must be a user that can GRANT).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the SQL that would be run without executing it.",
        )

    def handle(self, *args, **options):
        db_alias = options["database"]
        dry_run = options["dry_run"]
        app_user = DB_PROWLER_USER

        if db_alias not in settings.DATABASES:
            self.stderr.write(
                self.style.ERROR(
                    f"Database alias '{db_alias}' not found in settings.DATABASES. "
                    "Use an admin-capable alias (e.g. 'admin') or run the SQL manually as a superuser:\n"
                    "  GRANT SELECT, INSERT, UPDATE ON django_migrations TO <your_app_user>;\n"
                    f"  GRANT USAGE, SELECT ON SEQUENCE django_migrations_id_seq TO <your_app_user>;\n"
                    f"(Replace <your_app_user> with {app_user!r} if that is your app user.)"
                )
            )
            return

        sqls = [
            f"GRANT SELECT, INSERT, UPDATE ON django_migrations TO {app_user};",
            f"GRANT USAGE, SELECT ON SEQUENCE django_migrations_id_seq TO {app_user};",
        ]

        if dry_run:
            self.stdout.write("Would run (as %s):\n" % db_alias)
            for s in sqls:
                self.stdout.write("  %s\n" % s)
            return

        try:
            with psycopg_connection(db_alias) as conn:
                with conn.cursor() as cur:
                    for sql in sqls:
                        cur.execute(sql)
                conn.commit()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Granted django_migrations permissions to {app_user!r}."
                )
            )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(
                    "Failed to grant permissions: %s\n\n"
                    "For local dev, set in .env the Postgres superuser (e.g. postgres):\n"
                    "  POSTGRES_ADMIN_USER=postgres\n"
                    "  POSTGRES_ADMIN_PASSWORD=<your postgres password>\n\n"
                    "Then run this command again. Or run the SQL manually as a superuser:\n"
                    "  psql -U postgres -d %s -c \"GRANT SELECT, INSERT, UPDATE ON django_migrations TO %s;\"\n"
                    "  psql -U postgres -d %s -c \"GRANT USAGE, SELECT ON SEQUENCE django_migrations_id_seq TO %s;\""
                    % (e, settings.DATABASES["default"]["NAME"], app_user, settings.DATABASES["default"]["NAME"], app_user)
                )
            )
            raise
