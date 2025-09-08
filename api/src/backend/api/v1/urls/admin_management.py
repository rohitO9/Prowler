"""
URL Configuration for Admin User Management Interface
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.v1.views.admin_user_management import (
    AdminUserManagementViewSet,
    AdminRoleManagementViewSet
)

# Create router for admin API endpoints
router = DefaultRouter()
router.register(r'users', AdminUserManagementViewSet, basename='admin-users')
router.register(r'roles', AdminRoleManagementViewSet, basename='admin-roles')

# Admin management URLs
admin_patterns = [
    path('', include(router.urls)),
]

# Include in main URL patterns
urlpatterns = [
    path('api/v1/admin/', include(admin_patterns)),
]
