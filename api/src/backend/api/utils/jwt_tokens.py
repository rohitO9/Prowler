"""
JWT Token Management with RS256 Algorithm
"""

import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class JWTTokenService:
    """
    Service for managing JWT tokens with RS256 algorithm
    """
    
    def __init__(self):
        self.private_key = self._get_private_key()
        self.public_key = self._get_public_key()
        self.algorithm = 'RS256'
    
    def _get_private_key(self):
        """Get private key from settings or generate new one"""
        private_key_pem = getattr(settings, 'JWT_PRIVATE_KEY', None)
        
        if not private_key_pem:
            if settings.DEBUG:
                logger.warning("No JWT_PRIVATE_KEY found, generating new key for development")
                return self._generate_key_pair()[0]
            else:
                raise ImproperlyConfigured(
                    "JWT_PRIVATE_KEY must be set in production. "
                    "Generate with: python -c 'from cryptography.hazmat.primitives.asymmetric import rsa; "
                    "from cryptography.hazmat.primitives import serialization; "
                    "key = rsa.generate_private_key(public_exponent=65537, key_size=2048); "
                    "print(key.private_bytes(encoding=serialization.Encoding.PEM, "
                    "format=serialization.PrivateFormat.PKCS8, "
                    "encryption_algorithm=serialization.NoEncryption()).decode())'"
                )
        
        return serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
    
    def _get_public_key(self):
        """Get public key from private key"""
        return self.private_key.public_key()
    
    def _generate_key_pair(self):
        """Generate RSA key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        return private_key, public_key
    
    def generate_invite_token(self, user_id: str, tenant_id: str, role: str, 
                            expires_days: int = 7) -> str:
        """
        Generate JWT invite token
        
        Args:
            user_id: User UUID
            tenant_id: Tenant UUID
            role: User role
            expires_days: Token expiration in days
            
        Returns:
            str: JWT token
        """
        try:
            now = datetime.utcnow()
            payload = {
                'type': 'invite',
                'user_id': user_id,
                'tenant_id': tenant_id,
                'role': role,
                'iat': now,
                'exp': now + timedelta(days=expires_days),
                'iss': settings.JWT_ISSUER or 'prowler-saas',
                'aud': settings.JWT_AUDIENCE or 'prowler-users'
            }
            
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm=self.algorithm
            )
            
            logger.info(f"Generated invite token for user {user_id} in tenant {tenant_id}")
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate invite token: {e}")
            raise ValueError("Failed to generate invite token")
    
    def generate_session_token(self, user_id: str, tenant_id: str, 
                             expires_hours: int = 24) -> str:
        """
        Generate JWT session token
        
        Args:
            user_id: User UUID
            tenant_id: Tenant UUID
            expires_hours: Token expiration in hours
            
        Returns:
            str: JWT token
        """
        try:
            now = datetime.utcnow()
            payload = {
                'type': 'session',
                'user_id': user_id,
                'tenant_id': tenant_id,
                'iat': now,
                'exp': now + timedelta(hours=expires_hours),
                'iss': settings.JWT_ISSUER or 'prowler-saas',
                'aud': settings.JWT_AUDIENCE or 'prowler-users'
            }
            
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm=self.algorithm
            )
            
            logger.info(f"Generated session token for user {user_id} in tenant {tenant_id}")
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate session token: {e}")
            raise ValueError("Failed to generate session token")
    
    def validate_token(self, token: str, token_type: str = None) -> Dict[str, Any]:
        """
        Validate JWT token
        
        Args:
            token: JWT token
            token_type: Expected token type ('invite' or 'session')
            
        Returns:
            dict: Token payload
            
        Raises:
            jwt.InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                issuer=settings.JWT_ISSUER or 'prowler-saas',
                audience=settings.JWT_AUDIENCE or 'prowler-users'
            )
            
            # Validate token type if specified
            if token_type and payload.get('type') != token_type:
                raise jwt.InvalidTokenError(f"Invalid token type: expected {token_type}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise jwt.InvalidTokenError("Token validation failed")
    
    def refresh_token(self, token: str) -> str:
        """
        Refresh a session token
        
        Args:
            token: Current JWT token
            
        Returns:
            str: New JWT token
        """
        try:
            payload = self.validate_token(token, 'session')
            
            # Generate new token with same user and tenant
            return self.generate_session_token(
                payload['user_id'],
                payload['tenant_id']
            )
            
        except jwt.InvalidTokenError:
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise ValueError("Failed to refresh token")
    
    def get_public_key_pem(self) -> str:
        """
        Get public key in PEM format for token verification
        
        Returns:
            str: Public key in PEM format
        """
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()


# Global JWT service instance
_jwt_service = None


def get_jwt_service():
    """Get global JWT service instance"""
    global _jwt_service
    if _jwt_service is None:
        _jwt_service = JWTTokenService()
    return _jwt_service


def generate_invite_token(user_id: str, tenant_id: str, role: str, expires_days: int = 7) -> str:
    """Generate invite token"""
    return get_jwt_service().generate_invite_token(user_id, tenant_id, role, expires_days)


def generate_session_token(user_id: str, tenant_id: str, expires_hours: int = 24) -> str:
    """Generate session token"""
    return get_jwt_service().generate_session_token(user_id, tenant_id, expires_hours)


def validate_token(token: str, token_type: str = None) -> Dict[str, Any]:
    """Validate JWT token"""
    return get_jwt_service().validate_token(token, token_type)


def refresh_token(token: str) -> str:
    """Refresh session token"""
    return get_jwt_service().refresh_token(token)
