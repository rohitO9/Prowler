"""
Audit Log Service - Comprehensive audit logging for security and compliance.

This service provides centralized audit logging for all critical actions including:
- Security events and violations
- User authentication and authorization
- Tenant management actions
- Data access and modifications
- System errors and anomalies
"""

import logging
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ValidationError

from api.models import SecurityAuditLog, User, Tenant

logger = logging.getLogger(__name__)


class AuditLogService:
    """Service for comprehensive audit logging and security monitoring."""
    
    def log_event(self, event_type: str, message: str, user: Optional[User] = None, 
                  tenant: Optional[Tenant] = None, severity: str = 'medium',
                  ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                  request_path: Optional[str] = None, request_method: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None, 
                  is_security_violation: bool = False, 
                  requires_investigation: bool = False) -> SecurityAuditLog:
        """
        Log a security event with comprehensive context.
        
        Args:
            event_type: Type of event from SecurityAuditLog.EVENT_TYPES
            message: Human-readable description
            user: User involved (if applicable)
            tenant: Tenant context (if applicable)
            severity: Severity level ('low', 'medium', 'high', 'critical')
            ip_address: IP address of the request
            user_agent: User agent string
            request_path: Request path
            request_method: HTTP method
            details: Additional structured data
            is_security_violation: Whether this is a security violation
            requires_investigation: Whether manual investigation is needed
            
        Returns:
            SecurityAuditLog: The created audit log entry
        """
        try:
            # Validate event type
            valid_event_types = [choice[0] for choice in SecurityAuditLog.EVENT_TYPES]
            if event_type not in valid_event_types:
                raise ValidationError(f"Invalid event type: {event_type}")
            
            # Validate severity
            valid_severities = [choice[0] for choice in SecurityAuditLog.SEVERITY_LEVELS]
            if severity not in valid_severities:
                raise ValidationError(f"Invalid severity level: {severity}")
            
            # Create audit log entry
            audit_log = SecurityAuditLog.objects.create(
                event_type=event_type,
                message=message,
                user=user,
                tenant=tenant,
                severity=severity,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request_path,
                request_method=request_method,
                details=details or {},
                is_security_violation=is_security_violation,
                requires_investigation=requires_investigation
            )
            
            # Log to application logger
            log_level = self._get_log_level(severity)
            logger.log(log_level, f"Audit: {event_type} - {message}")
            
            return audit_log
            
        except Exception as e:
            logger.error(f"❌ Failed to create audit log: {e}")
            # Try to create a minimal audit log for the failure
            try:
                return SecurityAuditLog.objects.create(
                    event_type='system_error',
                    message=f"Failed to create audit log: {str(e)}",
                    severity='high',
                    details={'original_event_type': event_type, 'error': str(e)}
                )
            except:
                logger.critical("❌ CRITICAL: Failed to create audit log for audit log failure")
                raise
    
    def log_login_attempt(self, user: Optional[User], success: bool, 
                         ip_address: Optional[str] = None, 
                         user_agent: Optional[str] = None,
                         request_path: Optional[str] = None, 
                         tenant: Optional[Tenant] = None,
                         details: Optional[Dict[str, Any]] = None) -> SecurityAuditLog:
        """
        Log a login attempt with appropriate severity and flags.
        
        Args:
            user: User attempting to login (None for failed attempts with unknown user)
            success: Whether the login was successful
            ip_address: IP address of the request
            user_agent: User agent string
            request_path: Request path
            tenant: Tenant context
            details: Additional details about the login attempt
            
        Returns:
            SecurityAuditLog: The created audit log entry
        """
        if success:
            event_type = 'login_success'
            severity = 'low'
            message = f"Successful login for user {user.email if user else 'unknown'}"
            is_violation = False
            requires_investigation = False
        else:
            event_type = 'login_failed'
            severity = 'medium'
            message = f"Failed login attempt for user {user.email if user else 'unknown'}"
            is_violation = True
            requires_investigation = True
        
        return self.log_event(
            event_type=event_type,
            message=message,
            user=user,
            tenant=tenant,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            details=details,
            is_security_violation=is_violation,
            requires_investigation=requires_investigation
        )
    
    def log_tenant_access_denied(self, user: User, tenant: Tenant, 
                                ip_address: Optional[str] = None,
                                user_agent: Optional[str] = None,
                                request_path: Optional[str] = None,
                                details: Optional[Dict[str, Any]] = None) -> SecurityAuditLog:
        """
        Log when a user is denied access to a tenant.
        
        Args:
            user: User who was denied access
            tenant: Tenant that access was denied to
            ip_address: IP address of the request
            user_agent: User agent string
            request_path: Request path
            details: Additional details about the access denial
            
        Returns:
            SecurityAuditLog: The created audit log entry
        """
        return self.log_event(
            event_type='tenant_access_denied',
            message=f"User {user.email} denied access to tenant {tenant.name}",
            user=user,
            tenant=tenant,
            severity='high',
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            details=details,
            is_security_violation=True,
            requires_investigation=True
        )
    
    def log_data_access_violation(self, user: User, tenant: Tenant, 
                                 resource_type: str,
                                 ip_address: Optional[str] = None,
                                 user_agent: Optional[str] = None,
                                 request_path: Optional[str] = None,
                                 details: Optional[Dict[str, Any]] = None) -> SecurityAuditLog:
        """
        Log when a user attempts to access data they shouldn't.
        
        Args:
            user: User who attempted unauthorized access
            tenant: Tenant context
            resource_type: Type of resource that was accessed
            ip_address: IP address of the request
            user_agent: User agent string
            request_path: Request path
            details: Additional details about the violation
            
        Returns:
            SecurityAuditLog: The created audit log entry
        """
        return self.log_event(
            event_type='data_access_violation',
            message=f"User {user.email} attempted unauthorized access to {resource_type} in tenant {tenant.name}",
            user=user,
            tenant=tenant,
            severity='critical',
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            details=details,
            is_security_violation=True,
            requires_investigation=True
        )
    
    def log_oauth_event(self, event_type: str, user: Optional[User], 
                       tenant: Optional[Tenant], provider: str,
                       success: bool, details: Optional[Dict[str, Any]] = None) -> SecurityAuditLog:
        """
        Log OAuth-related events.
        
        Args:
            event_type: Type of OAuth event ('oauth_login', 'oauth_failed')
            user: User involved in the OAuth event
            tenant: Tenant context
            provider: OAuth provider (azure, google, etc.)
            success: Whether the OAuth event was successful
            details: Additional details about the OAuth event
            
        Returns:
            SecurityAuditLog: The created audit log entry
        """
        if success:
            severity = 'low'
            message = f"Successful OAuth login via {provider} for user {user.email if user else 'unknown'}"
            is_violation = False
            requires_investigation = False
        else:
            severity = 'medium'
            message = f"Failed OAuth login via {provider} for user {user.email if user else 'unknown'}"
            is_violation = True
            requires_investigation = True
        
        oauth_details = details or {}
        oauth_details['provider'] = provider
        
        return self.log_event(
            event_type=event_type,
            message=message,
            user=user,
            tenant=tenant,
            severity=severity,
            details=oauth_details,
            is_security_violation=is_violation,
            requires_investigation=requires_investigation
        )
    
    def log_user_management(self, action: str, user: User, target_user: Optional[User] = None,
                           tenant: Optional[Tenant] = None, details: Optional[Dict[str, Any]] = None) -> SecurityAuditLog:
        """
        Log user management actions.
        
        Args:
            action: Type of user management action ('user_created', 'user_deleted', etc.)
            user: User performing the action
            target_user: User being acted upon (if applicable)
            tenant: Tenant context
            details: Additional details about the action
            
        Returns:
            SecurityAuditLog: The created audit log entry
        """
        message = f"User {user.email} performed {action}"
        if target_user:
            message += f" on user {target_user.email}"
        
        return self.log_event(
            event_type=action,
            message=message,
            user=user,
            tenant=tenant,
            severity='medium',
            details=details,
            is_security_violation=False,
            requires_investigation=False
        )
    
    def log_tenant_management(self, action: str, user: User, tenant: Tenant,
                              details: Optional[Dict[str, Any]] = None) -> SecurityAuditLog:
        """
        Log tenant management actions.
        
        Args:
            action: Type of tenant management action
            user: User performing the action
            tenant: Tenant being acted upon
            details: Additional details about the action
            
        Returns:
            SecurityAuditLog: The created audit log entry
        """
        message = f"User {user.email} performed {action} on tenant {tenant.name}"
        
        return self.log_event(
            event_type=action,
            message=message,
            user=user,
            tenant=tenant,
            severity='medium',
            details=details,
            is_security_violation=False,
            requires_investigation=False
        )
    
    def get_security_events(self, tenant: Optional[Tenant] = None, 
                           user: Optional[User] = None,
                           event_types: Optional[List[str]] = None,
                           severity_levels: Optional[List[str]] = None,
                           is_violation: Optional[bool] = None,
                           requires_investigation: Optional[bool] = None,
                           start_date: Optional[timezone.datetime] = None,
                           end_date: Optional[timezone.datetime] = None,
                           limit: int = 100) -> List[SecurityAuditLog]:
        """
        Retrieve security events with filtering options.
        
        Args:
            tenant: Filter by tenant
            user: Filter by user
            event_types: Filter by event types
            severity_levels: Filter by severity levels
            is_violation: Filter by security violation flag
            requires_investigation: Filter by investigation requirement
            start_date: Filter events after this date
            end_date: Filter events before this date
            limit: Maximum number of events to return
            
        Returns:
            List of SecurityAuditLog entries
        """
        try:
            queryset = SecurityAuditLog.objects.all()
            
            # Apply filters
            if tenant:
                queryset = queryset.filter(tenant=tenant)
            
            if user:
                queryset = queryset.filter(user=user)
            
            if event_types:
                queryset = queryset.filter(event_type__in=event_types)
            
            if severity_levels:
                queryset = queryset.filter(severity__in=severity_levels)
            
            if is_violation is not None:
                queryset = queryset.filter(is_security_violation=is_violation)
            
            if requires_investigation is not None:
                queryset = queryset.filter(requires_investigation=requires_investigation)
            
            if start_date:
                queryset = queryset.filter(timestamp__gte=start_date)
            
            if end_date:
                queryset = queryset.filter(timestamp__lte=end_date)
            
            # Order by timestamp (newest first) and limit
            return list(queryset.order_by('-timestamp')[:limit])
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve security events: {e}")
            raise
    
    def get_security_summary(self, tenant: Optional[Tenant] = None,
                           days: int = 30) -> Dict[str, Any]:
        """
        Get a summary of security events for the specified period.
        
        Args:
            tenant: Filter by tenant (None for all tenants)
            days: Number of days to look back
            
        Returns:
            Dict containing security summary statistics
        """
        try:
            start_date = timezone.now() - timezone.timedelta(days=days)
            
            queryset = SecurityAuditLog.objects.filter(timestamp__gte=start_date)
            if tenant:
                queryset = queryset.filter(tenant=tenant)
            
            # Count events by type
            event_counts = {}
            for event_type, _ in SecurityAuditLog.EVENT_TYPES:
                count = queryset.filter(event_type=event_type).count()
                if count > 0:
                    event_counts[event_type] = count
            
            # Count by severity
            severity_counts = {}
            for severity, _ in SecurityAuditLog.SEVERITY_LEVELS:
                count = queryset.filter(severity=severity).count()
                if count > 0:
                    severity_counts[severity] = count
            
            # Count violations and investigations
            violations = queryset.filter(is_security_violation=True).count()
            investigations = queryset.filter(requires_investigation=True).count()
            unresolved = queryset.filter(requires_investigation=True, resolved=False).count()
            
            return {
                'period_days': days,
                'total_events': queryset.count(),
                'event_counts': event_counts,
                'severity_counts': severity_counts,
                'security_violations': violations,
                'requires_investigation': investigations,
                'unresolved_investigations': unresolved,
                'tenant': tenant.name if tenant else 'All Tenants'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get security summary: {e}")
            raise
    
    def resolve_investigation(self, audit_log: SecurityAuditLog, resolved_by: User,
                            resolution_notes: Optional[str] = None) -> SecurityAuditLog:
        """
        Mark an audit log as resolved.
        
        Args:
            audit_log: The audit log to resolve
            resolved_by: User who resolved the investigation
            resolution_notes: Notes about the resolution
            
        Returns:
            SecurityAuditLog: The updated audit log entry
        """
        try:
            audit_log.resolve(resolved_by, resolution_notes)
            
            # Log the resolution
            self.log_event(
                event_type='admin_action',
                message=f"Investigation resolved for event: {audit_log.message[:50]}",
                user=resolved_by,
                tenant=audit_log.tenant,
                severity='low',
                details={
                    'resolved_audit_log_id': str(audit_log.id),
                    'original_event_type': audit_log.event_type,
                    'resolution_notes': resolution_notes
                }
            )
            
            logger.info(f"✅ Investigation resolved: {audit_log.id}")
            return audit_log
            
        except Exception as e:
            logger.error(f"❌ Failed to resolve investigation: {e}")
            raise
    
    def _get_log_level(self, severity: str) -> int:
        """Convert severity level to Python logging level."""
        severity_map = {
            'low': logging.INFO,
            'medium': logging.WARNING,
            'high': logging.ERROR,
            'critical': logging.CRITICAL
        }
        return severity_map.get(severity, logging.WARNING)
