"""
Clean up duplicate tenants before applying unique constraints
Run this BEFORE creating migrations
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api', 'src', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django.base')
django.setup()

from api.models import Tenant, User
from django.db import transaction
from django.db.models import Count, Q
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_database():
    """Create backup tables"""
    from django.core.management import call_command
    
    logger.info("📦 Creating database backup...")
    call_command('dumpdata', 'api.Tenant', output='tenants_backup.json')
    call_command('dumpdata', 'api.User', output='users_backup.json')
    logger.info("✅ Backup created: tenants_backup.json, users_backup.json")


def find_duplicate_subdomains():
    """Find all duplicate subdomains"""
    duplicates = Tenant.objects.values('subdomain').annotate(
        count=Count('id')
    ).filter(count__gt=1, subdomain__isnull=False)
    
    return list(duplicates)


def find_duplicate_names():
    """Find all duplicate tenant names"""
    duplicates = Tenant.objects.values('name').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    return list(duplicates)


def consolidate_duplicate_subdomains():
    """
    Merge tenants with duplicate subdomains
    """
    duplicates = find_duplicate_subdomains()
    
    if not duplicates:
        logger.info("✅ No duplicate subdomains found")
        return
    
    logger.info(f"Found {len(duplicates)} duplicate subdomains")
    
    for dup in duplicates:
        subdomain = dup['subdomain']
        tenants = Tenant.objects.filter(subdomain=subdomain).order_by('created_at')
        
        logger.info(f"\n🔍 Processing subdomain: {subdomain} ({dup['count']} tenants)")
        
        # Find keeper (prefer one with most users, then oldest)
        keeper = None
        max_users = 0
        
        for tenant in tenants:
            user_count = User.objects.filter(primary_tenant=tenant).count()
            logger.info(f"  - {tenant.id}: {tenant.name}, created: {tenant.created_at}, users: {user_count}")
            
            if user_count > max_users:
                keeper = tenant
                max_users = user_count
        
        if not keeper:
            keeper = tenants.first()
        
        logger.info(f"  ✅ Keeping: {keeper.id} ({keeper.name})")
        
        # Migrate users and delete duplicates
        with transaction.atomic():
            for tenant in tenants:
                if tenant.id != keeper.id:
                    # Migrate users
                    users = User.objects.filter(primary_tenant=tenant)
                    count = users.count()
                    
                    if count > 0:
                        logger.info(f"  📦 Migrating {count} users from {tenant.id} to {keeper.id}")
                        users.update(primary_tenant=keeper)
                    
                    logger.info(f"  🗑️  Deleting duplicate: {tenant.id}")
                    tenant.delete()
            
            # Ensure keeper has correct subdomain (lowercase)
            keeper.subdomain = subdomain.lower()
            keeper.save()
            logger.info(f"  ✏️  Updated keeper subdomain: {keeper.subdomain}")


def fix_missing_subdomains():
    """Add subdomains to tenants that don't have them"""
    tenants_without_subdomain = Tenant.objects.filter(
        Q(subdomain__isnull=True) | Q(subdomain='')
    )
    
    if not tenants_without_subdomain.exists():
        logger.info("✅ All tenants have subdomains")
        return
    
    logger.info(f"Found {tenants_without_subdomain.count()} tenants without subdomain")
    
    for tenant in tenants_without_subdomain:
        import re
        subdomain = re.sub(r'[^a-z0-9-]', '', tenant.name.lower().replace(' ', '-'))
        
        # Ensure uniqueness
        counter = 1
        original = subdomain
        while Tenant.objects.filter(subdomain=subdomain).exists():
            subdomain = f"{original}{counter}"
            counter += 1
        
        tenant.subdomain = subdomain
        tenant.save()
        logger.info(f"  ✏️  Set subdomain for '{tenant.name}': {subdomain}")


def verify_cleanup():
    """Verify no duplicates remain"""
    logger.info("\n🔍 Verifying cleanup...")
    
    # Check duplicate subdomains
    dup_subdomains = find_duplicate_subdomains()
    if dup_subdomains:
        logger.error(f"❌ Still have {len(dup_subdomains)} duplicate subdomains!")
        return False
    
    # Check missing subdomains
    missing = Tenant.objects.filter(
        Q(subdomain__isnull=True) | Q(subdomain='')
    ).count()
    if missing > 0:
        logger.error(f"❌ Still have {missing} tenants without subdomain!")
        return False
    
    # Check orphaned users
    orphaned = User.objects.filter(primary_tenant__isnull=True).count()
    if orphaned > 0:
        logger.error(f"❌ Found {orphaned} orphaned users!")
        return False
    
    logger.info("✅ All checks passed!")
    return True


def main():
    logger.info("=" * 70)
    logger.info("TENANT DATABASE CLEANUP SCRIPT")
    logger.info("=" * 70)
    
    # Step 1: Backup
    backup_database()
    
    # Step 2: Show current state
    total_tenants = Tenant.objects.count()
    logger.info(f"\n📊 Current state: {total_tenants} tenants")
    
    # Step 3: Fix missing subdomains
    fix_missing_subdomains()
    
    # Step 4: Consolidate duplicates
    consolidate_duplicate_subdomains()
    
    # Step 5: Verify
    if verify_cleanup():
        logger.info("\n" + "=" * 70)
        logger.info("✅ CLEANUP COMPLETE!")
        logger.info("=" * 70)
        
        # Show final state
        logger.info("\n📊 Final tenant list:")
        for tenant in Tenant.objects.all().order_by('created_at'):
            user_count = User.objects.filter(primary_tenant=tenant).count()
            logger.info(f"  - {tenant.name}: {tenant.subdomain} ({user_count} users)")
        
        logger.info("\n✅ You can now run: python manage.py makemigrations")
        logger.info("✅ Then run: python manage.py migrate")
    else:
        logger.error("\n❌ Cleanup completed with errors!")
        logger.error("Review the errors above and fix manually")
        logger.error("\nTo restore from backup:")
        logger.error("  python manage.py loaddata tenants_backup.json")
        logger.error("  python manage.py loaddata users_backup.json")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)
