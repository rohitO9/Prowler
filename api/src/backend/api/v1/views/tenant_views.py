import logging
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

logger = logging.getLogger(__name__)


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
                "is_active": True,
                "is_verified": True,
                "theme_color": "#3B82F6",
                "secondary_color": "#1E40AF",
                "logo_url": None,
            }
        }
    }
    
    logger.info(f"Returning public data for tenant: {request.tenant.name}")
    return Response(public_data)
