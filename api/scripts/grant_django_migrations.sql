-- Fix: "permission denied for table django_migrations"
-- Run this as a PostgreSQL superuser (e.g. postgres or your admin user).
-- Replace prowler_user with your app DB user (POSTGRES_USER / DJANGO_DB_USER) if different.

GRANT SELECT, INSERT, UPDATE ON django_migrations TO prowler_user;

-- If you use the sequence for the primary key:
GRANT USAGE, SELECT ON SEQUENCE django_migrations_id_seq TO prowler_user;
