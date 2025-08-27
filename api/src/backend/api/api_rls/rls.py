

from django.db import connection
from django.core.exceptions import ValidationError
from contextlib import contextmanager

# Import settings - these should be safe to import here
try:
    from api.db_utils import DB_USER, POSTGRES_TENANT_VAR
except ImportError:
    # Fallback or default values
    DB_USER = 'api_user'  # Replace with your actual DB user
    POSTGRES_TENANT_VAR = 'app.current_tenant_id'  # Replace with your actual setting


class TenantContextManager:
    """Context manager for setting tenant context in PostgreSQL."""
    
    def __init__(self, tenant_id: str, connection_obj=None):
        self.tenant_id = str(tenant_id) if tenant_id else None
        self.connection_obj = connection_obj or connection
        self.previous_value = None
        
    def __enter__(self):
        if self.tenant_id:
            with self.connection_obj.cursor() as cursor:
                # Store previous value if it exists
                try:
                    cursor.execute(f"SELECT current_setting('{POSTGRES_TENANT_VAR}', true)")
                    result = cursor.fetchone()
                    self.previous_value = result[0] if result and result[0] else None
                except Exception:
                    self.previous_value = None
                
                # Set new tenant context
                cursor.execute(f"SET {POSTGRES_TENANT_VAR} = %s", [self.tenant_id])
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        with self.connection_obj.cursor() as cursor:
            if self.previous_value is not None:
                # Restore previous value
                cursor.execute(f"SET {POSTGRES_TENANT_VAR} = %s", [self.previous_value])
            else:
                # Clear the setting
                cursor.execute(f"SET {POSTGRES_TENANT_VAR} = ''")


@contextmanager
def tenant_context(tenant_id: str, connection_obj=None):
    """
    Context manager for setting tenant context for RLS policies.
    
    Usage:
        with tenant_context('123e4567-e89b-12d3-a456-426614174000'):
            # All database queries here will be filtered by tenant
            users = User.objects.all()  # Only returns users for this tenant
    """
    with TenantContextManager(tenant_id, connection_obj):
        yield


def set_tenant_context(tenant_id: str, connection_obj=None):
    """
    Set tenant context for the current database connection.
    
    Args:
        tenant_id: UUID string of the tenant
        connection_obj: Database connection (optional, uses default if None)
    
    Returns:
        TenantContextManager instance
    """
    return TenantContextManager(tenant_id, connection_obj)


def get_current_tenant_id(connection_obj=None):
    """
    Get the currently set tenant ID from the database connection.
    
    Returns:
        str: Current tenant ID or None if not set
    """
    conn = connection_obj or connection
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT current_setting('{POSTGRES_TENANT_VAR}', true)")
            result = cursor.fetchone()
            return result[0] if result and result[0] and result[0] != '' else None
    except Exception:
        return None


def clear_tenant_context(connection_obj=None):
    """Clear the tenant context from the current database connection."""
    conn = connection_obj or connection
    with conn.cursor() as cursor:
        cursor.execute(f"SET {POSTGRES_TENANT_VAR} = ''")


def validate_tenant_access(model_instance):
    """
    Validate that the current tenant context matches the model instance's tenant.
    
    Args:
        model_instance: Model instance with tenant_id field
        
    Raises:
        ValidationError: If tenant context doesn't match or is not set
    """
    current_tenant = get_current_tenant_id()
    
    if not current_tenant:
        raise ValidationError("No tenant context set. Cannot access tenant-protected resources.")
    
    if not hasattr(model_instance, 'tenant_id'):
        raise ValidationError(f"{model_instance.__class__.__name__} does not have tenant_id field.")
    
    instance_tenant = str(model_instance.tenant_id) if model_instance.tenant_id else None
    
    if current_tenant != instance_tenant:
        raise ValidationError(
            f"Tenant context mismatch. Current: {current_tenant}, "
            f"Instance: {instance_tenant}"
        )


class RLSMiddleware:
    """
    Middleware to automatically set tenant context based on request.
    
    Add this to your MIDDLEWARE setting:
    'api.rls.RLSMiddleware'
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get tenant from request (customize this based on your needs)
        tenant_id = self.get_tenant_from_request(request)
        
        if tenant_id:
            with tenant_context(tenant_id):
                response = self.get_response(request)
        else:
            # Clear any existing tenant context
            clear_tenant_context()
            response = self.get_response(request)
            
        return response

    def get_tenant_from_request(self, request):
        """
        Extract tenant ID from request. Customize this method based on your needs.
        
        Examples:
        - From subdomain: tenant_id = request.get_host().split('.')[0]
        - From header: tenant_id = request.headers.get('X-Tenant-ID')
        - From user: tenant_id = request.user.tenant_id if request.user.is_authenticated else None
        """
        # Example implementation - customize as needed
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'tenant_id'):
                return str(request.user.tenant_id)
        
        # Check for tenant in headers
        tenant_header = request.headers.get('X-Tenant-ID')
        if tenant_header:
            return tenant_header
            
        # Check for tenant in subdomain
        host_parts = request.get_host().split('.')
        if len(host_parts) > 2:  # subdomain.domain.com
            return host_parts[0]
            
        return None


def create_rls_policy(table_name: str, policy_name: str, statement: str = "SELECT", 
                     field_name: str = "tenant_id", connection_obj=None):
    """
    Manually create an RLS policy for a table.
    
    Args:
        table_name: Name of the database table
        policy_name: Name for the policy
        statement: SQL statement type (SELECT, INSERT, UPDATE, DELETE)
        field_name: Name of the tenant field (default: tenant_id)
        connection_obj: Database connection (optional)
    """
    conn = connection_obj or connection
    
    clause = "WITH CHECK" if statement in ["INSERT", "UPDATE"] else "USING"
    
    sql = f"""
    ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
    CREATE POLICY {policy_name}
    ON {table_name}
    FOR {statement}
    TO {DB_USER}
    {clause} (
        CASE
            WHEN current_setting('{POSTGRES_TENANT_VAR}', True) IS NULL THEN FALSE
            WHEN current_setting('{POSTGRES_TENANT_VAR}', True) = '' THEN FALSE
            ELSE {field_name} = current_setting('{POSTGRES_TENANT_VAR}')::uuid
        END
    );
    GRANT {statement} ON {table_name} TO {DB_USER};
    """
    
    with conn.cursor() as cursor:
        cursor.execute(sql)


def drop_rls_policy(table_name: str, policy_name: str, connection_obj=None):
    """
    Drop an RLS policy from a table.
    
    Args:
        table_name: Name of the database table
        policy_name: Name of the policy to drop
        connection_obj: Database connection (optional)
    """
    conn = connection_obj or connection
    
    sql = f"""
    DROP POLICY IF EXISTS {policy_name} ON {table_name};
    """
    
    with conn.cursor() as cursor:
        cursor.execute(sql)


def disable_rls(table_name: str, connection_obj=None):
    """
    Disable RLS for a table.
    
    Args:
        table_name: Name of the database table
        connection_obj: Database connection (optional)
    """
    conn = connection_obj or connection
    
    sql = f"""
    ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY;
    ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;
    """
    
    with conn.cursor() as cursor:
        cursor.execute(sql)