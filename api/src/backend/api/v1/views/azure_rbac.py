"""
Enhanced Azure AD Views for Multi-Tenant RBAC
"""

import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser

from api.models.azure_rbac import Company, AuditLog, AzureADGroupMapping
from api.models.enhanced_role import EnhancedRole
from api.services.azure_ad_auth import AzureADAuthService, AzureADRBACManager
from api.middleware.azure_rbac import HasPermission, HasRole, CompanyAccessPermission
from api.v1.serializers import UserSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class CompanyRegistrationView(APIView):
    """
    API endpoint for company registration with Azure AD configuration
    """
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    
    def post(self, request):
        """Register a new company with Azure AD configuration"""
        try:
            data = request.data
            
            # Validate required fields
            required_fields = [
                'name', 'domain', 'azure_tenant_id', 
                'azure_client_id', 'azure_client_secret', 'azure_redirect_uri'
            ]
            
            for field in required_fields:
                if not data.get(field):
                    return Response(
                        {'error': f'{field} is required'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Check if company already exists
            if Company.objects.filter(domain=data['domain']).exists():
                return Response(
                    {'error': 'Company with this domain already exists'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if Company.objects.filter(azure_tenant_id=data['azure_tenant_id']).exists():
                return Response(
                    {'error': 'Company with this Azure tenant ID already exists'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create company
            company = AzureADRBACManager.create_company_with_azure_config(
                name=data['name'],
                domain=data['domain'],
                azure_tenant_id=data['azure_tenant_id'],
                azure_client_id=data['azure_client_id'],
                azure_client_secret=data['azure_client_secret'],
                azure_redirect_uri=data['azure_redirect_uri'],
                created_by=request.user if request.user.is_authenticated else None
            )
            
            return Response({
                'company_id': str(company.id),
                'name': company.name,
                'domain': company.domain,
                'azure_tenant_id': company.azure_tenant_id,
                'status': 'created',
                'message': 'Company registered successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Company registration failed: {str(e)}")
            return Response(
                {'error': f'Registration failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AzureADLoginView(APIView):
    """
    Enhanced Azure AD login endpoint for multi-tenant authentication
    """
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    
    def post(self, request):
        """Authenticate user via Azure AD"""
        try:
            data = request.data
            
            # Get company identifier (domain or tenant_id)
            company_identifier = data.get('company')
            if not company_identifier:
                return Response(
                    {'error': 'Company identifier is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Find company
            company = None
            if '@' in company_identifier:
                # Assume it's an email domain
                domain = company_identifier.split('@')[1]
                company = Company.objects.filter(domain=domain).first()
            else:
                # Assume it's a tenant ID
                company = Company.objects.filter(azure_tenant_id=company_identifier).first()
            
            if not company:
                return Response(
                    {'error': 'Company not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if not company.is_active:
                return Response(
                    {'error': 'Company is not active'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get authorization code
            auth_code = data.get('code')
            if not auth_code:
                return Response(
                    {'error': 'Authorization code is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Authenticate user
            auth_service = AzureADAuthService(company)
            success, auth_result = auth_service.authenticate_user(auth_code)
            
            if not success:
                return Response(
                    {'error': auth_result.get('error', 'Authentication failed')}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            user = auth_result['user']
            serialized_user = UserSerializer(user).data
            
            return Response({
                'access_token': auth_result['access_token'],
                'refresh_token': auth_result['refresh_token'],
                'user': serialized_user,
                'company': {
                    'id': str(company.id),
                    'name': company.name,
                    'domain': company.domain
                },
                'azure_user_info': {
                    'email': auth_result['azure_user_info'].get('mail') or auth_result['azure_user_info'].get('userPrincipalName'),
                    'name': auth_result['azure_user_info'].get('displayName'),
                    'azure_id': auth_result['azure_user_info'].get('id')
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Azure AD login failed: {str(e)}")
            return Response(
                {'error': f'Login failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AzureADConfigView(APIView):
    """
    Get Azure AD configuration for frontend
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return Azure AD configuration"""
        try:
            company_identifier = request.GET.get('company')
            if not company_identifier:
                return Response(
                    {'error': 'Company identifier is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Find company
            company = None
            if '@' in company_identifier:
                domain = company_identifier.split('@')[1]
                company = Company.objects.filter(domain=domain).first()
            else:
                company = Company.objects.filter(azure_tenant_id=company_identifier).first()
            
            if not company:
                return Response(
                    {'error': 'Company not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            config = {
                'client_id': company.azure_client_id,
                'tenant_id': company.azure_tenant_id,
                'redirect_uri': company.azure_redirect_uri,
                'authority': f"https://login.microsoftonline.com/{company.azure_tenant_id}",
                'scopes': company.azure_scopes or ['openid', 'profile', 'email', 'User.Read'],
                'company_name': company.name,
                'company_domain': company.domain
            }
            
            return Response(config)
            
        except Exception as e:
            logger.error(f"Azure AD config error: {str(e)}")
            return Response(
                {'error': f'Configuration error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RoleManagementView(APIView):
    """
    API endpoint for role management
    """
    permission_classes = [IsAuthenticated, HasPermission(['roles.manage'])]
    
    def get(self, request):
        """Get all roles for the company"""
        try:
            company = request.company
            roles = EnhancedRole.objects.filter(
                tenant_id=company.id,
                is_active=True
            ).order_by('-priority', 'name')
            
            role_data = []
            for role in roles:
                role_data.append({
                    'id': str(role.id),
                    'name': role.name,
                    'display_name': role.display_name,
                    'description': role.description,
                    'role_type': role.role_type,
                    'is_system_role': role.is_system_role,
                    'is_default': role.is_default,
                    'priority': role.priority,
                    'azure_group_id': role.azure_group_id,
                    'azure_group_name': role.azure_group_name,
                    'auto_sync_from_azure': role.auto_sync_from_azure,
                    'permission_state': role.permission_state,
                    'users_count': role.get_users_count(),
                    'created_at': role.created_at.isoformat(),
                    'updated_at': role.updated_at.isoformat()
                })
            
            return Response({'roles': role_data})
            
        except Exception as e:
            logger.error(f"Error getting roles: {str(e)}")
            return Response(
                {'error': f'Failed to get roles: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Create a new role"""
        try:
            company = request.company
            data = request.data
            
            # Validate required fields
            if not data.get('name') or not data.get('display_name'):
                return Response(
                    {'error': 'Name and display_name are required'}, 
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
            
            # Log role creation
            AuditLog.log_action(
                user=request.user,
                company=company,
                action_type='role_assigned',
                action_description=f'Role {role.display_name} created',
                resource_type='role',
                resource_id=str(role.id),
                success=True,
                details={'role_name': role.name}
            )
            
            return Response({
                'id': str(role.id),
                'name': role.name,
                'display_name': role.display_name,
                'description': role.description,
                'role_type': role.role_type,
                'priority': role.priority,
                'status': 'created'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating role: {str(e)}")
            return Response(
                {'error': f'Failed to create role: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserRoleAssignmentView(APIView):
    """
    API endpoint for user role assignment management
    """
    permission_classes = [IsAuthenticated, HasPermission(['users.manage'])]
    
    def get(self, request):
        """Get user role assignments for the company"""
        try:
            company = request.company
            user_id = request.GET.get('user_id')
            
            if user_id:
                # Get assignments for specific user
                assignments = UserRoleAssignment.objects.filter(
                    user_id=user_id,
                    company=company,
                    is_active=True
                ).select_related('role', 'user')
            else:
                # Get all assignments for company
                assignments = UserRoleAssignment.objects.filter(
                    company=company,
                    is_active=True
                ).select_related('role', 'user')
            
            assignment_data = []
            for assignment in assignments:
                assignment_data.append({
                    'id': str(assignment.id),
                    'user_id': str(assignment.user.id),
                    'user_email': assignment.user.email,
                    'user_name': assignment.user.name,
                    'role_id': str(assignment.role.id),
                    'role_name': assignment.role.name,
                    'role_display_name': assignment.role.display_name,
                    'assignment_source': assignment.assignment_source,
                    'source_reference': assignment.source_reference,
                    'assigned_at': assignment.assigned_at.isoformat(),
                    'expires_at': assignment.expires_at.isoformat() if assignment.expires_at else None,
                    'is_expired': assignment.is_expired
                })
            
            return Response({'assignments': assignment_data})
            
        except Exception as e:
            logger.error(f"Error getting user role assignments: {str(e)}")
            return Response(
                {'error': f'Failed to get assignments: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Assign role to user"""
        try:
            company = request.company
            data = request.data
            
            # Validate required fields
            user_id = data.get('user_id')
            role_id = data.get('role_id')
            
            if not user_id or not role_id:
                return Response(
                    {'error': 'user_id and role_id are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user and role
            try:
                user = User.objects.get(id=user_id)
                role = EnhancedRole.objects.get(id=role_id, tenant_id=company.id)
            except (User.DoesNotExist, EnhancedRole.DoesNotExist):
                return Response(
                    {'error': 'User or role not found'}, 
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
                        {'error': 'Role assignment already exists'}, 
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
                    assignment_source=data.get('assignment_source', 'direct'),
                    source_reference=data.get('source_reference', ''),
                    assigned_by=request.user,
                    expires_at=data.get('expires_at'),
                    is_active=True
                )
            
            # Log role assignment
            AuditLog.log_action(
                user=request.user,
                company=company,
                action_type='role_assigned',
                action_description=f'Role {role.display_name} assigned to {user.email}',
                resource_type='user_role_assignment',
                resource_id=str(assignment.id),
                success=True,
                details={
                    'user_email': user.email,
                    'role_name': role.name,
                    'assignment_source': assignment.assignment_source
                }
            )
            
            return Response({
                'id': str(assignment.id),
                'user_email': user.email,
                'role_name': role.display_name,
                'assignment_source': assignment.assignment_source,
                'assigned_at': assignment.assigned_at.isoformat(),
                'status': 'assigned'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}")
            return Response(
                {'error': f'Failed to assign role: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request):
        """Remove role assignment from user"""
        try:
            company = request.company
            assignment_id = request.data.get('assignment_id')
            
            if not assignment_id:
                return Response(
                    {'error': 'assignment_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get assignment
            try:
                assignment = UserRoleAssignment.objects.get(
                    id=assignment_id,
                    company=company
                )
            except UserRoleAssignment.DoesNotExist:
                return Response(
                    {'error': 'Assignment not found'}, 
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
                action_description=f'Role {assignment.role.display_name} removed from {assignment.user.email}',
                resource_type='user_role_assignment',
                resource_id=str(assignment.id),
                success=True,
                details={
                    'user_email': assignment.user.email,
                    'role_name': assignment.role.name,
                    'assignment_source': assignment.assignment_source
                }
            )
            
            return Response({
                'status': 'removed',
                'message': f'Role {assignment.role.display_name} removed from {assignment.user.email}'
            })
            
        except Exception as e:
            logger.error(f"Error removing role assignment: {str(e)}")
            return Response(
                {'error': f'Failed to remove role assignment: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AzureADGroupSyncView(APIView):
    """
    API endpoint for syncing Azure AD groups to roles
    """
    permission_classes = [IsAuthenticated, HasPermission(['roles.manage'])]
    
    def post(self, request):
        """Sync Azure AD groups to application roles"""
        try:
            company = request.company
            data = request.data
            
            # Get access token for Azure AD API calls
            access_token = data.get('access_token')
            if not access_token:
                return Response(
                    {'error': 'Access token is required for group sync'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Sync groups
            success = AzureADRBACManager.sync_azure_groups_to_roles(company, access_token)
            
            if success:
                # Get updated group mappings
                group_mappings = AzureADGroupMapping.objects.filter(
                    company=company,
                    is_active=True
                ).select_related('role')
                
                mappings_data = []
                for mapping in group_mappings:
                    mappings_data.append({
                        'id': str(mapping.id),
                        'azure_group_id': mapping.azure_group_id,
                        'azure_group_name': mapping.azure_group_name,
                        'azure_group_description': mapping.azure_group_description,
                        'role_id': str(mapping.role.id),
                        'role_name': mapping.role.name,
                        'role_display_name': mapping.role.display_name,
                        'auto_sync': mapping.auto_sync,
                        'last_synced_at': mapping.last_synced_at.isoformat() if mapping.last_synced_at else None
                    })
                
                return Response({
                    'status': 'success',
                    'message': 'Azure AD groups synced successfully',
                    'group_mappings': mappings_data
                })
            else:
                return Response(
                    {'error': 'Failed to sync Azure AD groups'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        except Exception as e:
            logger.error(f"Error syncing Azure AD groups: {str(e)}")
            return Response(
                {'error': f'Group sync failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditLogView(APIView):
    """
    API endpoint for viewing audit logs
    """
    permission_classes = [IsAuthenticated, HasPermission(['audit.access'])]
    
    def get(self, request):
        """Get audit logs for the company"""
        try:
            company = request.company
            
            # Get query parameters
            action_type = request.GET.get('action_type')
            user_id = request.GET.get('user_id')
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            success_only = request.GET.get('success_only', 'false').lower() == 'true'
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 50))
            
            # Build query
            query = AuditLog.objects.filter(company=company)
            
            if action_type:
                query = query.filter(action_type=action_type)
            
            if user_id:
                query = query.filter(user_id=user_id)
            
            if start_date:
                query = query.filter(created_at__gte=start_date)
            
            if end_date:
                query = query.filter(created_at__lte=end_date)
            
            if success_only:
                query = query.filter(success=True)
            
            # Order and paginate
            query = query.order_by('-created_at')
            total_count = query.count()
            
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            logs = query[start_index:end_index]
            
            # Serialize logs
            logs_data = []
            for log in logs:
                logs_data.append({
                    'id': str(log.id),
                    'user_email': log.user.email if log.user else 'System',
                    'action_type': log.action_type,
                    'action_description': log.action_description,
                    'resource_type': log.resource_type,
                    'resource_id': log.resource_id,
                    'ip_address': str(log.ip_address) if log.ip_address else None,
                    'user_agent': log.user_agent,
                    'request_method': log.request_method,
                    'request_path': log.request_path,
                    'success': log.success,
                    'error_message': log.error_message,
                    'details': log.details,
                    'created_at': log.created_at.isoformat()
                })
            
            return Response({
                'logs': logs_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': (total_count + page_size - 1) // page_size
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting audit logs: {str(e)}")
            return Response(
                {'error': f'Failed to get audit logs: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
