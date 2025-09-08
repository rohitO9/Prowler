"""
Enhanced Authorization Middleware for Azure AD RBAC
"""

import logging
from typing import List, Optional
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from api.models.azure_rbac import Company, AuditLog, Permission
from api.models.enhanced_role import EnhancedRole
from api.models.azure_rbac import UserRoleAssignment

logger = logging.getLogger(__name__)


class AzureADRBACMiddleware(MiddlewareMixin):
    """
    Middleware for Azure AD RBAC authorization
    Validates user permissions and enforces role-based access control
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming request for authorization"""
        # Skip authorization for certain paths
        if self._should_skip_authorization(request):
            return None
        
        # Extract user and company context from JWT token
        user_context = self._extract_user_context(request)
        if not user_context:
            return None
        
        # Set request attributes for easy access in views
        request.user_context = user_context
        request.company = user_context.get('company')
        request.user_roles = user_context.get('roles', [])
        request.user_permissions = user_context.get('permissions', [])
        
        return None
    
    def process_response(self, request, response):
        """Process response for audit logging"""
        # Log API access for audit purposes
        if hasattr(request, 'user_context') and request.user_context:
            self._log_api_access(request, response)
        
        return response
    
    def _should_skip_authorization(self, request) -> bool:
        """Check if request should skip authorization"""
        skip_paths = [
            '/api/auth/',
            '/api/health/',
            '/api/docs/',
            '/admin/',
            '/static/',
            '/media/',
        ]
        
        path = request.path
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def _extract_user_context(self, request) -> Optional[dict]:
        """Extract user context from JWT token"""
        try:
            # Get JWT token from Authorization header
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if not auth_header.startswith('Bearer '):
                return None
            
            token = auth_header.split(' ')[1]
            
            # Decode JWT token (without verification for now)
            import jwt
            try:
                decoded_token = jwt.decode(token, options={"verify_signature": False})
            except jwt.InvalidTokenError:
                return None
            
            # Extract user information
            user_id = decoded_token.get('sub')
            company_id = decoded_token.get('company_id')
            
            if not user_id or not company_id:
                return None
            
            # Get company
            try:
                company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                return None
            
            # Get user roles and permissions
            roles = decoded_token.get('roles', [])
            permissions = decoded_token.get('permissions', [])
            
            return {
                'user_id': user_id,
                'company': company,
                'roles': roles,
                'permissions': permissions,
                'token': decoded_token
            }
            
        except Exception as e:
            logger.error(f"Error extracting user context: {str(e)}")
            return None
    
    def _log_api_access(self, request, response):
        """Log API access for audit purposes"""
        try:
            user_context = request.user_context
            company = user_context.get('company')
            
            # Determine action type based on HTTP method
            action_type_map = {
                'GET': 'data_access',
                'POST': 'data_modified',
                'PUT': 'data_modified',
                'PATCH': 'data_modified',
                'DELETE': 'data_modified',
            }
            
            action_type = action_type_map.get(request.method, 'data_access')
            
            # Log the access
            AuditLog.log_action(
                user_id=user_context.get('user_id'),
                company=company,
                action_type=action_type,
                action_description=f"{request.method} {request.path}",
                resource_type='api_endpoint',
                resource_id=request.path,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_method=request.method,
                request_path=request.path,
                success=200 <= response.status_code < 400,
                details={
                    'query_params': dict(request.GET),
                    'status_code': response.status_code
                }
            )
            
        except Exception as e:
            logger.error(f"Error logging API access: {str(e)}")


