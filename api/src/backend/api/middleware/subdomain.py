import logging
import json
import time
from django.http import Http404
from api.models import Tenant

logger = logging.getLogger(__name__)

# Shared exempt paths for all middleware classes
EXEMPT_PATHS = [
    '/api/v1/tenant/register',
    '/api/v1/tenant/register/',
    '/api/v1/tenant/login',
    '/api/v1/tenant/login/',
    '/api/v1/tokens',
    '/api/v1/tokens/',
    '/api/v1/users/me',
    '/api/v1/users/me/',
    '/api/v1/auth/azure/callback',
    '/api/v1/auth/azure/callback/',
    '/api/v1/detect-idp',
    '/api/v1/detect-idp/',
    '/api/health',
    '/api/health/',
    '/admin',
    '/admin/',
    '/api/v1/tenant/register-tenant/',
    '/api/v1/tenant/register-tenant',
    '/api/v1/tenant/public-info/',
]


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
        logger.debug(f"[TENANT_MIDDLEWARE] Processing request: {request.method} {request.path}")
        
        # Check if this path should be exempt from tenant processing
        should_exempt = any(request.path.startswith(path) for path in EXEMPT_PATHS)
        logger.debug(f"[TENANT_MIDDLEWARE] Checking if path '{request.path}' should be exempt: {should_exempt}")
        
        if should_exempt:
            logger.info(f"[TENANT_MIDDLEWARE] ✅ EXEMPTING path '{request.path}' from tenant context processing")
            request.tenant_id = None
            request.tenant_name = None
            response = self.get_response(request)
            return response
        
        # Get tenant from request (set by SubdomainMiddleware)
        tenant = getattr(request, 'tenant', None)
        logger.debug(f"[TENANT_MIDDLEWARE] Tenant from request: {tenant}")
        
        if tenant:
            # Set tenant context for the request
            request.tenant_id = tenant.id
            request.tenant_name = tenant.name
            logger.info(f"[TENANT_MIDDLEWARE] ✅ Set tenant context - ID: {tenant.id}, Name: {tenant.name}")
        else:
            request.tenant_id = None
            request.tenant_name = None
            logger.debug(f"[TENANT_MIDDLEWARE] ❌ No tenant context available for {request.path}")

        response = self.get_response(request)
        logger.debug(f"[TENANT_MIDDLEWARE] Request processing complete for {request.path}")
        return response


class SubdomainMiddleware:
    """
    Middleware to extract tenant from subdomain.
    
    Handles both subdomain.localhost:3000 and custom domains.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add comprehensive logging
        logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Processing request: {request.method} {request.path}")
        logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Host: {request.get_host()}")
        logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Headers: {dict(request.headers)}")
        
        # Check if this path should be exempt from tenant processing
        should_exempt = any(request.path.startswith(path) for path in EXEMPT_PATHS)
        logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Checking if path '{request.path}' should be exempt: {should_exempt}")
        
        if should_exempt:
            logger.info(f"[SUBDOMAIN_MIDDLEWARE] ✅ EXEMPTING path '{request.path}' from tenant processing")
            request.tenant = None
            response = self.get_response(request)
            return response
        
        # Extract tenant from subdomain
        logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Extracting tenant from subdomain...")
        tenant = self.get_tenant_from_request(request)
        
        if tenant:
            request.tenant = tenant
            logger.info(f"[SUBDOMAIN_MIDDLEWARE] ✅ Tenant found: {tenant.name} (ID: {tenant.id})")
        else:
            request.tenant = None
            logger.warning(f"[SUBDOMAIN_MIDDLEWARE] ❌ No tenant found for subdomain")

        response = self.get_response(request)
        logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Request processing complete for {request.path}")
        return response

    def get_tenant_from_request(self, request):
        """
        Extract tenant from request subdomain or domain.
        """
        host = request.get_host().split(':')[0]  # Remove port if present
        logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Extracted host: '{host}'")
        
        # Handle localhost development
        if host.endswith('.localhost'):
            subdomain = host.replace('.localhost', '')
            logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Extracted subdomain: '{subdomain}'")
            
            if subdomain and subdomain != 'www':
                logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Looking up tenant with subdomain: '{subdomain}'")
                try:
                    # First, try to get existing tenant
                    tenant = Tenant.objects.filter(name=subdomain).first()
                    if tenant:
                        logger.info(f"[SUBDOMAIN_MIDDLEWARE] ✅ Found existing tenant: {tenant.name} (ID: {tenant.id})")
                        return tenant
                    
                    logger.debug(f"[SUBDOMAIN_MIDDLEWARE] No existing tenant found, creating new one...")
                    # If no tenant exists, create one
                    tenant = Tenant.objects.create(name=subdomain)
                    logger.info(f"[SUBDOMAIN_MIDDLEWARE] ✅ Created new tenant: {tenant.name} (ID: {tenant.id})")
                    return tenant
                except Exception as e:
                    logger.error(f"[SUBDOMAIN_MIDDLEWARE] ❌ Error getting/creating tenant: {e}")
                    return None
            else:
                logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Invalid subdomain: '{subdomain}' (empty or www)")
        else:
            logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Host '{host}' does not end with '.localhost'")
        
        # Handle custom domains - try to find by name
        logger.debug(f"[SUBDOMAIN_MIDDLEWARE] Attempting to find tenant by host name: '{host}'")
        try:
            tenant = Tenant.objects.get(name=host)
            logger.info(f"[SUBDOMAIN_MIDDLEWARE] ✅ Found tenant by host name: {tenant.name} (ID: {tenant.id})")
            return tenant
        except Tenant.DoesNotExist:
            logger.debug(f"[SUBDOMAIN_MIDDLEWARE] No tenant found for host: '{host}'")
        except Exception as e:
            logger.error(f"[SUBDOMAIN_MIDDLEWARE] ❌ Error looking up tenant by host: {e}")
        
        logger.debug(f"[SUBDOMAIN_MIDDLEWARE] No tenant found for request")
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