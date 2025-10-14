"""
Tenant utilities for multi-tenant security and context management.
"""

import logging
import jwt
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from typing import Optional, Dict, Any

from api.models import Tenant, SecurityAuditLog

logger = logging.getLogger(__name__)
User = get_user_model()


def get_tenant_from_request(request) -> Optional[Tenant]:
    """
    Extract tenant information from the request.
    
    Args:
        request: Django request object
        
    Returns:
        Tenant object or None if not found
    """
    # Method 1: Extract from subdomain
    tenant = _get_tenant_from_subdomain(request)
    if tenant:
        return tenant
    
    # Method 2: Extract from headers
    tenant = _get_tenant_from_headers(request)
    if tenant:
        return tenant
    
    # Method 3: Extract from JWT token
    tenant = _get_tenant_from_token(request)
    if tenant:
        return tenant
    
    return None


def _get_tenant_from_subdomain(request) -> Optional[Tenant]:
    """Extract tenant from subdomain."""
    host = request.get_host()
    
    # Handle localhost development
    if 'localhost' in host or '127.0.0.1' in host:
        subdomain = host.split('.')[0]
        if subdomain in ['localhost', '127', '0', '0', '1']:
            return None
    else:
        # Handle production domains
        parts = host.split('.')
        if len(parts) >= 3:
            subdomain = parts[0]
        else:
            return None
    
    try:
        return Tenant.objects.get(subdomain=subdomain, is_active=True)
    except Tenant.DoesNotExist:
        return None


def _get_tenant_from_headers(request) -> Optional[Tenant]:
    """Extract tenant from custom headers."""
    tenant_id = request.headers.get('X-Tenant-ID')
    tenant_subdomain = request.headers.get('X-Tenant-Subdomain')
    
    if tenant_id:
        try:
            return Tenant.objects.get(id=tenant_id, is_active=True)
        except Tenant.DoesNotExist:
            return None
    
    if tenant_subdomain:
        try:
            return Tenant.objects.get(subdomain=tenant_subdomain, is_active=True)
        except Tenant.DoesNotExist:
            return None
    
    return None