class HasPermission(BasePermission):
    """
    Custom permission class for checking specific permissions
    """
    
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    def has_permission(self, request, view):
        """Check if user has required permissions"""
        if not hasattr(request, 'user_permissions'):
            return False
        
        user_permissions = request.user_permissions
        
        # Check if user has all required permissions
        for permission in self.required_permissions:
            if permission not in user_permissions:
                self._log_permission_denied(request, permission)
                return False
        
        return True
    
    def _log_permission_denied(self, request, permission):
        """Log permission denied event"""
        try:
            if hasattr(request, 'user_context'):
                user_context = request.user_context
                company = user_context.get('company')
                
                AuditLog.log_action(
                    user_id=user_context.get('user_id'),
                    company=company,
                    action_type='permission_denied',
                    action_description=f'Permission denied: {permission}',
                    resource_type='permission',
                    resource_id=permission,
                    ip_address=self._get_client_ip(request),
                    success=False,
                    details={
                        'required_permission': permission,
                        'user_permissions': user_permissions
                    }
                )
        except Exception as e:
            logger.error(f"Error logging permission denied: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class HasRole(BasePermission):
    """
    Custom permission class for checking specific roles
    """
    
    def __init__(self, required_roles: List[str]):
        self.required_roles = required_roles
    
    def has_permission(self, request, view):
        """Check if user has required roles"""
        if not hasattr(request, 'user_roles'):
            return False
        
        user_roles = request.user_roles
        
        # Check if user has any of the required roles
        for role in self.required_roles:
            if role in user_roles:
                return True
        
        self._log_role_denied(request)
        return False
    
    def _log_role_denied(self, request):
        """Log role denied event"""
        try:
            if hasattr(request, 'user_context'):
                user_context = request.user_context
                company = user_context.get('company')
                
                AuditLog.log_action(
                    user_id=user_context.get('user_id'),
                    company=company,
                    action_type='permission_denied',
                    action_description=f'Role denied: {self.required_roles}',
                    resource_type='role',
                    resource_id=str(self.required_roles),
                    ip_address=self._get_client_ip(request),
                    success=False,
                    details={
                        'required_roles': self.required_roles,
                        'user_roles': user_roles
                    }
                )
        except Exception as e:
            logger.error(f"Error logging role denied: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CompanyAccessPermission(BasePermission):
    """
    Permission class for company-level access control
    """
    
    def has_permission(self, request, view):
        """Check if user has access to the company"""
        if not hasattr(request, 'company'):
            return False
        
        # Check if user belongs to the company
        company = request.company
        user_context = getattr(request, 'user_context', {})
        user_id = user_context.get('user_id')
        
        if not user_id:
            return False
        
        # Check if user has active role assignment in this company
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            has_access = UserRoleAssignment.objects.filter(
                user=user,
                company=company,
                is_active=True
            ).exists()
            
            if not has_access:
                self._log_company_access_denied(request, company)
            
            return has_access
            
        except Exception as e:
            logger.error(f"Error checking company access: {str(e)}")
            return False
    
    def _log_company_access_denied(self, request, company):
        """Log company access denied event"""
        try:
            user_context = getattr(request, 'user_context', {})
            
            AuditLog.log_action(
                user_id=user_context.get('user_id'),
                company=company,
                action_type='permission_denied',
                action_description=f'Company access denied: {company.name}',
                resource_type='company',
                resource_id=str(company.id),
                ip_address=self._get_client_ip(request),
                success=False,
                details={
                    'company_id': str(company.id),
                    'company_name': company.name
                }
            )
        except Exception as e:
            logger.error(f"Error logging company access denied: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ResourceAccessPermission(BasePermission):
    """
    Permission class for resource-level access control
    """
    
    def __init__(self, resource_type: str, required_permission: str):
        self.resource_type = resource_type
        self.required_permission = required_permission
    
    def has_permission(self, request, view):
        """Check if user has permission to access the resource"""
        if not hasattr(request, 'user_permissions'):
            return False
        
        user_permissions = request.user_permissions
        
        # Check if user has the required permission
        if self.required_permission not in user_permissions:
            self._log_resource_access_denied(request)
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific object"""
        # This can be extended to check object-level permissions
        # For now, just check general permission
        return self.has_permission(request, view)
    
    def _log_resource_access_denied(self, request):
        """Log resource access denied event"""
        try:
            if hasattr(request, 'user_context'):
                user_context = request.user_context
                company = user_context.get('company')
                
                AuditLog.log_action(
                    user_id=user_context.get('user_id'),
                    company=company,
                    action_type='permission_denied',
                    action_description=f'Resource access denied: {self.resource_type}',
                    resource_type=self.resource_type,
                    resource_id=self.required_permission,
                    ip_address=self._get_client_ip(request),
                    success=False,
                    details={
                        'required_permission': self.required_permission,
                        'resource_type': self.resource_type
                    }
                )
        except Exception as e:
            logger.error(f"Error logging resource access denied: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# Convenience decorators for views
def require_permission(permissions: List[str]):
    """Decorator to require specific permissions"""
    def decorator(view_func):
        view_func.permission_classes = [HasPermission(permissions)]
        return view_func
    return decorator


def require_role(roles: List[str]):
    """Decorator to require specific roles"""
    def decorator(view_func):
        view_func.permission_classes = [HasRole(roles)]
        return view_func
    return decorator


def require_company_access():
    """Decorator to require company access"""
    def decorator(view_func):
        view_func.permission_classes = [CompanyAccessPermission()]
        return view_func
    return decorator


def require_resource_access(resource_type: str, permission: str):
    """Decorator to require resource access"""
    def decorator(view_func):
        view_func.permission_classes = [ResourceAccessPermission(resource_type, permission)]
        return view_func
    return decorator
