from enum import Enum
from typing import Optional

from django.db.models import QuerySet
from rest_framework.permissions import BasePermission
import logging

from api.db_router import MainRouter
from api.models import Provider, Role, User

logger = logging.getLogger(__name__)

class Permissions(Enum):
    MANAGE_USERS = "manage_users"
    MANAGE_ACCOUNT = "manage_account"
    MANAGE_BILLING = "manage_billing"
    MANAGE_PROVIDERS = "manage_providers"
    MANAGE_INTEGRATIONS = "manage_integrations"
    MANAGE_SCANS = "manage_scans"
    UNLIMITED_VISIBILITY = "unlimited_visibility"

class HasPermissions(BasePermission):
    """
    Custom permission to check if the user's role has the required permissions.
    The required permissions should be specified in the view as a list in `required_permissions`.
    """

    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            logger.debug("User not authenticated")
            return False
            
        required_permissions = getattr(view, "required_permissions", [])
        
        # Handle both enum objects and string values
        perm_values = []
        for p in required_permissions:
            if hasattr(p, 'value'):  # It's a Permissions enum
                perm_values.append(p.value)
            else:  # It's already a string
                perm_values.append(str(p))
        
        logger.debug(f"Required permissions for view {view.__class__.__name__}: {perm_values}")
        
        if not required_permissions:
            logger.debug("No permissions required, allowing access")
            return True

        try:
            # Use the default database instead of admin_db since users are stored there
            user_roles = request.user.roles.all()
            user_identifier = getattr(request.user, 'username', None) or getattr(request.user, 'email', None) or str(request.user.id)
            logger.debug(f"User {request.user.id} ({user_identifier}) has {user_roles.count()} roles")
            
            # Alternative: if you really need to use admin_db, add error handling
            # try:
            #     user = User.objects.using(MainRouter.admin_db).get(id=request.user.id)
            #     user_roles = user.roles.all()
            # except User.DoesNotExist:
            #     logger.warning(f"User {request.user.id} not found in admin database, falling back to default")
            #     user_roles = request.user.roles.all()
            
        except Exception as e:
            logger.error(f"Error fetching user roles for user {getattr(request.user, 'id', 'unknown')}: {e}")
            return False

        if not user_roles.exists():
            logger.warning(f"User {request.user.id} has no roles assigned")
            return False

        # Get the first role (assuming single role per user based on your helper function)
        user_role = user_roles.first()
        logger.debug(f"User's primary role: {user_role} (ID: {user_role.id if user_role else 'None'})")
        
        # Check if the role has all required permissions
        for perm in required_permissions:
            # Handle both enum objects and string values
            perm_name = perm.value if hasattr(perm, 'value') else str(perm)
            
            has_perm = hasattr(user_role, perm_name) and getattr(user_role, perm_name, False)
            logger.debug(f"Checking permission '{perm_name}': {has_perm}")
            
            if not has_perm:
                logger.warning(f"User {request.user.id} missing permission: {perm_name}")
                return False

        logger.debug(f"User {request.user.id} has all required permissions")
        return True

def get_role(user: User) -> Optional[Role]:
    """
    Retrieve the first role assigned to the given user.

    Returns:
        The user's first Role instance if the user has any roles, otherwise None.
    """
    return user.roles.first()

def get_providers(role: Role) -> QuerySet[Provider]:
    """
    Return a distinct queryset of Providers accessible by the given role.

    If the role has no associated provider groups, an empty queryset is returned.

    Args:
        role: A Role instance.

    Returns:
        A QuerySet of Provider objects filtered by the role's provider groups.
        If the role has no provider groups, returns an empty queryset.
    """
    tenant = role.tenant
    provider_groups = role.provider_groups.all()
    if not provider_groups.exists():
        return Provider.objects.none()

    return Provider.objects.filter(
        tenant=tenant, provider_groups__in=provider_groups
    ).distinct()
