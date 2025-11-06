"""
Error Handling and SCIM Compliance Utilities
"""

import logging
import traceback
from typing import Dict, Any, Optional
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class SCIMErrorHandler:
    """
    Handles SCIM-compliant error responses
    """
    
    @staticmethod
    def create_scim_error(status_code: int, detail: str, 
                         scim_type: str = None) -> Response:
        """
        Create SCIM-compliant error response
        
        Args:
            status_code: HTTP status code
            detail: Error detail message
            scim_type: SCIM error type (optional)
            
        Returns:
            Response: SCIM-compliant error response
        """
        error_data = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": str(status_code),
            "detail": detail
        }
        
        if scim_type:
            error_data["scimType"] = scim_type
        
        return Response(error_data, status=status_code)
    
    @staticmethod
    def handle_validation_error(error: ValidationError) -> Response:
        """Handle Django validation errors"""
        detail = str(error)
        if hasattr(error, 'message_dict'):
            detail = "; ".join([f"{k}: {v}" for k, v in error.message_dict.items()])
        
        return SCIMErrorHandler.create_scim_error(
            status_code=400,
            detail=f"Validation error: {detail}",
            scim_type="invalidValue"
        )
    
    @staticmethod
    def handle_not_found(resource_type: str, resource_id: str) -> Response:
        """Handle resource not found errors"""
        return SCIMErrorHandler.create_scim_error(
            status_code=404,
            detail=f"{resource_type} with id '{resource_id}' not found",
            scim_type="invalidValue"
        )
    
    @staticmethod
    def handle_conflict(detail: str) -> Response:
        """Handle conflict errors"""
        return SCIMErrorHandler.create_scim_error(
            status_code=409,
            detail=detail,
            scim_type="uniqueness"
        )
    
    @staticmethod
    def handle_internal_error(error: Exception) -> Response:
        """Handle internal server errors"""
        # Log the full error for debugging
        logger.error(f"Internal server error: {error}")
        logger.error(traceback.format_exc())
        
        # Return generic error to client
        return SCIMErrorHandler.create_scim_error(
            status_code=500,
            detail="Internal server error"
        )


class SecurityErrorHandler:
    """
    Handles security-related errors without exposing internal details
    """
    
    @staticmethod
    def handle_authentication_error(error: Exception) -> JsonResponse:
        """Handle authentication errors"""
        logger.warning(f"Authentication error: {error}")
        
        return JsonResponse({
            'error': 'Authentication failed',
            'message': 'Invalid credentials or token'
        }, status=401)
    
    @staticmethod
    def handle_authorization_error(error: Exception) -> JsonResponse:
        """Handle authorization errors"""
        logger.warning(f"Authorization error: {error}")
        
        return JsonResponse({
            'error': 'Access denied',
            'message': 'You do not have permission to perform this action'
        }, status=403)
    
    @staticmethod
    def handle_tenant_isolation_error(error: Exception) -> JsonResponse:
        """Handle tenant isolation errors"""
        logger.warning(f"Tenant isolation error: {error}")
        
        return JsonResponse({
            'error': 'Tenant access denied',
            'message': 'You do not have access to this tenant'
        }, status=403)
    
    @staticmethod
    def handle_rate_limit_error(error: Exception) -> JsonResponse:
        """Handle rate limit errors"""
        logger.warning(f"Rate limit exceeded: {error}")
        
        return JsonResponse({
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.'
        }, status=429)
    
    @staticmethod
    def handle_validation_error(error: ValidationError) -> JsonResponse:
        """Handle validation errors"""
        logger.info(f"Validation error: {error}")
        
        detail = str(error)
        if hasattr(error, 'message_dict'):
            detail = "; ".join([f"{k}: {v}" for k, v in error.message_dict.items()])
        
        return JsonResponse({
            'error': 'Validation error',
            'message': detail
        }, status=400)


class AzureADErrorHandler:
    """
    Handles Azure AD specific errors
    """
    
    @staticmethod
    def handle_azure_connection_error(error: Exception) -> JsonResponse:
        """Handle Azure AD connection errors"""
        logger.error(f"Azure AD connection error: {error}")
        
        return JsonResponse({
            'error': 'Azure AD connection failed',
            'message': 'Unable to connect to Azure AD. Please check your configuration.'
        }, status=400)
    
    @staticmethod
    def handle_azure_credentials_error(error: Exception) -> JsonResponse:
        """Handle Azure AD credentials errors"""
        logger.warning(f"Azure AD credentials error: {error}")
        
        return JsonResponse({
            'error': 'Invalid Azure AD credentials',
            'message': 'The provided Azure AD credentials are invalid.'
        }, status=400)
    
    @staticmethod
    def handle_azure_user_not_found(error: Exception) -> JsonResponse:
        """Handle Azure AD user not found errors"""
        logger.info(f"Azure AD user not found: {error}")
        
        return JsonResponse({
            'error': 'User not found',
            'message': 'The specified user was not found in Azure AD.'
        }, status=404)
    
    @staticmethod
    def handle_azure_sync_error(error: Exception) -> JsonResponse:
        """Handle Azure AD sync errors"""
        logger.error(f"Azure AD sync error: {error}")
        
        return JsonResponse({
            'error': 'Sync failed',
            'message': 'Failed to sync with Azure AD. Please try again.'
        }, status=500)


def safe_api_call(func):
    """
    Decorator to safely handle API calls with proper error handling
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            return SecurityErrorHandler.handle_validation_error(e)
        except PermissionError as e:
            return SecurityErrorHandler.handle_authorization_error(e)
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            
            return JsonResponse({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred. Please try again.'
            }, status=500)
    
    return wrapper


def safe_scim_call(func):
    """
    Decorator to safely handle SCIM API calls with SCIM-compliant error handling
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with SCIM error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            return SCIMErrorHandler.handle_validation_error(e)
        except Exception as e:
            logger.error(f"SCIM error in {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            
            return SCIMErrorHandler.handle_internal_error(e)
    
    return wrapper


class ErrorContext:
    """
    Context manager for error handling with automatic logging
    """
    
    def __init__(self, operation: str, tenant=None, user=None):
        self.operation = operation
        self.tenant = tenant
        self.user = user
        self.start_time = None
    
    def __enter__(self):
        self.start_time = timezone.now()
        logger.info(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = timezone.now() - self.start_time
        
        if exc_type is None:
            logger.info(f"Completed {self.operation} in {duration.total_seconds():.2f}s")
        else:
            logger.error(f"Failed {self.operation} after {duration.total_seconds():.2f}s: {exc_val}")
            
            # Log full traceback for debugging
            logger.error(traceback.format_exception(exc_type, exc_val, exc_tb))
            
            # Log to audit system if available
            try:
                from api.services.audit_log_service import AuditLogService
                audit_service = AuditLogService()
                
                audit_service.log_event(
                    event_type='system_error',
                    message=f"Operation {self.operation} failed: {str(exc_val)}",
                    user=self.user,
                    tenant=self.tenant,
                    severity='high',
                    details={
                        'operation': self.operation,
                        'error_type': exc_type.__name__,
                        'error_message': str(exc_val),
                        'duration_seconds': duration.total_seconds()
                    },
                    is_security_violation=False,
                    requires_investigation=True
                )
            except Exception:
                pass  # Don't fail if audit logging fails
        
        return False  # Don't suppress the exception
