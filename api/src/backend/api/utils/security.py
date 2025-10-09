"""
Security utilities for multi-tenant authentication and authorization.
"""

import hashlib
import hmac
import time
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
import jwt
from cryptography.fernet import Fernet
import secrets


def generate_secure_token(payload: Dict[str, Any], expires_in: int = 3600) -> str:
    """
    Generate a secure JWT token with tenant context.
    
    Args:
        payload: Token payload data
        expires_in: Token expiration time in seconds
    
    Returns:
        Encoded JWT token
    """
    now = timezone.now()
    payload.update({
        'iat': now,
        'exp': now + timedelta(seconds=expires_in),
        'iss': settings.SECRET_KEY,
        'aud': 'prowler-multi-tenant'
    })
    
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm='HS256'
    )


def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate and decode a JWT token.
    
    Args:
        token: JWT token to validate
    
    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256'],
            audience='prowler-multi-tenant'
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def validate_password_strength(password: str) -> bool:
    """
    Validate password meets security requirements.
    
    Requirements:
    - At least 12 characters
    - Contains uppercase letter
    - Contains lowercase letter
    - Contains digit
    - Contains special character
    
    Args:
        password: Password to validate
    
    Returns:
        True if password meets requirements
    """
    if len(password) < 12:
        return False
    
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    return all([has_upper, has_lower, has_digit, has_special])


def rate_limit_login_attempts(request, email: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
    """
    Rate limit login attempts to prevent brute force attacks.
    
    Args:
        request: Django request object
        email: User email
        max_attempts: Maximum attempts allowed
        window_minutes: Time window in minutes
    
    Returns:
        True if request is allowed, False if rate limited
    """
    # Create cache key based on IP and email
    ip_address = request.META.get('REMOTE_ADDR', 'unknown')
    cache_key = f"login_attempts:{ip_address}:{email}"
    
    # Get current attempts
    attempts = cache.get(cache_key, 0)
    
    if attempts >= max_attempts:
        return False
    
    # Increment attempts
    cache.set(cache_key, attempts + 1, timeout=window_minutes * 60)
    
    return True


def generate_secure_random_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes
    
    Returns:
        Base64 encoded random token
    """
    return secrets.token_urlsafe(length)


def hash_sensitive_data(data: str) -> str:
    """
    Hash sensitive data using HMAC-SHA256.
    
    Args:
        data: Data to hash
    
    Returns:
        HMAC-SHA256 hash
    """
    return hmac.new(
        settings.SECRET_KEY.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()


def encrypt_sensitive_data(data: str) -> str:
    """
    Encrypt sensitive data using Fernet encryption.
    
    Args:
        data: Data to encrypt
    
    Returns:
        Encrypted data
    """
    key = settings.SECRETS_ENCRYPTION_KEY.encode()
    fernet = Fernet(key)
    return fernet.encrypt(data.encode()).decode()


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data using Fernet decryption.
    
    Args:
        encrypted_data: Encrypted data
    
    Returns:
        Decrypted data
    """
    key = settings.SECRETS_ENCRYPTION_KEY.encode()
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data.encode()).decode()


def validate_tenant_subdomain(subdomain: str) -> bool:
    """
    Validate tenant subdomain format.
    
    Requirements:
    - 3-63 characters
    - Only lowercase letters, numbers, and hyphens
    - Cannot start or end with hyphen
    - Cannot be reserved names
    
    Args:
        subdomain: Subdomain to validate
    
    Returns:
        True if valid subdomain
    """
    if not subdomain or len(subdomain) < 3 or len(subdomain) > 63:
        return False
    
    # Check format
    if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', subdomain):
        return False
    
    # Check reserved names
    reserved_names = {
        'www', 'api', 'admin', 'app', 'mail', 'ftp', 'blog', 'shop',
        'support', 'help', 'docs', 'status', 'cdn', 'assets', 'static'
    }
    
    if subdomain.lower() in reserved_names:
        return False
    
    return True


