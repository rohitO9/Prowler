#!/usr/bin/env python
"""
Script to clean up duplicate tenants and keep only one per name.
Run this from the api directory: python cleanup_tenants.py
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'backend'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django.base')
django.setup()

from api.models import Tenant

def cleanup_duplicate_tenants():
    """Remove duplicate tenants, keeping only the first one for each name."""
    try:
        # Get all tenants grouped by name
        from django.db.models import Count
        duplicate_names = Tenant.objects.values('name').annotate(count=Count('name')).filter(count__gt=1)
        
        for item in duplicate_names:
            name = item['name']
            print(f"Found {item['count']} tenants with name '{name}'")
            
            # Get all tenants with this name
            tenants = Tenant.objects.filter(name=name).order_by('inserted_at')
            
            # Keep the first one, delete the rest
            keep_tenant = tenants.first()
            delete_tenants = tenants[1:]
            
            print(f"Keeping tenant: {keep_tenant.name} (ID: {keep_tenant.id})")
            
            for tenant in delete_tenants:
                print(f"Deleting duplicate tenant: {tenant.name} (ID: {tenant.id})")
                tenant.delete()
        
        print("✅ Cleanup complete!")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

if __name__ == "__main__":
    print("Cleaning up duplicate tenants...")
    cleanup_duplicate_tenants()
