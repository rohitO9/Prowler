"""
Tenant-Aware Query Managers

These managers ensure that all database queries are automatically
scoped to the current tenant context, preventing cross-tenant data access.
"""

from django.db import models, connection
from django.core.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)


class TenantAwareManager(models.Manager):
    """
    Manager that automatically filters queries by tenant context.
    
    This manager ensures that all queries are scoped to the current tenant,
    preventing accidental cross-tenant data access.
    """
    
    def get_queryset(self):
        """Override queryset to include tenant filtering"""
        queryset = super().get_queryset()
        
        # Get current tenant ID from database context
        tenant_id = self._get_current_tenant_id()
        if tenant_id:
            # Filter by tenant if the model has a tenant field
            if hasattr(self.model, 'tenant'):
                queryset = queryset.filter(tenant_id=tenant_id)
            elif hasattr(self.model, 'tenant_id'):
                queryset = queryset.filter(tenant_id=tenant_id)
        
        return queryset
    
    def _get_current_tenant_id(self):
        """Get current tenant ID from database context"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW app.current_tenant_id")
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0]
        except Exception as e:
            logger.debug(f"Could not get tenant context: {e}")
        return None


class TenantAwareUserManager(TenantAwareManager):
    """
    Tenant-aware manager for User model.
    
    This manager ensures that user queries are properly scoped
    to tenant membership relationships.
    """
    
    def get_queryset(self):
        """Override queryset to include tenant membership filtering"""
        queryset = super().get_queryset()
        
        tenant_id = self._get_current_tenant_id()
        if tenant_id:
            # Filter users who are members of the current tenant
            queryset = queryset.filter(
                tenant_memberships__tenant_id=tenant_id,
                tenant_memberships__is_active=True
            ).distinct()
        
        return queryset


class TenantScopedManager(models.Manager):
    """
    Manager for models that belong to a specific tenant.
    
    This manager automatically filters by tenant_id field.
    """
    
    def get_queryset(self):
        """Override queryset to include tenant filtering"""
        queryset = super().get_queryset()
        
        tenant_id = self._get_current_tenant_id()
        if tenant_id and hasattr(self.model, 'tenant_id'):
            queryset = queryset.filter(tenant_id=tenant_id)
        
        return queryset
    
    def _get_current_tenant_id(self):
        """Get current tenant ID from database context"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW app.current_tenant_id")
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0]
        except Exception as e:
            logger.debug(f"Could not get tenant context: {e}")
        return None


def enforce_tenant_isolation(func):
    """
    Decorator to enforce tenant isolation on view functions.
    
    This decorator ensures that views can only access data
    belonging to the current tenant.
    """
    def wrapper(request, *args, **kwargs):
        # Check if request has tenant context
        if not hasattr(request, 'tenant') or not request.tenant:
            raise PermissionDenied("No tenant context found")
        
        # For authenticated users, validate tenant access
        if request.user.is_authenticated:
            if not request.user.can_access_tenant(request.tenant.id):
                logger.error(
                    f"SECURITY VIOLATION: User {request.user.email} attempted access to unauthorized tenant {request.tenant.subdomain}"
                )
                raise PermissionDenied("Access denied - insufficient permissions")
        
        return func(request, *args, **kwargs)
    
    return wrapper


class TenantIsolationMixin:
    """
    Mixin for views that require tenant isolation.
    
    This mixin provides methods to ensure tenant isolation
    and prevent cross-tenant data access.
    """
    
    def get_queryset(self):
        """Override get_queryset to enforce tenant isolation"""
        queryset = super().get_queryset()
        
        # Get current tenant
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            raise PermissionDenied("No tenant context found")
        
        # Filter queryset by tenant
        if hasattr(self.model, 'tenant'):
            queryset = queryset.filter(tenant=tenant)
        elif hasattr(self.model, 'tenant_id'):
            queryset = queryset.filter(tenant_id=tenant.id)
        
        return queryset
    
    def perform_create(self, serializer):
        """Override perform_create to set tenant context"""
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            raise PermissionDenied("No tenant context found")
        
        # Set tenant on the object being created
        if hasattr(serializer.Meta.model, 'tenant'):
            serializer.save(tenant=tenant)
        elif hasattr(serializer.Meta.model, 'tenant_id'):
            serializer.save(tenant_id=tenant.id)
        else:
            serializer.save()
    
    def validate_tenant_access(self):
        """Validate that user has access to current tenant"""
        if not self.request.user.is_authenticated:
            raise PermissionDenied("Authentication required")
        
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            raise PermissionDenied("No tenant context found")
        
        if not self.request.user.can_access_tenant(tenant.id):
            logger.error(
                f"SECURITY VIOLATION: User {self.request.user.email} attempted access to unauthorized tenant {tenant.subdomain}"
            )
            raise PermissionDenied("Access denied - insufficient permissions")
        
        return True
