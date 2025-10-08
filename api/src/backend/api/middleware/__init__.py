import logging
import time

from config.custom_logging import BackendLogger
from django.utils.functional import SimpleLazyObject
from api.models import Tenant
# Removed circular import - subdomain logic moved inline


def extract_auth_info(request) -> dict:
    if getattr(request, "auth", None) is not None:
        tenant_id = request.auth.get("tenant_id", "N/A")
        user_id = request.auth.get("sub", "N/A")
    else:
        tenant_id, user_id = "N/A", "N/A"
    return {"tenant_id": tenant_id, "user_id": user_id}


class APILoggingMiddleware:
    """
    Middleware for logging API requests.

    This middleware logs details of API requests, including the typical request metadata among other useful information.

    Args:
        get_response (Callable): A callable to get the response, typically the next middleware or view.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger(BackendLogger.API)

    def __call__(self, request):
        request_start_time = time.time()

        response = self.get_response(request)
        duration = time.time() - request_start_time
        auth_info = extract_auth_info(request)
        self.logger.info(
            "",
            extra={
                "user_id": auth_info["user_id"],
                "tenant_id": auth_info["tenant_id"],
                "method": request.method,
                "path": request.path,
                "query_params": request.GET.dict(),
                "status_code": response.status_code,
                "duration": duration,
            },
        )

        return response


logger = logging.getLogger(__name__)


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set tenant as None by default
        request.tenant = None
        
        # First, try to get tenant from subdomain
        tenant = self.get_tenant_from_subdomain(request)
        if tenant:
            request.tenant = tenant
            logger.debug(f"Set tenant from subdomain: {tenant.subdomain} ({tenant.name})")
        
        # If no tenant from subdomain and user is authenticated, try other methods
        if not request.tenant and request.user.is_authenticated:
            logger.debug(f"User authenticated: {request.user.is_authenticated}")
            logger.debug(f"User: {request.user}")
            
            # Try to get tenant ID from header
            tenant_id = request.headers.get("X-Tenant-ID")

            # If not in header, try to get from query params
            if not tenant_id and request.GET.get("tenant"):
                tenant_id = request.GET.get("tenant")

            logger.debug(f"Looking for tenant with ID: {tenant_id}")

            if tenant_id:
                try:
                    tenant = Tenant.objects.get(id=tenant_id)
                    if tenant.members.filter(id=request.user.id).exists():
                        request.tenant = tenant
                        logger.debug(f"Set tenant for request: {tenant.id}")
                except Tenant.DoesNotExist:
                    logger.debug(f"Tenant not found: {tenant_id}")
            else:
                # If no tenant specified, try to get user's default tenant
                try:
                    default_tenant = request.user.memberships.first()
                    if default_tenant:
                        request.tenant = default_tenant.tenant
                        logger.debug(f"Set default tenant: {default_tenant.tenant.id}")
                    else:
                        logger.debug("No default tenant found for user")
                except Exception as e:
                    logger.debug(f"Error getting default tenant: {e}")

        response = self.get_response(request)
        return response
    
    def get_tenant_from_subdomain(self, request):
        """
        Extract tenant from request subdomain or domain.
        """
        host = request.get_host().split(':')[0]  # e.g., "company1.localhost"
        logger.info(f"Extracted host: {host}")

        # Split host by dot
        host_parts = host.split('.')

        # Example for localhost based local development:
        if host.endswith('localhost') and len(host_parts) > 1:
            subdomain = host_parts[0]
        else:
            # For production domains like "company1.example.com"
            subdomain = host_parts[0] if len(host_parts) > 2 else None

        logger.info(f"Extracted subdomain: {subdomain}")

        # HARDCODED TEST: For development, create a test tenant if none exists
        # Only for plain localhost (no subdomain) - skip if we have a subdomain
        if (host == 'localhost' or host == '127.0.0.1') and subdomain is None:
            logger.info("Development mode: checking for test tenant")
            try:
                # Try to get or create a test tenant
                test_tenant, created = Tenant.objects.get_or_create(
                    subdomain='test',
                    defaults={
                        'name': 'Test Company',
                        'is_active': True,
                        'is_verified': True
                    }
                )
                if created:
                    logger.info(f"Created test tenant: {test_tenant.name} (ID: {test_tenant.id})")
                else:
                    logger.info(f"Found existing test tenant: {test_tenant.name} (ID: {test_tenant.id})")
                return test_tenant
            except Exception as e:
                logger.warning(f"Error creating test tenant: {e}")
                return None
        
        try:
            # Handle localhost development with subdomains
            if host.endswith('.localhost'):
                subdomain = host.replace('.localhost', '')
                logger.info(f"Extracted subdomain: {subdomain}")
                if subdomain and subdomain != 'www':
                    try:
                        tenant = Tenant.objects.get(subdomain=subdomain, is_active=True)
                        logger.info(f"Found tenant: {tenant.name} (ID: {tenant.id})")
                        return tenant
                    except Tenant.DoesNotExist:
                        logger.warning(f"Tenant not found for subdomain: {subdomain}")
                        # Auto-create tenant for development subdomains
                        logger.info(f"Auto-creating development tenant for subdomain: {subdomain}")
                        try:
                            tenant = Tenant.objects.create(
                                name=f"{subdomain.title()} Company",
                                subdomain=subdomain,
                                is_active=True,
                                is_verified=True
                            )
                            logger.info(f"Created development tenant: {tenant.name} (ID: {tenant.id})")
                            return tenant
                        except Exception as e:
                            logger.error(f"Failed to create development tenant: {e}")
                            return None
            
            # Handle custom domains
            try:
                return Tenant.objects.get(domain=host, is_active=True)
            except Tenant.DoesNotExist:
                pass
            
            # Handle www subdomain (redirect to main domain)
            if host.startswith('www.'):
                main_domain = host[4:]  # Remove 'www.'
                try:
                    return Tenant.objects.get(domain=main_domain, is_active=True)
                except Tenant.DoesNotExist:
                    pass
        except Exception as e:
            # Handle database schema issues (missing columns)
            logger.warning(f"Database schema issue in tenant lookup: {e}")
            return None
        
        return None