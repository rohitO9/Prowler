"""
URL Configuration for Azure AD RBAC System
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.v1.views.azure_rbac import (
    CompanyRegistrationView,
    AzureADLoginView,
    AzureADConfigView,
    RoleManagementView,
    UserRoleAssignmentView,
    AzureADGroupSyncView,
    AuditLogView
)

# Create router for API endpoints
router = DefaultRouter()

# Azure AD RBAC URLs
azure_rbac_patterns = [
    # Company Management
    path('companies/register/', CompanyRegistrationView.as_view(), name='company-register'),
    
    # Authentication
    path('auth/azure/login/', AzureADLoginView.as_view(), name='azure-login'),
    path('auth/azure/config/', AzureADConfigView.as_view(), name='azure-config'),
    
    # Role Management
    path('roles/', RoleManagementView.as_view(), name='role-management'),
    path('user-roles/', UserRoleAssignmentView.as_view(), name='user-role-assignment'),
    
    # Azure AD Integration
    path('azure/groups/sync/', AzureADGroupSyncView.as_view(), name='azure-group-sync'),
    
    # Audit
    path('audit/logs/', AuditLogView.as_view(), name='audit-logs'),
]

# Include in main URL patterns
urlpatterns = [
    path('api/v1/azure-rbac/', include(azure_rbac_patterns)),
]
