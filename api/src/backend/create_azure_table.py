#!/usr/bin/env python
import os
import sys
import django

# Add the backend directory to Python path
sys.path.append('/Users/rohit/OneDrive/Desktop/Prowler/api/src/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from api.v1.models.azure_sso import AzureSSOConfig

def create_azure_sso_table():
    """Manually create the azure_sso_config table"""
    cursor = connection.cursor()
    
    # Get the SQL for creating the table
    sql = """
    CREATE TABLE IF NOT EXISTS azure_sso_config (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id UUID NOT NULL REFERENCES api_tenant(id) ON DELETE CASCADE,
        azure_tenant_id VARCHAR(255) NOT NULL,
        client_id VARCHAR(255) NOT NULL,
        client_secret TEXT NOT NULL,
        authority VARCHAR(500),
        authorization_endpoint VARCHAR(500),
        token_endpoint VARCHAR(500),
        scim_enabled BOOLEAN DEFAULT FALSE,
        scim_token VARCHAR(255),
        scim_base_url VARCHAR(500),
        auto_provision_users BOOLEAN DEFAULT TRUE,
        auto_deprovision_users BOOLEAN DEFAULT TRUE,
        sync_user_attributes BOOLEAN DEFAULT TRUE,
        attribute_mapping JSONB DEFAULT '{}',
        group_role_mapping JSONB DEFAULT '{}',
        last_sync_at TIMESTAMP WITH TIME ZONE,
        last_sync_status VARCHAR(50),
        last_sync_error TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    try:
        cursor.execute(sql)
        print("✅ Successfully created azure_sso_config table")
        return True
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False

if __name__ == "__main__":
    create_azure_sso_table()
