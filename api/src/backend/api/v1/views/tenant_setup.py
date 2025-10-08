import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from api.models import Tenant, Membership
from api.v1.serializers import TenantSerializer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_tenant(request):
    """
    Setup a new tenant for the authenticated user.
    This is called when a user wants to create their own company/tenant.
    """
    try:
        data = request.data.get('data', {})
        attributes = data.get('attributes', {})
        
        company_name = attributes.get('name')
        subdomain = attributes.get('subdomain')
        
        if not company_name or not subdomain:
            return Response(
                {"errors": [{"detail": "Company name and subdomain are required"}]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate subdomain format
        if not subdomain.replace('-', '').replace('_', '').isalnum():
            return Response(
                {"errors": [{"detail": "Subdomain can only contain letters, numbers, hyphens, and underscores"}]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if subdomain is already taken
        if Tenant.objects.filter(subdomain=subdomain).exists():
            return Response(
                {"errors": [{"detail": "This subdomain is already taken"}]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Create the tenant
            tenant = Tenant.objects.create(
                name=company_name,
                subdomain=subdomain,
                is_active=True,
                trial_ends_at=timezone.now() + timedelta(days=14)  # 14-day trial
            )
            
            # Add the user as the owner
            Membership.objects.create(
                user=request.user,
                tenant=tenant,
                role='owner'
            )
            
            logger.info(f"Created tenant {tenant.name} with subdomain {tenant.subdomain} for user {request.user.email}")
            
            serializer = TenantSerializer(tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.error(f"Error setting up tenant: {str(e)}")
        return Response(
            {"errors": [{"detail": "Failed to setup tenant"}]},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_subdomain_availability(request):
    """
    Check if a subdomain is available.
    """
    subdomain = request.GET.get('subdomain')
    
    if not subdomain:
        return Response(
            {"errors": [{"detail": "Subdomain parameter is required"}]},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate subdomain format
    if not subdomain.replace('-', '').replace('_', '').isalnum():
        return Response(
            {"errors": [{"detail": "Subdomain can only contain letters, numbers, hyphens, and underscores"}]},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    is_available = not Tenant.objects.filter(subdomain=subdomain).exists()
    
    return Response({
        "data": {
            "attributes": {
                "subdomain": subdomain,
                "available": is_available
            }
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tenant_info(request):
    """
    Get information about the current tenant (from subdomain).
    Requires authentication.
    """
    if not hasattr(request, 'tenant') or not request.tenant:
        return Response(
            {"errors": [{"detail": "No tenant found for this subdomain"}]},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = TenantSerializer(request.tenant)
    return Response(serializer.data)


@api_view(['GET'])
def get_public_tenant_info(request):
    """
    Get public information about the current tenant (from subdomain).
    No authentication required - used for landing pages and public info.
    """
    logger.info(f"=== PUBLIC TENANT INFO DEBUG ===")
    logger.info(f"Request path: {request.path}")
    logger.info(f"Request host: {request.get_host()}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Has tenant attr: {hasattr(request, 'tenant')}")
    
    if hasattr(request, 'tenant'):
        logger.info(f"Tenant object: {request.tenant}")
        if request.tenant:
            logger.info(f"Tenant name: {request.tenant.name}")
            logger.info(f"Tenant subdomain: {request.tenant.subdomain}")
        else:
            logger.info("Tenant is None")
    else:
        logger.info("Request has no tenant attribute")
    
    if not hasattr(request, 'tenant') or not request.tenant:
        logger.warning("No tenant found for this subdomain")
        return Response(
            {"errors": [{"detail": "No tenant found for this subdomain"}]},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Only return public information, not sensitive data
    public_data = {
        "data": {
            "type": "tenants",
            "id": str(request.tenant.id),
            "attributes": {
                "name": request.tenant.name,
                "subdomain": request.tenant.subdomain,
                "is_active": request.tenant.is_active,
                "is_verified": request.tenant.is_verified,
                "theme_color": getattr(request.tenant, 'theme_color', '#3B82F6'),
                "secondary_color": getattr(request.tenant, 'secondary_color', '#1E40AF'),
                "logo_url": getattr(request.tenant, 'logo_url', None),
            }
        }
    }
    
    logger.info(f"Returning public data for tenant: {request.tenant.name}")
    return Response(public_data)


@api_view(['GET'])
def test_endpoint(request):
    """
    Simple test endpoint to verify URL routing is working.
    """
    logger.info("=== TEST ENDPOINT CALLED ===")
    return Response({"message": "Test endpoint is working!", "path": request.path})
