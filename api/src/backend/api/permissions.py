import logging
from rest_framework import permissions

logger = logging.getLogger(__name__)

class HasTenantPermissions(permissions.BasePermission):
    """
    Custom permission to check if user has access to tenant operations.
    """
    def has_permission(self, request, view):
        # Debug logging
        logger.debug(f"Checking tenant permissions for user: {request.user}")
        logger.debug(f"Request tenant attribute exists: {hasattr(request, 'tenant')}")
        
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            logger.debug("User is not authenticated")
            return False

        # Check if request has tenant attribute
        if not hasattr(request, 'tenant'):
            logger.debug("Request does not have tenant attribute")
            return True  # Allow access if no tenant context required

        # Check if user is a member of the tenant
        tenant = request.tenant
        is_member = tenant.members.filter(id=request.user.id).exists()
        logger.debug(f"User is member of tenant: {is_member}")
        return is_member

    def has_object_permission(self, request, view, obj):
        logger.debug(f"Checking object permission for user: {request.user}")
        
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(obj, 'tenant'):
            return obj.tenant.members.filter(id=request.user.id).exists()
        
        if hasattr(obj, 'members'):
            return obj.members.filter(id=request.user.id).exists()

        return False