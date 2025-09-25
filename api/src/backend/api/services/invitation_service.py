from datetime import timedelta
from django.utils import timezone
from api.models import Invitation  # Change from TenantInvitation to Invitation

class TenantInvitationService:
    def create_invitation(self, tenant, invited_by, email, role, expires_in_days=7):
        expires_at = timezone.now() + timedelta(days=expires_in_days)
        
        invitation = Invitation.objects.create(  # Use Invitation instead of TenantInvitation
            tenant=tenant,
            invited_by=invited_by,
            email=email,
            state=Invitation.State.PENDING,
            expires_at=expires_at
        )
        
        return invitation

    def get_active_invitations(self, tenant):
        return Invitation.objects.filter(
            tenant=tenant,
            state=Invitation.State.PENDING,
            expires_at__gt=timezone.now()
        )

    def revoke_invitation(self, tenant, invitation_id, revoked_by):
        invitation = Invitation.objects.get(
            tenant=tenant,
            id=invitation_id,
            state=Invitation.State.PENDING
        )
        invitation.state = Invitation.State.REVOKED
        invitation.revoked_by = revoked_by
        invitation.revoked_at = timezone.now()
        invitation.save()
        return invitation