def _get_tenant_from_token(request) -> Optional[Tenant]:
    """Extract tenant from JWT token."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    try:
        token = auth_header.split(' ')[1]
        user = get_user_from_token(token)
        if user and user.primary_tenant:
            return user.primary_tenant
    except Exception as e:
        logger.warning(f"Error extracting tenant from token: {e}")
    
    return None


def get_user_from_token(token: str) -> Optional[User]:
    """
    Extract user from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        User object or None if invalid
    """
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
        
        user_id = payload.get('user_id')
        if not user_id:
            return None
        
        # Get user from database
        user = User.objects.get(id=user_id, is_active=True)
        return user
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT token")
        return None
    except User.DoesNotExist:
        logger.warning(f"User not found for token: {user_id}")
        return None
    except Exception as e:
        logger.error(f"Error decoding JWT token: {e}")
        return None


def validate_tenant_access(user: User, tenant: Tenant) -> bool:
    """
    Validate that a user can access a specific tenant.
    
    Args:
        user: User object
        tenant: Tenant object
        
    Returns:
        True if access is allowed, False otherwise
    """
    if not user.is_active:
        return False
    
    if user.is_superuser:
        return True
    
    if user.is_locked():
        return False
    
    return user.can_access_tenant(tenant.id)


def get_tenant_context(request) -> Dict[str, Any]:
    """
    Get comprehensive tenant context for the request.
    
    Args:
        request: Django request object
        
    Returns:
        Dictionary containing tenant context information
    """
    context = {
        'tenant': None,
        'user': None,
        'has_access': False,
        'is_authenticated': False,
        'is_superuser': False
    }
    
    # Get tenant
    tenant = get_tenant_from_request(request)
    context['tenant'] = tenant
    
    # Get user
    if hasattr(request, 'user') and request.user.is_authenticated:
        context['user'] = request.user
        context['is_authenticated'] = True
        context['is_superuser'] = request.user.is_superuser
        
        # Check access
        if tenant:
            context['has_access'] = validate_tenant_access(request.user, tenant)
    
    return context


def enforce_tenant_isolation(queryset, tenant_id: str):
    """
    Enforce tenant isolation on a queryset.
    
    Args:
        queryset: Django queryset
        tenant_id: Tenant ID to filter by
        
    Returns:
        Filtered queryset
    """
    if hasattr(queryset.model, 'tenant_id'):
        return queryset.filter(tenant_id=tenant_id)
    elif hasattr(queryset.model, 'tenant'):
        return queryset.filter(tenant_id=tenant_id)
    else:
        # If model doesn't have tenant field, return as-is
        # This should be handled by Row Level Security
        return queryset


def get_tenant_limits(tenant: Tenant) -> Dict[str, Any]:
    """
    Get tenant limits and usage information.
    
    Args:
        tenant: Tenant object
        
    Returns:
        Dictionary containing limit information
    """
    return {
        'max_users': tenant.max_users,
        'current_users': tenant.user_count,
        'max_providers': tenant.max_providers,
        'current_providers': tenant.providers.count() if hasattr(tenant, 'providers') else 0,
        'is_at_user_limit': tenant.is_at_user_limit,
        'can_add_user': tenant.can_add_user(),
        'subscription_status': tenant.subscription_status,
        'is_trial_expired': tenant.is_trial_expired()
    }


def check_tenant_limits(tenant: Tenant, resource_type: str) -> bool:
    """
    Check if tenant can add a specific resource type.
    
    Args:
        tenant: Tenant object
        resource_type: Type of resource ('user', 'provider', etc.)
        
    Returns:
        True if limit allows, False otherwise
    """
    if resource_type == 'user':
        return tenant.can_add_user()
    elif resource_type == 'provider':
        current_count = tenant.providers.count() if hasattr(tenant, 'providers') else 0
        return current_count < tenant.max_providers
    else:
        return True


def log_tenant_activity(tenant: Tenant, user: User, activity: str, 
                       details: Dict[str, Any] = None, severity: str = 'low'):
    """
    Log tenant-specific activity.
    
    Args:
        tenant: Tenant object
        user: User object
        activity: Activity description
        details: Additional details
        severity: Severity level
    """
    SecurityAuditLog.log_event(
        event_type='tenant_modified',
        message=f"User {user.email} performed {activity} in tenant {tenant.name}",
        user=user,
        tenant=tenant,
        severity=severity,
        details=details or {},
        is_security_violation=False,
        requires_investigation=False
    )


def get_tenant_security_summary(tenant: Tenant) -> Dict[str, Any]:
    """
    Get comprehensive security summary for a tenant.
    
    Args:
        tenant: Tenant object
        
    Returns:
        Dictionary containing security summary
    """
    # Get recent security events
    recent_events = SecurityAuditLog.objects.filter(
        tenant=tenant,
        timestamp__gte=timezone.now() - timezone.timedelta(days=7)
    ).order_by('-timestamp')[:10]
    
    # Count security violations
    violation_count = SecurityAuditLog.objects.filter(
        tenant=tenant,
        is_security_violation=True,
        timestamp__gte=timezone.now() - timezone.timedelta(days=30)
    ).count()
    
    # Count unresolved issues
    unresolved_count = SecurityAuditLog.objects.filter(
        tenant=tenant,
        requires_investigation=True,
        resolved=False
    ).count()
    
    return {
        'tenant_info': tenant.get_security_summary(),
        'recent_events': [event.get_security_summary() for event in recent_events],
        'violation_count_30d': violation_count,
        'unresolved_issues': unresolved_count,
        'last_security_scan': tenant.last_security_scan,
        'security_notes': tenant.security_notes if hasattr(tenant, 'security_notes') else None
    }


def create_tenant_audit_report(tenant: Tenant, days: int = 30) -> Dict[str, Any]:
    """
    Create a comprehensive audit report for a tenant.
    
    Args:
        tenant: Tenant object
        days: Number of days to include in report
        
    Returns:
        Dictionary containing audit report
    """
    start_date = timezone.now() - timezone.timedelta(days=days)
    
    # Get all events in the period
    events = SecurityAuditLog.objects.filter(
        tenant=tenant,
        timestamp__gte=start_date
    ).order_by('-timestamp')
    
    # Group by event type
    event_counts = {}
    for event in events:
        event_type = event.event_type
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    # Get severity distribution
    severity_counts = {}
    for event in events:
        severity = event.severity
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    # Get top users by activity
    user_activity = {}
    for event in events:
        if event.user:
            user_email = event.user.email
            user_activity[user_email] = user_activity.get(user_email, 0) + 1
    
    return {
        'tenant_name': tenant.name,
        'report_period_days': days,
        'total_events': events.count(),
        'event_type_distribution': event_counts,
        'severity_distribution': severity_counts,
        'top_active_users': sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10],
        'security_violations': events.filter(is_security_violation=True).count(),
        'unresolved_issues': events.filter(requires_investigation=True, resolved=False).count(),
        'recent_events': [event.get_security_summary() for event in events[:20]]
    }
