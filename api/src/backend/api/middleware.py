import logging
import time

from config.custom_logging import BackendLogger
from django.utils.functional import SimpleLazyObject
from api.models import Tenant


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

        if request.user.is_authenticated:
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
                default_tenant = request.user.tenant_memberships.filter(is_active=True).first()
                if default_tenant:
                    request.tenant = default_tenant.tenant
                    logger.debug(f"Set default tenant: {default_tenant.tenant.id}")

        response = self.get_response(request)
        return response
