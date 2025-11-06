"""
Celery Background Tasks for Azure AD Sync
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction

from api.models import Tenant
from api.v1.models.azure_sso import AzureSSOConfig, AzureADAuditLog
from api.services.azure_scim_service import AzureSCIMService

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def sync_azure_users_task(self, tenant_id):
    """
    Sync users from Azure AD for a specific tenant
    
    Args:
        tenant_id: UUID of the tenant to sync
        
    Returns:
        Dictionary with sync statistics
    """
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        
        try:
            sso_config = tenant.azure_sso_config
            if not sso_config.is_active:
                return {
                    "status": "skipped",
                    "reason": "SSO not configured or inactive"
                }
        except AzureSSOConfig.DoesNotExist:
            return {
                "status": "skipped",
                "reason": "Azure SSO not configured"
            }
        
        # Log sync start
        AzureADAuditLog.log_event(
            tenant=tenant,
            event_type='SCIM_SYNC_STARTED',
            description=f'Background sync started for tenant {tenant.name}',
            details={'task_id': self.request.id}
        )
        
        # Perform sync
        scim_service = AzureSCIMService(tenant)
        stats = scim_service.sync_all_users()
        
        # Update sync status
        sso_config.last_sync_at = timezone.now()
        sso_config.last_sync_status = 'success' if stats['errors'] == 0 else 'partial'
        sso_config.last_sync_error = '' if stats['errors'] == 0 else f"{stats['errors']} errors occurred"
        sso_config.save()
        
        # Log sync completion
        AzureADAuditLog.log_event(
            tenant=tenant,
            event_type='SCIM_SYNC_COMPLETED',
            description=f'Background sync completed for tenant {tenant.name}',
            details={
                'task_id': self.request.id,
                'stats': stats
            }
        )
        
        logger.info(f"Sync completed for tenant {tenant.name}: {stats}")
        
        return {
            "status": "completed",
            "tenant_id": str(tenant_id),
            "tenant_name": tenant.name,
            "stats": stats
        }
        
    except Tenant.DoesNotExist:
        logger.error(f"Tenant {tenant_id} not found")
        return {
            "status": "failed",
            "error": f"Tenant {tenant_id} not found"
        }
    except Exception as e:
        logger.error(f"Sync failed for tenant {tenant_id}: {e}")
        
        # Update sync status with error
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            sso_config = tenant.azure_sso_config
            sso_config.last_sync_at = timezone.now()
            sso_config.last_sync_status = 'failed'
            sso_config.last_sync_error = str(e)
            sso_config.save()
            
            # Log sync failure
            AzureADAuditLog.log_event(
                tenant=tenant,
                event_type='SCIM_SYNC_FAILED',
                description=f'Background sync failed for tenant {tenant.name}',
                details={
                    'task_id': self.request.id,
                    'error': str(e)
                }
            )
        except Exception:
            pass  # Don't fail the task if we can't update the status
        
        return {
            "status": "failed",
            "tenant_id": str(tenant_id),
            "error": str(e)
        }


@shared_task
def periodic_azure_sync():
    """
    Periodic sync for all tenants with SCIM enabled
    This task should be run every 6 hours via Celery Beat
    
    Returns:
        Dictionary with task results
    """
    try:
        # Find all tenants with active SCIM
        tenants = Tenant.objects.filter(
            azure_sso_config__is_active=True,
            azure_sso_config__scim_enabled=True
        )
        
        results = []
        for tenant in tenants:
            # Trigger sync task
            result = sync_azure_users_task.delay(tenant.id)
            results.append({
                "tenant_id": str(tenant.id),
                "tenant_name": tenant.name,
                "task_id": result.id
            })
        
        logger.info(f"Triggered sync for {len(results)} tenants")
        
        return {
            "status": "started",
            "tenants_synced": len(results),
            "tasks": results
        }
        
    except Exception as e:
        logger.error(f"Periodic sync failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


@shared_task
def cleanup_expired_invites():
    """
    Clean up expired invitations
    This task should be run daily via Celery Beat
    
    Returns:
        Dictionary with cleanup statistics
    """
    try:
        from api.models import TenantMembership
        
        # Find expired invites
        expired_invites = TenantMembership.objects.filter(
            invite_expires_at__lt=timezone.now(),
            invite_accepted_at__isnull=True,
            invite_token__isnull=False
        )
        
        count = expired_invites.count()
        
        # Clear expired invite tokens
        expired_invites.update(
            invite_token='',
            invite_expires_at=None
        )
        
        logger.info(f"Cleaned up {count} expired invitations")
        
        return {
            "status": "completed",
            "expired_invites_cleaned": count
        }
        
    except Exception as e:
        logger.error(f"Cleanup expired invites failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


@shared_task
def send_invite_email_task(user_id, tenant_id, invite_token):
    """
    Send invitation email to a user
    
    Args:
        user_id: UUID of the user
        tenant_id: UUID of the tenant
        invite_token: JWT invite token
        
    Returns:
        Dictionary with send status
    """
    try:
        from api.models import User, Tenant
        from api.services.invite_service import InviteService
        
        user = User.objects.get(id=user_id)
        tenant = Tenant.objects.get(id=tenant_id)
        
        # Get membership
        membership = user.tenant_memberships.get(tenant=tenant)
        
        # Send email
        invite_service = InviteService()
        email_sent = invite_service.send_invite_email(
            membership=membership,
            invite_token=invite_token
        )
        
        # Log email send
        AzureADAuditLog.log_event(
            tenant=tenant,
            user=user,
            event_type='USER_INVITED',
            description=f'Invitation email sent to {user.email}',
            details={
                'email_sent': email_sent,
                'invite_token': invite_token[:10] + '...'  # Truncate for security
            }
        )
        
        return {
            "status": "completed",
            "user_id": str(user_id),
            "email": user.email,
            "email_sent": email_sent
        }
        
    except Exception as e:
        logger.error(f"Send invite email failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


@shared_task
def bulk_sync_azure_users(tenant_ids):
    """
    Bulk sync multiple tenants
    
    Args:
        tenant_ids: List of tenant UUIDs
        
    Returns:
        Dictionary with sync results
    """
    try:
        results = []
        
        for tenant_id in tenant_ids:
            result = sync_azure_users_task.delay(tenant_id)
            results.append({
                "tenant_id": str(tenant_id),
                "task_id": result.id
            })
        
        logger.info(f"Triggered bulk sync for {len(results)} tenants")
        
        return {
            "status": "started",
            "tenants": results
        }
        
    except Exception as e:
        logger.error(f"Bulk sync failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }
