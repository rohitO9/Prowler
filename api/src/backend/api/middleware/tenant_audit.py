import logging
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('tenant.audit')


class TenantAuditMiddleware(MiddlewareMixin):
    """
    Log all tenant access and security events for auditing
    """
    
    def process_request(self, request):
        """Mark request start time"""
        request._audit_start_time = time.time()
    
    def process_response(self, request, response):
        """Log access and security events"""
        duration = time.time() - getattr(request, '_audit_start_time', time.time())
        
        tenant = getattr(request, 'tenant', None)
        user = request.user if hasattr(request, 'user') else None
        
        # Get user email or IP
        user_identifier = (
            user.email if user and user.is_authenticated 
            else request.META.get('REMOTE_ADDR', 'unknown')
        )
        
        # Log different events based on status code
        if response.status_code == 403:
            # Security violation
            logger.warning(
                f"ACCESS_DENIED | "
                f"user={user_identifier} | "
                f"tenant={tenant.subdomain if tenant else 'none'} | "
                f"path={request.path} | "
                f"method={request.method} | "
                f"duration={duration:.3f}s"
            )
        
        elif response.status_code >= 400:
            # Client or server error
            logger.info(
                f"ERROR | "
                f"status={response.status_code} | "
                f"user={user_identifier} | "
                f"tenant={tenant.subdomain if tenant else 'none'} | "
                f"path={request.path} | "
                f"method={request.method}"
            )
        
        elif tenant and user and user.is_authenticated:
            # Successful tenant access
            logger.info(
                f"ACCESS | "
                f"user={user_identifier} | "
                f"tenant={tenant.subdomain} | "
                f"path={request.path} | "
                f"method={request.method} | "
                f"status={response.status_code} | "
                f"duration={duration:.3f}s"
            )
        
        return response