def generate_tenant_invitation_token(tenant_id: str, email: str, role: str = 'member') -> str:
    """
    Generate secure invitation token for tenant.
    
    Args:
        tenant_id: Tenant ID
        email: Invited user email
        role: User role in tenant
    
    Returns:
        Invitation token
    """
    payload = {
        'tenant_id': tenant_id,
        'email': email,
        'role': role,
        'type': 'invitation',
        'iat': timezone.now(),
        'exp': timezone.now() + timedelta(days=7)  # 7 days expiry
    }
    
    return generate_secure_token(payload, expires_in=7 * 24 * 3600)


def validate_tenant_invitation_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate tenant invitation token.
    
    Args:
        token: Invitation token
    
    Returns:
        Token payload or None if invalid
    """
    payload = validate_token(token)
    if not payload:
        return None
    
    if payload.get('type') != 'invitation':
        return None
    
    return payload


def check_tenant_feature_access(tenant, feature_name: str) -> bool:
    """
    Check if tenant can access a specific feature.
    
    Args:
        tenant: Tenant instance
        feature_name: Feature name to check
    
    Returns:
        True if tenant can access feature
    """
    # Basic subscription check
    if not tenant.can_access_feature(feature_name):
        return False
    
    # Feature-specific checks
    feature_requirements = {
        'advanced_analytics': lambda t: t.subscription_status in ['active', 'trial'],
        'custom_branding': lambda t: t.subscription_status == 'active',
        'api_access': lambda t: t.subscription_status in ['active', 'trial'],
        'sso_integration': lambda t: t.subscription_status == 'active',
    }
    
    requirement_func = feature_requirements.get(feature_name)
    if requirement_func:
        return requirement_func(tenant)
    
    return True


def audit_tenant_access(user, tenant, action: str, details: Dict[str, Any] = None):
    """
    Log tenant access for audit purposes.
    
    Args:
        user: User instance
        tenant: Tenant instance
        action: Action performed
        details: Additional details
    """
    from api.models import AuditLog
    
    AuditLog.objects.create(
        user=user,
        tenant=tenant,
        action=action,
        details=details or {},
        ip_address=user.last_login_ip,
        timestamp=timezone.now()
    )


def sanitize_tenant_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize tenant data to prevent data leakage.
    
    Args:
        data: Data to sanitize
    
    Returns:
        Sanitized data
    """
    # Remove sensitive fields
    sensitive_fields = {
        'password', 'secret', 'key', 'token', 'auth', 'credential'
    }
    
    sanitized = {}
    for key, value in data.items():
        if not any(sensitive in key.lower() for sensitive in sensitive_fields):
            sanitized[key] = value
    
    return sanitized


class TenantSecurityValidator:
    """
    Centralized validator for tenant security operations.
    """
    
    @staticmethod
    def validate_tenant_access(user, tenant) -> tuple[bool, str]:
        """
        Validate user access to tenant.
        
        Returns:
            (is_valid, error_message)
        """
        if not user.is_active:
            return False, "User account is inactive"
        
        if user.is_locked():
            return False, "User account is locked"
        
        if not tenant.is_active:
            return False, "Tenant account is inactive"
        
        if not user.can_access_tenant(tenant.id):
            return False, "User does not belong to this tenant"
        
        return True, ""
    
    @staticmethod
    def validate_tenant_permission(user, tenant, permission: str) -> tuple[bool, str]:
        """
        Validate user permission in tenant.
        
        Returns:
            (has_permission, error_message)
        """
        is_valid, error = TenantSecurityValidator.validate_tenant_access(user, tenant)
        if not is_valid:
            return False, error
        
        try:
            from api.models import TenantMembership
            membership = TenantMembership.objects.get(
                user=user,
                tenant=tenant,
                is_active=True
            )
            
            if not membership.has_permission(permission):
                return False, f"Permission '{permission}' required"
            
            return True, ""
        except TenantMembership.DoesNotExist:
            return False, "User membership not found"
    
    @staticmethod
    def validate_tenant_data_access(user, tenant, data_tenant_id) -> tuple[bool, str]:
        """
        Validate user can access data from specific tenant.
        
        Returns:
            (can_access, error_message)
        """
        if str(tenant.id) != str(data_tenant_id):
            return False, "Data does not belong to current tenant"
        
        return TenantSecurityValidator.validate_tenant_access(user, tenant)
