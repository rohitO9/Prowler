from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.db import transaction
from api.base_views import BaseTenantViewset
from api.models import Tenant, Invitation
from api.v1.serializers import TenantSerializer, TenantInvitationSerializer
from api.services.invitation_service import TenantInvitationService
from api.utils.logging import get_logger
from django.utils import timezone
from datetime import timedelta

logger = get_logger(__name__)

class TenantViewSet(BaseTenantViewset):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer

    filterset_fields = ["name"]
    search_fields = ["name"]

    def set_required_permissions(self):
        self.required_permissions = ["manage_account"]

    def get_queryset(self):
        return Tenant.objects.all()

    @action(
        detail=False,
        methods=['post'],
        url_path='invitations',
        permission_classes=[IsAuthenticated],
    )
    def create_invitation(self, request):
        """Create an invitation for a new member to join the tenant."""
        tenant_id = request.data.get('tenant_id')
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            
            serializer = TenantInvitationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            invitation = Invitation.objects.create(
                tenant=tenant,
                email=serializer.validated_data['email'],
                invited_by=request.user,
                state='pending',
                role=serializer.validated_data['role'],
                expires_at=timezone.now() + timedelta(
                    days=serializer.validated_data.get('expires_in_days', 7)
                )
            )
            
            return Response(
                TenantInvitationSerializer(invitation).data,
                status=status.HTTP_201_CREATED
            )
    
        except Tenant.DoesNotExist:
            return Response(
                {"error": "Tenant not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        except ValidationError as e:
            logger.warning(
                f"Invalid invitation request",
                extra={
                    "tenant_id": tenant_id,
                    "error": str(e),
                    "request_data": request.data
                }
            )
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(
                f"Failed to create invitation",
                extra={
                    "tenant_id": tenant_id,
                    "error": str(e)
                },
                exc_info=True
            )
            return Response(
                {"error": "Failed to create invitation"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=True,
        methods=['get'],
        url_path='invitations',
        permission_classes=[IsAuthenticated],
    )
    def list_invitations(self, request, pk=None):
        """List all active invitations for the tenant"""
        tenant = self.get_object()
        
        try:
            invitation_service = TenantInvitationService()
            invitations = invitation_service.get_active_invitations(tenant)
            
            return Response({
                "invitations": invitations
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                f"Failed to list tenant invitations",
                extra={"tenant_id": tenant.id, "error": str(e)},
                exc_info=True
            )
            return Response({
                "error": "Failed to retrieve invitations"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(
        detail=True,
        methods=['delete'],
        url_path='invitations/(?P<invitation_id>[^/.]+)',
        permission_classes=[IsAuthenticated],
    )
    def revoke_invitation(self, request, pk=None, invitation_id=None):
        """Revoke a specific invitation"""
        tenant = self.get_object()
        
        try:
            invitation_service = TenantInvitationService()
            invitation_service.revoke_invitation(
                tenant=tenant,
                invitation_id=invitation_id,
                revoked_by=request.user
            )

            logger.info(
                f"Tenant invitation revoked",
                extra={
                    "tenant_id": tenant.id,
                    "invitation_id": invitation_id,
                    "revoked_by": request.user.id
                }
            )

            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(
                f"Failed to revoke invitation",
                extra={
                    "tenant_id": tenant.id,
                    "invitation_id": invitation_id,
                    "error": str(e)
                },
                exc_info=True
            )
            return Response({
                "error": "Failed to revoke invitation"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)