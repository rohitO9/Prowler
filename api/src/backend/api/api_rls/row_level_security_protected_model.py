from django.db import models


class RowLevelSecurityProtectedModel(models.Model):
    """
    Abstract base model that provides tenant-based row-level security.
    All models inheriting from this will automatically get tenant isolation.
    """
    tenant_id = models.ForeignKey(
        'api.Tenant',
        on_delete=models.CASCADE,
        db_index=True,
        db_column='tenant_id',  # Prevents Django from creating 'tenant_id_id' column
        help_text="The tenant this record belongs to",
        related_name='%(class)s_set'  # Dynamic related name to avoid conflicts
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """
        Override save to ensure tenant_id is always set.
        Subclasses can override this if they need custom tenant logic.
        """
        if not self.tenant_id:
            raise ValueError("tenant_id must be set before saving")
        super().save(*args, **kwargs)
    
    def __str__(self):
        """
        Default string representation including tenant information.
        Subclasses should override this for more specific representations.
        """
        return f"{self.__class__.__name__} (Tenant: {self.tenant_id})"