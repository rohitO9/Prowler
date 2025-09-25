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
        detail=True,
        methods=['post'],
        url_path='invitations',
        permission_classes=[IsAuthenticated],
    )
    def create_invitation(self, request, pk=None):
        """
        Create an invitation for a new member to join the tenant.
        
        Expected payload:
        {
            "email": "user@example.com",
            "role": "member|admin",
            "expires_in_days": 7  # optional
        }
        """
        tenant = self.get_object()
        serializer = TenantInvitationSerializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                invitation = Invitation.objects.create(
                    tenant=tenant,
                    invited_by=request.user,
                    **serializer.validated_data
                )

                # Log the invitation creation
                logger.info(
                    f"Tenant invitation created",
                    extra={
                        "tenant_id": tenant.id,
                        "invited_by": request.user.id,
                        "invited_email": serializer.validated_data["email"],
                        "invitation_id": invitation.id
                    }
                )

                return Response({
                    "message": "Invitation sent successfully",
                    "invitation_id": invitation.id,
                    "expires_at": invitation.expires_at
                }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            logger.warning(
                f"Invalid invitation request",
                extra={
                    "tenant_id": tenant.id,
                    "error": str(e),
                    "request_data": request.data
                }
            )
            return Response({
                "error": "Invalid invitation request",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(
                f"Failed to create tenant invitation",
                extra={
                    "tenant_id": tenant.id,
                    "error": str(e),
                    "request_data": request.data
                },
                exc_info=True
            )
            return Response({
                "error": "Failed to create invitation. Please try again later."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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