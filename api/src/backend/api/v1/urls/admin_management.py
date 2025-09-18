"""
URL Configuration for Admin User Management Interface
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.v1.views.admin_user_management import (
    AdminUserManagementViewSet,
    AdminRoleManagementViewSet
)

# Create router for admin API endpoints (match main router style)
router = DefaultRouter(trailing_slash=False)
router.register(r'users', AdminUserManagementViewSet, basename='admin-users')
router.register(r'roles', AdminRoleManagementViewSet, basename='admin-roles')

# Admin management URLs
admin_patterns = [
    path('', include(router.urls)),
]

# Expose admin endpoints under 'admin/' prefix. The project urlconf should include this
# module under the 'api/v1/' prefix to avoid double prefixing.
urlpatterns = [
    path('admin/', include(admin_patterns)),
]
