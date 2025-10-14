import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from api.models import Tenant
from api.models import set_current_tenant, clear_current_tenant

logger = logging.getLogger(__name__)


class SubdomainMiddleware(MiddlewareMixin):
    """
    Extract tenant from subdomain and set in request
    Must run BEFORE authentication middleware
    """
    
    # Paths that don't require tenant context
    EXEMPT_PATHS = [
        '/admin/',
        '/api/v1/tenant/register',
        '/api/v1/tenant/login',
        '/api/v1/tenant/list',
        '/health',
        '/static/',
        '/media/',
    ]
    
    def process_request(self, request):
        """Extract tenant from subdomain"""
        # Check if path is exempt
        if self._is_exempt_path(request.path):
            request.tenant = None
            clear_current_tenant()
            return None
        
        # Extract tenant from subdomain or header
        tenant = self._get_tenant_from_request(request)
        
        if tenant:
            request.tenant = tenant
            set_current_tenant(tenant)  # Set in thread-local for managers
            logger.debug(f"✅ Tenant set: {tenant.name} ({tenant.subdomain})")
        else:
            request.tenant = None
            clear_current_tenant()
            
            # For non-exempt paths, warn about missing tenant
            if not self._is_exempt_path(request.path):
                logger.warning(f"⚠️  No tenant found for: {request.path}")
        
        return None
    
    def process_response(self, request, response):
        """Clean up thread-local storage"""
        clear_current_tenant()
        return response
    
    def _is_exempt_path(self, path):
        """Check if path doesn't require tenant"""
        return any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS)
    
    def _get_tenant_from_request(self, request):
        """Extract tenant from subdomain or header"""
        # Priority 1: Subdomain
        host = request.get_host().split(':')[0]  # Remove port
        
        if '.' in host and not host.startswith('www'):
            subdomain = host.split('.')[0].lower()
            
            # Skip localhost, IP addresses
            if subdomain not in ['localhost', 'www', 'api', '127'] and not subdomain.replace('.', '').isdigit():
                try:
                    tenant = Tenant.objects.get(
                        subdomain=subdomain,
                        is_active=True
                    )
                    logger.debug(f"Found tenant by subdomain: {subdomain}")
                    return tenant
                except Tenant.DoesNotExist:
                    logger.warning(f"Tenant not found for subdomain: {subdomain}")
                except Tenant.MultipleObjectsReturned:
                    logger.error(f"Multiple tenants found for subdomain: {subdomain}")
                    # This shouldn't happen with unique constraint!
        
        # Priority 2: Custom header (for API calls)
        tenant_header = request.headers.get('X-Tenant-Subdomain')
        if tenant_header:
            try:
                tenant = Tenant.objects.get(
                    subdomain=tenant_header.lower(),
                    is_active=True
                )
                logger.debug(f"Found tenant by header: {tenant_header}")
                return tenant
            except Tenant.DoesNotExist:
                logger.warning(f"Tenant not found for header: {tenant_header}")
        
        return None