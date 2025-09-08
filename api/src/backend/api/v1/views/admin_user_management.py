"""
Admin User Management Views for Azure AD RBAC
"""

import logging
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from api.models.azure_rbac import Company, AuditLog, Permission
from api.models.enhanced_role import EnhancedRole
from api.models.azure_rbac import UserRoleAssignment
from api.middleware.azure_rbac import HasPermission, HasRole
from api.v1.serializers import UserSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class AdminUserManagementViewSet(ModelViewSet):
    """
    Admin interface for user management with permission controls
    """
    permission_classes = [IsAuthenticated, HasPermission(['users.manage'])]
    serializer_class = UserSerializer
    
    def get_queryset(self):
        """Get all users in the admin's company"""
        company = self.request.company
        return User.objects.filter(
            role_assignments__company=company,
            role_assignments__is_active=True
        ).distinct().select_related('azure_profile')
    
    def list(self, request):
        """List all users with their roles and permissions"""
        try:
            company = request.company
            users = self.get_queryset()
            
            users_data = []
            for user in users:
                # Get user's roles in this company
                role_assignments = UserRoleAssignment.objects.filter(
                    user=user,
                    company=company,
                    is_active=True
                ).select_related('role')
                
                # Get user's permissions
                permissions = []
                for assignment in role_assignments:
                    role_permissions = assignment.role.get_permissions()
                    permissions.extend([p.name for p in role_permissions])
                
                # Remove duplicates
                permissions = list(set(permissions))
                
                # Get Azure AD profile if exists
                azure_profile = None
                try:
                    profile = user.azure_profile.get(company=company)
                    azure_profile = {
                        'azure_ad_id': profile.azure_ad_id,
                        'job_title': profile.job_title,
                        'department': profile.department,
                        'office_location': profile.office_location,
                        'last_synced_at': profile.last_synced_at.isoformat() if profile.last_synced_at else None,
                        'sync_status': profile.sync_status
                    }
                except:
                    pass
                
                users_data.append({
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined.isoformat(),
                    'roles': [
                        {
                            'id': str(assignment.role.id),
                            'name': assignment.role.name,
                            'display_name': assignment.role.display_name,
                            'role_type': assignment.role.role_type,
                            'assignment_source': assignment.assignment_source,
                            'assigned_at': assignment.assigned_at.isoformat(),
                            'expires_at': assignment.expires_at.isoformat() if assignment.expires_at else None,
                            'is_expired': assignment.is_expired
                        }
                        for assignment in role_assignments
                    ],
                    'permissions': permissions,
                    'azure_profile': azure_profile,
                    'trial_info': {
                        'trial_start': user.trial_start.isoformat() if user.trial_start else None,
                        'trial_end': user.trial_end.isoformat() if user.trial_end else None,
                        'is_trial_active': user.is_trial_active
                    }
                })
            
            return Response({
                'users': users_data,
                'total_count': len(users_data)
            })
            
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return Response(
                {'error': f'Failed to list users: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def assign_role(self, request, pk=None):
        """Assign a role to a user"""
        try:
            company = request.company
            user = self.get_object()
            
            role_id = request.data.get('role_id')
            assignment_source = request.data.get('assignment_source', 'direct')
            expires_at = request.data.get('expires_at')
            
            if not role_id:
                return Response(
                    {'error': 'role_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get role
            try:
                role = EnhancedRole.objects.get(id=role_id, tenant_id=company.id)
            except EnhancedRole.DoesNotExist:
                return Response(
                    {'error': 'Role not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if assignment already exists
            existing_assignment = UserRoleAssignment.objects.filter(
                user=user,
                role=role,
                company=company
            ).first()
            
            if existing_assignment:
                if existing_assignment.is_active:
                    return Response(
                        {'error': 'User already has this role'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    # Reactivate existing assignment
                    existing_assignment.is_active = True
                    existing_assignment.assigned_by = request.user
                    existing_assignment.save()
                    assignment = existing_assignment
            else:
                # Create new assignment
                assignment = UserRoleAssignment.objects.create(
                    user=user,
                    role=role,
                    company=company,
                    assignment_source=assignment_source,
                    assigned_by=request.user,
                    expires_at=expires_at,
                    is_active=True
                )
            
            # Log role assignment
            AuditLog.log_action(
                user=request.user,
                company=company,
                action_type='role_assigned',
                action_description=f'Admin assigned role {role.display_name} to {user.email}',
                resource_type='user_role_assignment',
                resource_id=str(assignment.id),
                success=True,
                details={
                    'user_email': user.email,
                    'role_name': role.name,
                    'assignment_source': assignment_source
                }
            )
            
            return Response({
                'message': f'Role {role.display_name} assigned to {user.email}',
                'assignment_id': str(assignment.id),
                'assigned_at': assignment.assigned_at.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}")
            return Response(
                {'error': f'Failed to assign role: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def remove_role(self, request, pk=None):
        """Remove a role from a user"""
        try:
            company = request.company
            user = self.get_object()
            
            role_id = request.data.get('role_id')
            
            if not role_id:
                return Response(
                    {'error': 'role_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get assignment
            try:
                assignment = UserRoleAssignment.objects.get(
                    user=user,
                    role_id=role_id,
                    company=company,
                    is_active=True
                )
            except UserRoleAssignment.DoesNotExist:
                return Response(
                    {'error': 'Role assignment not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Deactivate assignment
            assignment.is_active = False
            assignment.save()
            
            # Log role removal
            AuditLog.log_action(
                user=request.user,
                company=company,
                action_type='role_removed',
                action_description=f'Admin removed role {assignment.role.display_name} from {user.email}',
                resource_type='user_role_assignment',
                resource_id=str(assignment.id),
                success=True,
                details={
                    'user_email': user.email,
                    'role_name': assignment.role.name,
                    'assignment_source': assignment.assignment_source
                }
            )
            
            return Response({
                'message': f'Role {assignment.role.display_name} removed from {user.email}',
                'removed_at': assignment.updated_at.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error removing role: {str(e)}")
            return Response(
                {'error': f'Failed to remove role: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """Get user's current permissions"""
        try:
            company = request.company
            user = self.get_object()
            
            # Get user's roles
            role_assignments = UserRoleAssignment.objects.filter(
                user=user,
                company=company,
                is_active=True
            ).select_related('role')
            
            # Get all permissions
            all_permissions = Permission.objects.all().order_by('category', 'name')
            
            # Get user's current permissions
            user_permissions = set()
            user_roles = []
            
            for assignment in role_assignments:
                role_permissions = assignment.role.get_permissions()
                user_permissions.update([p.name for p in role_permissions])
                user_roles.append({
                    'id': str(assignment.role.id),
                    'name': assignment.role.name,
                    'display_name': assignment.role.display_name,
                    'permissions': [p.name for p in role_permissions]
                })
            
            # Organize permissions by category
            permissions_by_category = {}
            for perm in all_permissions:
                if perm.category not in permissions_by_category:
                    permissions_by_category[perm.category] = []
                
                permissions_by_category[perm.category].append({
                    'name': perm.name,
                    'display_name': perm.display_name,
                    'description': perm.description,
                    'action': perm.action,
                    'resource_type': perm.resource_type,
                    'has_permission': perm.name in user_permissions
                })
            
            return Response({
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name
                },
                'roles': user_roles,
                'permissions_by_category': permissions_by_category,
                'total_permissions': len(user_permissions)
            })
            
        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return Response(
                {'error': f'Failed to get user permissions: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def update_permissions(self, request, pk=None):
        """Update user's permissions by modifying their roles"""
        try:
            company = request.company
            user = self.get_object()
            
            # Get requested permissions
            requested_permissions = request.data.get('permissions', [])
            
            if not requested_permissions:
                return Response(
                    {'error': 'permissions list is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Find roles that have the requested permissions
            suitable_roles = []
            for role in EnhancedRole.objects.filter(tenant_id=company.id, is_active=True):
                role_permissions = role.get_permissions()
                role_permission_names = [p.name for p in role_permissions]
                
                # Check if role has all requested permissions
                if all(perm in role_permission_names for perm in requested_permissions):
                    suitable_roles.append(role)
            
            if not suitable_roles:
                return Response(
                    {'error': 'No existing roles have all the requested permissions. Create a custom role first.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Use the role with the highest priority
            best_role = max(suitable_roles, key=lambda r: r.priority)
            
            # Remove existing role assignments
            UserRoleAssignment.objects.filter(
                user=user,
                company=company,
                is_active=True
            ).update(is_active=False)
            
            # Assign new role
            assignment = UserRoleAssignment.objects.create(
                user=user,
                role=best_role,
                company=company,
                assignment_source='admin_override',
                assigned_by=request.user,
                is_active=True
            )
            
            # Log permission update
            AuditLog.log_action(
                user=request.user,
                company=company,
                action_type='permission_granted',
                action_description=f'Admin updated permissions for {user.email}',
                resource_type='user_permissions',
                resource_id=str(user.id),
                success=True,
                details={
                    'user_email': user.email,
                    'assigned_role': best_role.name,
                    'requested_permissions': requested_permissions,
                    'granted_permissions': [p.name for p in best_role.get_permissions()]
                }
            )
            
            return Response({
                'message': f'Permissions updated for {user.email}',
                'assigned_role': {
                    'id': str(best_role.id),
                    'name': best_role.name,
                    'display_name': best_role.display_name
                },
                'permissions': [p.name for p in best_role.get_permissions()]
            })
            
        except Exception as e:
            logger.error(f"Error updating user permissions: {str(e)}")
            return Response(
                {'error': f'Failed to update permissions: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle user active status"""
        try:
            company = request.company
            user = self.get_object()
            
            # Don't allow deactivating the current user
            if user == request.user:
                return Response(
                    {'error': 'Cannot deactivate your own account'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Toggle active status
            user.is_active = not user.is_active
            user.save()
            
            # Log status change
            AuditLog.log_action(
                user=request.user,
                company=company,
                action_type='data_modified',
                action_description=f'Admin {"activated" if user.is_active else "deactivated"} user {user.email}',
                resource_type='user',
                resource_id=str(user.id),
                success=True,
                details={
                    'user_email': user.email,
                    'new_status': 'active' if user.is_active else 'inactive'
                }
            )
            
            return Response({
                'message': f'User {user.email} {"activated" if user.is_active else "deactivated"}',
                'is_active': user.is_active
            })
            
        except Exception as e:
            logger.error(f"Error toggling user status: {str(e)}")
            return Response(
                {'error': f'Failed to toggle user status: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminRoleManagementViewSet(ModelViewSet):
    """
    Admin interface for role management
    """
    permission_classes = [IsAuthenticated, HasPermission(['roles.manage'])]
    
    def get_queryset(self):
        """Get all roles for the admin's company"""
        company = self.request.company
        return EnhancedRole.objects.filter(
            tenant_id=company.id,
            is_active=True
        ).order_by('-priority', 'name')
    
    def list(self, request):
        """List all roles with their permissions"""
        try:
            company = request.company
            roles = self.get_queryset()
            
            roles_data = []
            for role in roles:
                permissions = role.get_permissions()
                users_count = role.get_users_count()
                
                roles_data.append({
                    'id': str(role.id),
                    'name': role.name,
                    'display_name': role.display_name,
                    'description': role.description,
                    'role_type': role.role_type,
                    'priority': role.priority,
                    'is_system_role': role.is_system_role,
                    'is_default': role.is_default,
                    'azure_group_id': role.azure_group_id,
                    'azure_group_name': role.azure_group_name,
                    'auto_sync_from_azure': role.auto_sync_from_azure,
                    'permission_state': role.permission_state,
                    'permissions': [
                        {
                            'name': p.name,
                            'display_name': p.display_name,
                            'category': p.category,
                            'action': p.action
                        }
                        for p in permissions
                    ],
                    'users_count': users_count,
                    'created_at': role.created_at.isoformat(),
                    'updated_at': role.updated_at.isoformat()
                })
            
            return Response({
                'roles': roles_data,
                'total_count': len(roles_data)
            })
            
        except Exception as e:
            logger.error(f"Error listing roles: {str(e)}")
            return Response(
                {'error': f'Failed to list roles: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request):
        """Create a new custom role"""
        try:
            company = request.company
            data = request.data
            
            # Validate required fields
            if not data.get('name') or not data.get('display_name'):
                return Response(
                    {'error': 'name and display_name are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if role already exists
            if EnhancedRole.objects.filter(
                tenant_id=company.id,
                name=data['name']
            ).exists():
                return Response(
                    {'error': 'Role with this name already exists'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create role
            role = EnhancedRole.objects.create(
                tenant_id=company.id,
                name=data['name'],
                display_name=data['display_name'],
                description=data.get('description', ''),
                role_type=data.get('role_type', 'custom'),
                manage_users=data.get('manage_users', False),
                manage_account=data.get('manage_account', False),
                manage_billing=data.get('manage_billing', False),
                manage_providers=data.get('manage_providers', False),
                manage_integrations=data.get('manage_integrations', False),
                manage_scans=data.get('manage_scans', False),
                unlimited_visibility=data.get('unlimited_visibility', False),
                priority=data.get('priority', 0),
                is_default=data.get('is_default', False),
                created_by=request.user
            )
            
            # Add specific permissions if provided
            permission_names = data.get('permissions', [])
            for perm_name in permission_names:
                role.add_permission(perm_name)
            
            # Log role creation
            AuditLog.log_action(
                user=request.user,
                company=company,
                action_type='role_assigned',
                action_description=f'Admin created role {role.display_name}',
                resource_type='role',
                resource_id=str(role.id),
                success=True,
                details={
                    'role_name': role.name,
                    'permissions': permission_names
                }
            )
            
            return Response({
                'id': str(role.id),
                'name': role.name,
                'display_name': role.display_name,
                'description': role.description,
                'role_type': role.role_type,
                'priority': role.priority,
                'permissions': permission_names,
                'status': 'created'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating role: {str(e)}")
            return Response(
                {'error': f'Failed to create role: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def add_permission(self, request, pk=None):
        """Add a permission to a role"""
        try:
            company = request.company
            role = self.get_object()
            
            permission_name = request.data.get('permission_name')
            if not permission_name:
                return Response(
                    {'error': 'permission_name is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add permission to role
            role_permission = role.add_permission(permission_name)
            
            if role_permission:
                # Log permission addition
                AuditLog.log_action(
                    user=request.user,
                    company=company,
                    action_type='permission_granted',
                    action_description=f'Admin added permission {permission_name} to role {role.display_name}',
                    resource_type='role_permission',
                    resource_id=str(role_permission.id),
                    success=True,
                    details={
                        'role_name': role.name,
                        'permission_name': permission_name
                    }
                )
                
                return Response({
                    'message': f'Permission {permission_name} added to role {role.display_name}',
                    'permission': permission_name
                })
            else:
                return Response(
                    {'error': 'Permission not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
        except Exception as e:
            logger.error(f"Error adding permission to role: {str(e)}")
            return Response(
                {'error': f'Failed to add permission: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def remove_permission(self, request, pk=None):
        """Remove a permission from a role"""
        try:
            company = request.company
            role = self.get_object()
            
            permission_name = request.data.get('permission_name')
            if not permission_name:
                return Response(
                    {'error': 'permission_name is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Remove permission from role
            success = role.remove_permission(permission_name)
            
            if success:
                # Log permission removal
                AuditLog.log_action(
                    user=request.user,
                    company=company,
                    action_type='permission_denied',
                    action_description=f'Admin removed permission {permission_name} from role {role.display_name}',
                    resource_type='role_permission',
                    resource_id=str(role.id),
                    success=True,
                    details={
                        'role_name': role.name,
                        'permission_name': permission_name
                    }
                )
                
                return Response({
                    'message': f'Permission {permission_name} removed from role {role.display_name}',
                    'permission': permission_name
                })
            else:
                return Response(
                    {'error': 'Permission not found or not assigned to role'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
        except Exception as e:
            logger.error(f"Error removing permission from role: {str(e)}")
            return Response(
                {'error': f'Failed to remove permission: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
