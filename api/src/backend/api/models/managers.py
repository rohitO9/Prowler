from django.db import models
import threading

# Thread-local storage for current tenant
_thread_locals = threading.local()


def set_current_tenant(tenant):
    """Set current tenant in thread-local storage"""
    _thread_locals.tenant = tenant


def get_current_tenant():
    """Get current tenant from thread-local storage"""
    return getattr(_thread_locals, 'tenant', None)


def clear_current_tenant():
    """Clear current tenant from thread-local storage"""
    if hasattr(_thread_locals, 'tenant'):
        del _thread_locals.tenant


class TenantManager(models.Manager):
    """
    Custom manager that automatically filters queries by current tenant
    Use this on all tenant-scoped models
    """
    
    def __init__(self, *args, tenant_field='tenant', **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant_field = tenant_field
    
    def get_queryset(self):
        """Override to automatically filter by current tenant"""
        qs = super().get_queryset()
        tenant = get_current_tenant()
        
        if tenant:
            filter_kwargs = {self.tenant_field: tenant}
            return qs.filter(**filter_kwargs)
        
        # No tenant in context - return unfiltered (for admin, migrations, etc.)
        return qs
    
    def for_tenant(self, tenant):
        """Explicitly filter by specific tenant"""
        return self.get_queryset().filter(**{self.tenant_field: tenant})
    
    def all_tenants(self):
        """Bypass tenant filtering (use carefully!)"""
        return super().get_queryset()


class TenantAwareModel(models.Model):
    """
    Abstract base model for all tenant-scoped models
    Automatically adds tenant field and manager
    """
    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)s_set'
    )
    
    # Use tenant-aware manager by default
    objects = TenantManager()
    
    # Keep unfiltered manager for admin/maintenance
    all_objects = models.Manager()
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['tenant'], name='idx_%(class)s_tenant'),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-set tenant if not provided"""
        if not self.tenant_id:
            tenant = get_current_tenant()
            if tenant:
                self.tenant = tenant
        super().save(*args, **kwargs)
