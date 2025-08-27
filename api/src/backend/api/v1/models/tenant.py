from django.db import models
import uuid


class Tenant(models.Model):
    """
    Represents a tenant/organization in the multi-tenant application.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Tenant name/organization name")
    slug = models.SlugField(max_length=255, unique=True, help_text="URL-friendly tenant identifier")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Whether this tenant is active")
    
    class Meta:
        app_label = 'api_v1'
        db_table = 'tenants'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name