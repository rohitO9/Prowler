"""
Enhanced SCIM Authentication with Rate Limiting
"""

import time
import logging
from django.core.cache import cache
from django.core.exceptions import ValidationError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, Throttled
from api.v1.models.azure_sso import AzureSSOConfig, AzureADAuditLog

logger = logging.getLogger(__name__)


class SCIMTokenAuthentication(BaseAuthentication):
    """
    Enhanced SCIM Bearer Token Authentication with Rate Limiting
    """
    
    RATE_LIMIT_REQUESTS = 100  # requests per minute
    RATE_LIMIT_WINDOW = 60     # seconds
    
    def authenticate(self, request):
        """
        Authenticate the request using SCIM bearer token with rate limiting
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        
        try:
            # Get SSO config by token
            sso_config = AzureSSOConfig.objects.select_related('tenant').get(
                scim_token=token, 
                is_active=True,
                scim_enabled=True
            )
            
            tenant = sso_config.tenant
            
            # Apply rate limiting
            if not self._check_rate_limit(tenant, request):
                # Log rate limit violation
                AzureADAuditLog.log_event(
                    tenant=tenant,
                    event_type='SCIM_RATE_LIMIT_EXCEEDED',
                    description=f'SCIM rate limit exceeded for tenant {tenant.name}',
                    details={
                        'ip_address': request.META.get('REMOTE_ADDR'),
                        'user_agent': request.META.get('HTTP_USER_AGENT'),
                        'path': request.path
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
                
                raise Throttled(detail="SCIM rate limit exceeded")
            
            # Log successful SCIM request
            AzureADAuditLog.log_event(
                tenant=tenant,
                event_type='SCIM_REQUEST',
                description=f'SCIM request to {request.path}',
                details={
                    'method': request.method,
                    'path': request.path,
                    'ip_address': request.META.get('REMOTE_ADDR')
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return (tenant, token)
            
        except AzureSSOConfig.DoesNotExist:
            # Log invalid token attempt
            AzureADAuditLog.log_event(
                tenant=None,
                event_type='SCIM_INVALID_TOKEN',
                description=f'Invalid SCIM token attempt',
                details={
                    'token_prefix': token[:10] + '...',
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'path': request.path
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            raise AuthenticationFailed('Invalid SCIM token')
        except Throttled:
            raise
        except Exception as e:
            logger.error(f"SCIM authentication error: {e}")
            raise AuthenticationFailed('SCIM authentication failed')
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return 'Bearer'
    
    def _check_rate_limit(self, tenant, request):
        """
        Check if request is within rate limit for tenant
        
        Args:
            tenant: Tenant object
            request: HTTP request
            
        Returns:
            bool: True if within rate limit, False otherwise
        """
        try:
            # Create rate limit key
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
            rate_key = f"scim_rate_limit:{tenant.id}:{ip_address}"
            
            # Get current count
            current_count = cache.get(rate_key, 0)
            
            if current_count >= self.RATE_LIMIT_REQUESTS:
                return False
            
            # Increment counter
            cache.set(rate_key, current_count + 1, self.RATE_LIMIT_WINDOW)
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Allow request if rate limiting fails
            return True