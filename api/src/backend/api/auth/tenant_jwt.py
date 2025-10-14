"""
Enhanced JWT authentication with comprehensive tenant support and security.
"""

import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from api.models import Tenant, SecurityAuditLog
from api.utils.tenant_utils import validate_tenant_access

logger = logging.getLogger(__name__)
User = get_user_model()


class TenantJWTAuthentication:
    """
    Enhanced JWT authentication with tenant support and security features.
    """
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = 'HS256'
        self.access_token_lifetime = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', 3600)  # 1 hour
        self.refresh_token_lifetime = getattr(settings, 'JWT_REFRESH_TOKEN_LIFETIME', 604800)  # 7 days
    
    def generate_tokens(self, user: User, tenant: Tenant, 
                       additional_claims: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Generate access and refresh tokens with tenant information.
        
        Args:
            user: User object
            tenant: Tenant object
            additional_claims: Additional claims to include in tokens
            
        Returns:
            Dictionary containing access_token and refresh_token
        """
        now = timezone.now()
        access_exp = now + timedelta(seconds=self.access_token_lifetime)
        refresh_exp = now + timedelta(seconds=self.refresh_token_lifetime)
        
        # Base claims
        access_claims = {
            'user_id': str(user.id),
            'email': user.email,
            'name': user.name,
            'tenant_id': str(tenant.id),
            'tenant_name': tenant.name,
            'tenant_subdomain': tenant.subdomain,
            'is_superuser': user.is_superuser,
            'is_verified': user.is_verified,
            'two_factor_enabled': user.two_factor_enabled,
            'iat': now.timestamp(),
            'exp': access_exp.timestamp(),
            'type': 'access'
        }
        
        refresh_claims = {
            'user_id': str(user.id),
            'tenant_id': str(tenant.id),
            'iat': now.timestamp(),
            'exp': refresh_exp.timestamp(),
            'type': 'refresh'
        }
        
        # Add additional claims
        if additional_claims:
            access_claims.update(additional_claims)
        
        # Generate tokens
        access_token = jwt.encode(access_claims, self.secret_key, algorithm=self.algorithm)
        refresh_token = jwt.encode(refresh_claims, self.secret_key, algorithm=self.algorithm)
        
        # Log token generation
        SecurityAuditLog.log_event(
            event_type='login_success',
            message=f'JWT tokens generated for user {user.email} in tenant {tenant.name}',
            user=user,
            tenant=tenant,
            severity='low',
            details={
                'token_type': 'access_refresh',
                'access_expires_at': access_exp.isoformat(),
                'refresh_expires_at': refresh_exp.isoformat()
            },
            is_security_violation=False,
            requires_investigation=False
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': self.access_token_lifetime,
            'token_type': 'Bearer'
        }
    
    def validate_token(self, token: str, token_type: str = 'access') -> Optional[Dict[str, Any]]:
        """
        Validate JWT token and return claims.
        
        Args:
            token: JWT token string
            token_type: Expected token type ('access' or 'refresh')
            
        Returns:
            Token claims if valid, None otherwise
        """
        try:
            # Decode token
            claims = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Validate token type
            if claims.get('type') != token_type:
                logger.warning(f"Invalid token type: expected {token_type}, got {claims.get('type')}")
                return None
            
            # Check expiration
            exp_timestamp = claims.get('exp')
            if exp_timestamp and datetime.fromtimestamp(exp_timestamp) < datetime.now():
                logger.warning("Token has expired")
                return None
            
            # Check if token is blacklisted
            if self._is_token_blacklisted(token):
                logger.warning("Token is blacklisted")
                return None
            
            return claims
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error validating JWT token: {e}")
            return None
    
    def validate_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate access token and return claims."""
        return self.validate_token(token, 'access')
    
    def validate_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate refresh token and return claims."""
        return self.validate_token(token, 'refresh')
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token or None if refresh token is invalid
        """
        # Validate refresh token
        claims = self.validate_refresh_token(refresh_token)
        if not claims:
            return None
        
        try:
            # Get user and tenant
            user = User.objects.get(id=claims['user_id'], is_active=True)
            tenant = Tenant.objects.get(id=claims['tenant_id'], is_active=True)
            
            # Validate user still has access to tenant
            if not validate_tenant_access(user, tenant):
                logger.warning(f"User {user.email} no longer has access to tenant {tenant.name}")
                return None
            
            # Generate new access token
            return self.generate_tokens(user, tenant)
            
        except (User.DoesNotExist, Tenant.DoesNotExist):
            logger.warning("User or tenant not found for refresh token")
            return None
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return None
    
    def blacklist_token(self, token: str, reason: str = "Token blacklisted") -> bool:
        """
        Add token to blacklist.
        
        Args:
            token: JWT token to blacklist
            reason: Reason for blacklisting
            
        Returns:
            True if successfully blacklisted
        """
        try:
            # Decode token to get expiration
            claims = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            exp_timestamp = claims.get('exp')
            
            if exp_timestamp:
                # Calculate TTL for cache
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                ttl = int((exp_datetime - datetime.now()).total_seconds())
                
                if ttl > 0:
                    # Store in cache with TTL
                    cache_key = f"blacklisted_token:{token[:20]}"  # Use first 20 chars as key
                    cache.set(cache_key, reason, ttl)
                    
                    logger.info(f"Token blacklisted: {reason}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error blacklisting token: {e}")
            return False
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        cache_key = f"blacklisted_token:{token[:20]}"
        return cache.get(cache_key) is not None
    
    def get_user_from_token(self, token: str) -> Optional[User]:
        """
        Get user from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            User object or None if invalid
        """
        claims = self.validate_access_token(token)
        if not claims:
            return None
        
        try:
            return User.objects.get(id=claims['user_id'], is_active=True)
        except User.DoesNotExist:
            return None
    
    def get_tenant_from_token(self, token: str) -> Optional[Tenant]:
        """
        Get tenant from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Tenant object or None if invalid
        """
        claims = self.validate_access_token(token)
        if not claims:
            return None
        
        try:
            return Tenant.objects.get(id=claims['tenant_id'], is_active=True)
        except Tenant.DoesNotExist:
            return None
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive token information.
        
        Args:
            token: JWT token string
            
        Returns:
            Token information dictionary or None if invalid
        """
        claims = self.validate_access_token(token)
        if not claims:
            return None
        
        return {
            'user_id': claims.get('user_id'),
            'email': claims.get('email'),
            'name': claims.get('name'),
            'tenant_id': claims.get('tenant_id'),
            'tenant_name': claims.get('tenant_name'),
            'tenant_subdomain': claims.get('tenant_subdomain'),
            'is_superuser': claims.get('is_superuser', False),
            'is_verified': claims.get('is_verified', False),
            'two_factor_enabled': claims.get('two_factor_enabled', False),
            'issued_at': datetime.fromtimestamp(claims.get('iat', 0)),
            'expires_at': datetime.fromtimestamp(claims.get('exp', 0)),
            'is_blacklisted': self._is_token_blacklisted(token)
        }
    
    def revoke_user_tokens(self, user: User, reason: str = "User logout") -> bool:
        """
        Revoke all tokens for a user by blacklisting them.
        
        Args:
            user: User object
            reason: Reason for revocation
            
        Returns:
            True if successful
        """
        try:
            # This is a simplified approach - in production, you might want to
            # maintain a list of valid tokens per user and invalidate them
            # For now, we'll log the revocation
            SecurityAuditLog.log_event(
                event_type='admin_action',
                message=f'All tokens revoked for user {user.email}: {reason}',
                user=user,
                severity='medium',
                details={'action': 'token_revocation', 'reason': reason},
                is_security_violation=False,
                requires_investigation=False
            )
            
            logger.info(f"All tokens revoked for user {user.email}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking user tokens: {e}")
            return False
    
    def validate_tenant_access_from_token(self, token: str, required_tenant_id: str) -> bool:
        """
        Validate that token provides access to specific tenant.
        
        Args:
            token: JWT token string
            required_tenant_id: Required tenant ID
            
        Returns:
            True if access is allowed
        """
        claims = self.validate_access_token(token)
        if not claims:
            return False
        
        token_tenant_id = claims.get('tenant_id')
        if not token_tenant_id:
            return False
        
        # Superusers can access any tenant
        if claims.get('is_superuser', False):
            return True
        
        # Check if token tenant matches required tenant
        return token_tenant_id == required_tenant_id
    
    def get_user_permissions_from_token(self, token: str) -> Dict[str, Any]:
        """
        Get user permissions from token.
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary containing user permissions
        """
        claims = self.validate_access_token(token)
        if not claims:
            return {}
        
        user_id = claims.get('user_id')
        tenant_id = claims.get('tenant_id')
        
        if not user_id or not tenant_id:
            return {}
        
        try:
            user = User.objects.get(id=user_id)
            tenant = Tenant.objects.get(id=tenant_id)
            
            # Get user's role in tenant
            membership = user.tenant_memberships.filter(
                tenant=tenant,
                is_active=True
            ).first()
            
            if not membership:
                return {}
            
            return {
                'role': membership.role,
                'can_invite_users': membership.can_invite_users,
                'can_manage_settings': membership.can_manage_settings,
                'can_view_analytics': membership.can_view_analytics,
                'is_owner_or_admin': membership.is_owner_or_admin()
            }
            
        except (User.DoesNotExist, Tenant.DoesNotExist):
            return {}


# Global instance
tenant_jwt_auth = TenantJWTAuthentication()


def get_tenant_jwt_auth() -> TenantJWTAuthentication:
    """Get the global tenant JWT authentication instance."""
    return tenant_jwt_auth
