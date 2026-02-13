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
    
    # Paths that don't require tenant context (include /v1/... when proxy strips /api)
    EXEMPT_PATHS = [
        '/admin/',
        '/api/v1/tenant/register',
        '/api/v1/tenant/login',
        '/api/v1/tenant/list',
        '/api/v1/tenant/public-info',
        '/api/v1/tokens',
        '/api/v1/users/me',
        '/api/v1/tenant/validate-invite',
        '/api/v1/tenant/accept-invite',
        '/v1/tenant/register',
        '/v1/tenant/login',
        '/v1/tenant/list',
        '/v1/tenant/public-info',
        '/v1/tenant/validate-invite',
        '/v1/tenant/accept-invite',
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
        """Extract tenant from subdomain or header. Uses two-level subdomain rule:
        - Production (e.g. vulneralq.anantacloud.com): 3 parts = app domain, no tenant.
        - Production (e.g. tenant1.vulneralq.anantacloud.com): 4+ parts = first part is tenant.
        - Localhost: company1.localhost = tenant company1.
        """
        # Priority 1: X-Tenant-Subdomain header
        tenant_header = request.headers.get('X-Tenant-Subdomain')
        if tenant_header:
            try:
                tenant = Tenant.objects.get(
                    subdomain=tenant_header.lower().strip(),
                    is_active=True
                )
                logger.debug(f"Found tenant by header: {tenant_header}")
                return tenant
            except Tenant.DoesNotExist:
                logger.warning(f"Tenant not found for header: {tenant_header}")
            except Tenant.MultipleObjectsReturned:
                logger.error(f"Multiple tenants found for header: {tenant_header}")
                return None

        # Priority 2: Subdomain with two-level rule
        host = request.get_host().split(':')[0].strip().lower()
        parts = host.split('.')

        # Localhost / dev
        if host == 'localhost' or host == '127.0.0.1' or '.localhost' in host or '.127.0.0.1' in host:
            if len(parts) >= 2 and parts[0] not in ('www', 'api', '127'):
                subdomain = parts[0]
                try:
                    return Tenant.objects.get(subdomain=subdomain, is_active=True)
                except Tenant.DoesNotExist:
                    pass
                except Tenant.MultipleObjectsReturned:
                    logger.error(f"Multiple tenants found for subdomain: {subdomain}")
                    return None
            return None

        # Production: only 4+ parts = tenant subdomain (e.g. tenant1.vulneralq.anantacloud.com)
        # 3 parts (vulneralq.anantacloud.com) = app domain, not a tenant
        if len(parts) >= 4 and parts[0] not in ('www', 'api', 'admin', 'app', 'dashboard'):
            subdomain = parts[0]
            try:
                return Tenant.objects.get(subdomain=subdomain, is_active=True)
            except Tenant.DoesNotExist:
                logger.warning(f"Tenant not found for subdomain: {subdomain}")
            except Tenant.MultipleObjectsReturned:
                logger.error(f"Multiple tenants found for subdomain: {subdomain}")
                return None

        return None