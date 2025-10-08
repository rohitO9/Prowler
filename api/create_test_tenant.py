#!/usr/bin/env python
"""
Script to create a test tenant for development purposes.
Run this from the api directory: python create_test_tenant.py
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django.base')
django.setup()

from api.models import Tenant

def create_test_tenant():
    """Create a test tenant for company1 subdomain."""
    try:
        # Check if tenant already exists
        tenant, created = Tenant.objects.get_or_create(
            subdomain='company1',
            defaults={
                'name': 'Company1',
                'is_active': True,
                'is_verified': True
            }
        )
        
        if created:
            print(f"✅ Created tenant: {tenant.name} (ID: {tenant.id}) with subdomain: {tenant.subdomain}")
        else:
            print(f"ℹ️  Tenant already exists: {tenant.name} (ID: {tenant.id}) with subdomain: {tenant.subdomain}")
            
        return tenant
        
    except Exception as e:
        print(f"❌ Error creating tenant: {e}")
        return None

if __name__ == "__main__":
    print("Creating test tenant for company1.localhost...")
    tenant = create_test_tenant()
    if tenant:
        print("✅ Test tenant setup complete!")
    else:
        print("❌ Failed to create test tenant")
