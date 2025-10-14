from functools import wraps
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def require_tenant(view_func):
    """
    Decorator to ensure request has valid tenant context
    Use on all tenant-scoped API endpoints
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if request has tenant
        if not hasattr(request, 'tenant') or not request.tenant:
            logger.warning(f"Endpoint {view_func.__name__} called without tenant context")
            return Response({
                'errors': [{
                    'status': '400',
                    'code': 'missing_tenant',
                    'title': 'Tenant Required',
                    'detail': 'This endpoint requires tenant context. Ensure you are accessing via tenant subdomain.',
                }]
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if tenant is active
        if not request.tenant.is_active:
            logger.warning(f"Access attempt to inactive tenant: {request.tenant.subdomain}")
            return Response({
                'errors': [{
                    'status': '403',
                    'code': 'tenant_inactive',
                    'title': 'Tenant Inactive',
                    'detail': 'This organization account is currently inactive.',
                }]
            }, status=status.HTTP_403_FORBIDDEN)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def require_tenant_admin(view_func):
    """
    Decorator to require tenant admin role
    """
    @wraps(view_func)
    @require_tenant
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return Response({
                'errors': [{
                    'status': '401',
                    'code': 'authentication_required',
                    'title': 'Authentication Required',
                    'detail': 'You must be logged in to access this resource.',
                }]
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if user is admin for this tenant
        # Option 1: Check if user is staff/superuser
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Option 2: Check TenantMembership role (if implemented)
        # from api.models import TenantMembership
        # membership = TenantMembership.objects.filter(
        #     user=request.user,
        #     tenant=request.tenant,
        #     role__in=['owner', 'admin']
        # ).first()
        # if membership:
        #     return view_func(request, *args, **kwargs)
        
        logger.warning(
            f"Non-admin user {request.user.email} attempted admin action "
            f"on tenant {request.tenant.subdomain}"
        )
        
        return Response({
            'errors': [{
                'status': '403',
                'code': 'insufficient_permissions',
                'title': 'Forbidden',
                'detail': 'You do not have admin permissions for this organization.',
            }]
        }, status=status.HTTP_403_FORBIDDEN)
    
    return wrapper


def tenant_scoped_queryset(queryset_or_model):
    """
    Decorator to automatically scope queryset to current tenant
    
    Usage:
        @tenant_scoped_queryset(Resource)
        def list_resources(request):
            # queryset is already filtered by tenant
            return queryset
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Add tenant-scoped queryset to request
            if hasattr(request, 'tenant') and request.tenant:
                from django.db.models import Model
                
                if isinstance(queryset_or_model, type) and issubclass(queryset_or_model, Model):
                    request.tenant_queryset = queryset_or_model.objects.filter(tenant=request.tenant)
                else:
                    request.tenant_queryset = queryset_or_model.filter(tenant=request.tenant)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator