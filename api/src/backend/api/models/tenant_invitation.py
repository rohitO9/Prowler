from django.db import models
from django.conf import settings

class TenantInvitation(models.Model):
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    email = models.EmailField()
    role = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
            ('revoked', 'Revoked'),
        ]
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_invitations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='revoked_invitations'
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'email', 'status']),
            models.Index(fields=['expires_at']),
        ]