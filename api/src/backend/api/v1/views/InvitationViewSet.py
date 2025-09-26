from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.core.mail import send_mail
from django.conf import settings
from api.models import Invitation, Tenant
from api.v1.serializers import InvitationSerializer
from rest_framework.permissions import IsAuthenticated
from api.permissions import HasTenantPermissions  # This should now work
import uuid
from datetime import datetime, timedelta, timezone
from rest_framework.exceptions import ValidationError

class InvitationViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasTenantPermissions]
    serializer_class = InvitationSerializer

    def get_tenant_or_400(self, request):
        """Helper method to get tenant or raise 400"""
        if not hasattr(request, 'tenant') or not request.tenant:
            raise ValidationError({
                "detail": "Tenant ID is required. Please provide X-Tenant-ID header."
            })
        return request.tenant

    def list(self, request):
        """List all invitations for the current tenant"""
        tenant = self.get_tenant_or_400(request)
        invitations = Invitation.objects.filter(tenant_id=tenant.id)
        serializer = InvitationSerializer(invitations, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """Create and send a new tenant invitation"""
        tenant = self.get_tenant_or_400(request)
        try:
            data = request.data.get('data', {})
            attributes = data.get('attributes', {})
            
            email = attributes.get('email')
            role = attributes.get('role', 'member')
            tenant_id = request.tenant.id
            
            # Basic validation
            if not email:
                return Response(
                    {"errors": [{"detail": "Email is required"}]}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if invitation already exists
            existing_invitation = Invitation.objects.filter(
                email=email,
                tenant_id=tenant_id,
                state='pending'
            ).first()
            
            if existing_invitation:
                return Response(
                    {"errors": [{"detail": "Invitation already exists for this email"}]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create invitation record
            invitation = Invitation.objects.create(
                id=uuid.uuid4(),
                email=email,
                role=role,
                tenant_id=tenant_id,
                invited_by=request.user,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                state='pending'
            )
            
            # Send invitation email
            invitation_link = f"{settings.FRONTEND_URL}/invitations/accept/{invitation.id}"
            send_mail(
                subject=f"Invitation to join {request.tenant.name}",
                message=f"""
                You've been invited to join {request.tenant.name}.
                Click here to accept: {invitation_link}
                
                This invitation will expire in 7 days.
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            serializer = InvitationSerializer(invitation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"errors": [{"detail": f"Failed to create invitation: {str(e)}"}]}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """Get a specific invitation by ID"""
        try:
            invitation = Invitation.objects.get(id=pk, tenant=request.tenant)
            serializer = InvitationSerializer(invitation)
            return Response(serializer.data)
        except Invitation.DoesNotExist:
            return Response(
                {"errors": [{"detail": "Invitation not found"}]},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def destroy(self, request, pk=None):
        """Delete/cancel an invitation"""
        try:
            invitation = Invitation.objects.get(id=pk, tenant=request.tenant)
            invitation.state = 'cancelled'
            invitation.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Invitation.DoesNotExist:
            return Response(
                {"errors": [{"detail": "Invitation not found"}]},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Resend an invitation email"""
        try:
            invitation = Invitation.objects.get(id=pk, tenant=request.tenant)
            
            if invitation.state != 'pending':
                return Response(
                    {"errors": [{"detail": "Can only resend pending invitations"}]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update expiration
            invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            invitation.save()
            
            # Resend email
            invitation_link = f"{settings.FRONTEND_URL}/invitations/accept/{invitation.id}"
            send_mail(
                subject=f"Invitation to join {request.tenant.name} (Resent)",
                message=f"""
                You've been invited to join {request.tenant.name}.
                Click here to accept: {invitation_link}
                
                This invitation will expire in 7 days.
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitation.email],
                fail_silently=False,
            )
            
            serializer = InvitationSerializer(invitation)
            return Response(serializer.data)
            
        except Invitation.DoesNotExist:
            return Response(
                {"errors": [{"detail": "Invitation not found"}]},
                status=status.HTTP_404_NOT_FOUND
            )