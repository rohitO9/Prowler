#!/usr/bin/env python3
"""
Database Clear Script for Prowler SaaS
Clears all data from the database while preserving the schema
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.db import connection, transaction
from django.conf import settings

def clear_database():
    """Clear all data from the database"""
    print("🗑️  Clearing database data...")
    
    with connection.cursor() as cursor:
        # Get all table names
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name NOT LIKE 'django_%'
            ORDER BY table_name;
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("✅ No tables found to clear.")
            return
        
        print(f"📋 Found {len(tables)} tables to clear:")
        for table in tables:
            print(f"   - {table}")
        
        # Disable foreign key checks temporarily
        cursor.execute("SET session_replication_role = replica;")
        
        try:
            with transaction.atomic():
                # Clear all tables
                for table in tables:
                    cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
                    print(f"✅ Cleared table: {table}")
                
                # Reset sequences
                cursor.execute("""
                    SELECT setval(pg_get_serial_sequence(quote_ident(schemaname)||'.'||quote_ident(tablename), quote_ident(attname)), 1, false)
                    FROM pg_tables t
                    JOIN pg_class c ON c.relname = t.tablename
                    JOIN pg_attribute a ON a.attrelid = c.oid
                    WHERE a.attnum > 0
                    AND NOT a.attisdropped
                    AND a.attname LIKE '%id'
                    AND t.schemaname = 'public'
                    AND t.tablename NOT LIKE 'django_%';
                """)
                
        finally:
            # Re-enable foreign key checks
            cursor.execute("SET session_replication_role = DEFAULT;")
        
        print("✅ Database cleared successfully!")
        print("📊 All data has been removed while preserving the schema.")

def reset_migrations():
    """Reset migrations to a clean state"""
    print("🔄 Resetting migrations...")
    
    # Remove migration files (except __init__.py)
    migration_dirs = [
        'api/migrations',
        'api/v1/migrations',
    ]
    
    for migration_dir in migration_dirs:
        if os.path.exists(migration_dir):
            for file in os.listdir(migration_dir):
                if file.endswith('.py') and file != '__init__.py':
                    file_path = os.path.join(migration_dir, file)
                    os.remove(file_path)
                    print(f"🗑️  Removed migration: {file}")
    
    print("✅ Migrations reset!")

def main():
    """Main function"""
    print("🚀 Prowler SaaS Database Clear Script")
    print("=" * 50)
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django.base')
    django.setup()
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: manage.py not found. Please run this script from the Django project root.")
        sys.exit(1)
    
    # Confirm action
    print("\n⚠️  WARNING: This will delete ALL data from the database!")
    print("   - All tenants, users, and related data will be lost")
    print("   - The database schema will be preserved")
    print("   - This action cannot be undone!")
    
    confirm = input("\n🤔 Are you sure you want to continue? (yes/no): ").lower().strip()
    
    if confirm not in ['yes', 'y']:
        print("❌ Operation cancelled.")
        sys.exit(0)
    
    try:
        # Clear the database
        clear_database()
        
        # Ask about resetting migrations
        reset_migrations_confirm = input("\n🔄 Do you also want to reset migrations? (yes/no): ").lower().strip()
        
        if reset_migrations_confirm in ['yes', 'y']:
            reset_migrations()
            print("\n📝 Next steps:")
            print("   1. Run: python manage.py makemigrations")
            print("   2. Run: python manage.py migrate")
        else:
            print("\n📝 Next steps:")
            print("   1. Run: python manage.py migrate")
        
        print("\n✅ Database clear completed successfully!")
        
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
