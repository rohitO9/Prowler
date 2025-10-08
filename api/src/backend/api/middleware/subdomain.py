import logging
import json
import time
from django.http import Http404
from api.models import Tenant

logger = logging.getLogger(__name__)


class APILoggingMiddleware:
    """
    Middleware to log API requests and responses.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log request
        start_time = time.time()
        
        # Get request data
        method = request.method
        path = request.get_full_path()
        user = getattr(request, 'user', None)
        user_info = str(user) if user and hasattr(user, 'username') else 'Anonymous'
        
        logger.info(f"API Request: {method} {path} - User: {user_info}")
        
        # Process request
        response = self.get_response(request)
        
        # Log response
        duration = time.time() - start_time
        status_code = response.status_code
        
        logger.info(f"API Response: {method} {path} - Status: {status_code} - Duration: {duration:.3f}s")
        
        return response


class TenantMiddleware:
    """
    Middleware to set tenant context for multi-tenancy.
    Works in conjunction with SubdomainMiddleware.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get tenant from request (set by SubdomainMiddleware)
        tenant = getattr(request, 'tenant', None)
        
        if tenant:
            # Set tenant context for the request
            request.tenant_id = tenant.id
            request.tenant_name = tenant.name
            logger.debug(f"TenantMiddleware: Set tenant context - ID: {tenant.id}, Name: {tenant.name}")
        else:
            request.tenant_id = None
            request.tenant_name = None
            logger.debug("TenantMiddleware: No tenant context available")

        response = self.get_response(request)
        return response


class SubdomainMiddleware:
    """
    Middleware to extract tenant from subdomain.
    
    Handles both subdomain.localhost:3000 and custom domains.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract tenant from subdomain
        tenant = self.get_tenant_from_request(request)
        if tenant:
            request.tenant = tenant
            logger.debug(f"Set tenant from subdomain: {tenant.name} (ID: {tenant.id})")
        else:
            request.tenant = None
            logger.debug("No tenant found for subdomain")

        response = self.get_response(request)
        return response

    def get_tenant_from_request(self, request):
        """
        Extract tenant from request subdomain or domain.
        """
        host = request.get_host().split(':')[0]  # Remove port if present
        
        # Handle localhost development
        if host.endswith('.localhost'):
            subdomain = host.replace('.localhost', '')
            if subdomain and subdomain != 'www':
                try:
                    # First, try to get existing tenant
                    tenant = Tenant.objects.filter(name=subdomain).first()
                    if tenant:
                        logger.info(f"Found existing tenant: {tenant.name} (ID: {tenant.id})")
                        return tenant
                    
                    # If no tenant exists, create one
                    tenant = Tenant.objects.create(name=subdomain)
                    logger.info(f"Created new tenant: {tenant.name} (ID: {tenant.id})")
                    return tenant
                except Exception as e:
                    logger.error(f"Error getting/creating tenant: {e}")
                    return None
        
        # Handle custom domains - try to find by name
        try:
            return Tenant.objects.get(name=host)
        except Tenant.DoesNotExist:
            pass
        
        return None

    def get_subdomain(self, request):
        """
        Extract subdomain from request host.
        """
        host = request.get_host().split(':')[0]
        
        # Handle localhost development
        if host.endswith('.localhost'):
            return host.replace('.localhost', '')
        
        # Handle custom domains
        if '.' in host and not host.startswith('www.'):
            return host.split('.')[0]
        
        return None