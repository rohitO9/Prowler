"""
Test Suite for Azure AD RBAC System
"""

import json
import uuid
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from api.models.azure_rbac import (
    Company, AzureADUserProfile, AzureADTokenCache, 
    UserRoleAssignment, AuditLog, Permission
)
from api.models.enhanced_role import EnhancedRole
from api.services.azure_ad_auth import AzureADAuthService, AzureADRBACManager

User = get_user_model()


class CompanyModelTest(TestCase):
    """Test Company model functionality"""
    
    def setUp(self):
        self.company_data = {
            'name': 'Test Company',
            'domain': 'testcompany.com',
            'azure_tenant_id': str(uuid.uuid4()),
            'azure_client_id': 'test-client-id',
            'azure_client_secret': 'test-secret',
            'azure_redirect_uri': 'http://localhost:3000/callback',
            'azure_scopes': ['openid', 'profile', 'email'],
            'azure_allowed_domains': ['testcompany.com']
        }
    
    def test_company_creation(self):
        """Test company creation"""
        company = Company.objects.create(**self.company_data)
        
        self.assertEqual(company.name, 'Test Company')
        self.assertEqual(company.domain, 'testcompany.com')
        self.assertEqual(company.azure_tenant_id, self.company_data['azure_tenant_id'])
        self.assertTrue(company.is_active)
        self.assertEqual(company.subscription_tier, 'trial')
    
    def test_azure_client_secret_encryption(self):
        """Test Azure client secret encryption/decryption"""
        company = Company.objects.create(**self.company_data)
        
        # Test setting secret
        company.azure_client_secret = 'new-secret'
        company.save()
        
        # Test getting secret
        self.assertEqual(company.azure_client_secret, 'new-secret')
    
    def test_azure_authority_url(self):
        """Test Azure authority URL generation"""
        company = Company.objects.create(**self.company_data)
        expected_url = f"https://login.microsoftonline.com/{company.azure_tenant_id}"
        self.assertEqual(company.get_azure_authority_url(), expected_url)
    
    def test_trial_status(self):
        """Test trial status checking"""
        company = Company.objects.create(**self.company_data)
        
        # No trial end date
        self.assertFalse(company.is_trial_active())
        
        # Set trial end date in future
        from django.utils import timezone
        from datetime import timedelta
        company.trial_end = timezone.now() + timedelta(days=7)
        company.save()
        self.assertTrue(company.is_trial_active())
        
        # Set trial end date in past
        company.trial_end = timezone.now() - timedelta(days=1)
        company.save()
        self.assertFalse(company.is_trial_active())


class EnhancedRoleModelTest(TestCase):
    """Test EnhancedRole model functionality"""
    
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            domain='testcompany.com',
            azure_tenant_id=str(uuid.uuid4()),
            azure_client_id='test-client-id',
            azure_client_secret='test-secret',
            azure_redirect_uri='http://localhost:3000/callback'
        )
    
    def test_role_creation(self):
        """Test role creation"""
        role = EnhancedRole.objects.create(
            tenant_id=self.company.id,
            name='admin',
            display_name='Administrator',
            description='Full admin access',
            role_type='system',
            manage_users=True,
            manage_account=True,
            priority=100
        )
        
        self.assertEqual(role.name, 'admin')
        self.assertEqual(role.display_name, 'Administrator')
        self.assertEqual(role.role_type, 'system')
        self.assertTrue(role.manage_users)
        self.assertEqual(role.priority, 100)
    
    def test_permission_state_calculation(self):
        """Test permission state calculation"""
        # Unlimited permissions
        role = EnhancedRole.objects.create(
            tenant_id=self.company.id,
            name='admin',
            display_name='Administrator',
            manage_users=True,
            manage_account=True,
            manage_billing=True,
            manage_providers=True,
            manage_integrations=True,
            manage_scans=True
        )
        self.assertEqual(role.permission_state, 'unlimited')
        
        # No permissions
        role = EnhancedRole.objects.create(
            tenant_id=self.company.id,
            name='viewer',
            display_name='Viewer',
            manage_users=False,
            manage_account=False,
            manage_billing=False,
            manage_providers=False,
            manage_integrations=False,
            manage_scans=False
        )
        self.assertEqual(role.permission_state, 'none')
        
        # Limited permissions
        role = EnhancedRole.objects.create(
            tenant_id=self.company.id,
            name='user',
            display_name='User',
            manage_users=False,
            manage_account=False,
            manage_billing=False,
            manage_providers=False,
            manage_integrations=False,
            manage_scans=True
        )
        self.assertEqual(role.permission_state, 'limited')
    
    def test_create_default_roles(self):
        """Test default role creation"""
        roles = EnhancedRole.create_default_roles(self.company.id)
        
        self.assertEqual(len(roles), 3)
        
        role_names = [role.name for role in roles]
        self.assertIn('admin', role_names)
        self.assertIn('user', role_names)
        self.assertIn('viewer', role_names)
        
        # Check admin role
        admin_role = next(role for role in roles if role.name == 'admin')
        self.assertTrue(admin_role.manage_users)
        self.assertEqual(admin_role.priority, 100)
        
        # Check default role
        user_role = next(role for role in roles if role.name == 'user')
        self.assertTrue(user_role.is_default)


class AzureADAuthServiceTest(TestCase):
    """Test AzureADAuthService functionality"""
    
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            domain='testcompany.com',
            azure_tenant_id=str(uuid.uuid4()),
            azure_client_id='test-client-id',
            azure_client_secret='test-secret',
            azure_redirect_uri='http://localhost:3000/callback'
        )
        self.auth_service = AzureADAuthService(self.company)
    
    @patch('api.services.azure_ad_auth.requests.post')
    def test_exchange_code_for_token_success(self, mock_post):
        """Test successful token exchange"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        success, token_data = self.auth_service.exchange_code_for_token('test-code')
        
        self.assertTrue(success)
        self.assertEqual(token_data['access_token'], 'test-access-token')
        self.assertEqual(token_data['token_type'], 'Bearer')
    
    @patch('api.services.azure_ad_auth.requests.post')
    def test_exchange_code_for_token_failure(self, mock_post):
        """Test failed token exchange"""
        # Mock failed response
        mock_post.side_effect = Exception('Network error')
        
        success, token_data = self.auth_service.exchange_code_for_token('test-code')
        
        self.assertFalse(success)
        self.assertIn('error', token_data)
    
    @patch('api.services.azure_ad_auth.requests.get')
    def test_get_user_info_success(self, mock_get):
        """Test successful user info retrieval"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'azure-user-id',
            'mail': 'user@testcompany.com',
            'displayName': 'Test User',
            'givenName': 'Test',
            'surname': 'User'
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        success, user_info = self.auth_service.get_user_info('test-token')
        
        self.assertTrue(success)
        self.assertEqual(user_info['mail'], 'user@testcompany.com')
        self.assertEqual(user_info['displayName'], 'Test User')
    
    def test_domain_validation(self):
        """Test domain validation"""
        # Allowed domain
        self.assertTrue(self.auth_service._is_domain_allowed('user@testcompany.com'))
        
        # Disallowed domain
        self.assertFalse(self.auth_service._is_domain_allowed('user@otherdomain.com'))
        
        # No allowed domains configured (should allow all)
        self.company.azure_allowed_domains = []
        self.company.save()
        self.auth_service = AzureADAuthService(self.company)
        self.assertTrue(self.auth_service._is_domain_allowed('user@anydomain.com'))


class AzureADRBACManagerTest(TestCase):
    """Test AzureADRBACManager functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='admin@test.com',
            name='Admin User'
        )
    
    def test_create_company_with_azure_config(self):
        """Test company creation with Azure configuration"""
        company = AzureADRBACManager.create_company_with_azure_config(
            name='Test Company',
            domain='testcompany.com',
            azure_tenant_id=str(uuid.uuid4()),
            azure_client_id='test-client-id',
            azure_client_secret='test-secret',
            azure_redirect_uri='http://localhost:3000/callback',
            created_by=self.user
        )
        
        self.assertEqual(company.name, 'Test Company')
        self.assertEqual(company.domain, 'testcompany.com')
        self.assertTrue(company.is_active)
        
        # Check that default roles were created
        roles = EnhancedRole.objects.filter(tenant_id=company.id)
        self.assertEqual(roles.count(), 3)
        
        # Check audit log
        audit_log = AuditLog.objects.filter(
            company=company,
            action_type='company_created'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertTrue(audit_log.success)


class CompanyRegistrationAPITest(APITestCase):
    """Test Company Registration API"""
    
    def test_company_registration_success(self):
        """Test successful company registration"""
        data = {
            'name': 'Test Company',
            'domain': 'testcompany.com',
            'azure_tenant_id': str(uuid.uuid4()),
            'azure_client_id': 'test-client-id',
            'azure_client_secret': 'test-secret',
            'azure_redirect_uri': 'http://localhost:3000/callback'
        }
        
        response = self.client.post('/api/v1/azure-rbac/companies/register/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('company_id', response.data)
        self.assertEqual(response.data['name'], 'Test Company')
        self.assertEqual(response.data['status'], 'created')
    
    def test_company_registration_missing_fields(self):
        """Test company registration with missing fields"""
        data = {
            'name': 'Test Company',
            'domain': 'testcompany.com'
            # Missing required fields
        }
        
        response = self.client.post('/api/v1/azure-rbac/companies/register/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_company_registration_duplicate_domain(self):
        """Test company registration with duplicate domain"""
        # Create existing company
        Company.objects.create(
            name='Existing Company',
            domain='testcompany.com',
            azure_tenant_id=str(uuid.uuid4()),
            azure_client_id='existing-client-id',
            azure_client_secret='existing-secret',
            azure_redirect_uri='http://localhost:3000/callback'
        )
        
        data = {
            'name': 'Test Company',
            'domain': 'testcompany.com',
            'azure_tenant_id': str(uuid.uuid4()),
            'azure_client_id': 'test-client-id',
            'azure_client_secret': 'test-secret',
            'azure_redirect_uri': 'http://localhost:3000/callback'
        }
        
        response = self.client.post('/api/v1/azure-rbac/companies/register/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already exists', response.data['error'])


class AzureADLoginAPITest(APITestCase):
    """Test Azure AD Login API"""
    
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            domain='testcompany.com',
            azure_tenant_id=str(uuid.uuid4()),
            azure_client_id='test-client-id',
            azure_client_secret='test-secret',
            azure_redirect_uri='http://localhost:3000/callback'
        )
    
    @patch('api.v1.views.azure_rbac.AzureADAuthService')
    def test_azure_login_success(self, mock_auth_service):
        """Test successful Azure AD login"""
        # Mock authentication service
        mock_service_instance = MagicMock()
        mock_auth_service.return_value = mock_service_instance
        
        mock_user = User.objects.create_user(
            email='user@testcompany.com',
            name='Test User'
        )
        
        mock_service_instance.authenticate_user.return_value = (True, {
            'user': mock_user,
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'company': self.company,
            'azure_user_info': {
                'id': 'azure-user-id',
                'mail': 'user@testcompany.com',
                'displayName': 'Test User'
            }
        })
        
        data = {
            'company': 'testcompany.com',
            'code': 'test-auth-code'
        }
        
        response = self.client.post('/api/v1/azure-rbac/auth/azure/login/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('user', response.data)
        self.assertIn('company', response.data)
    
    def test_azure_login_company_not_found(self):
        """Test Azure AD login with non-existent company"""
        data = {
            'company': 'nonexistent.com',
            'code': 'test-auth-code'
        }
        
        response = self.client.post('/api/v1/azure-rbac/auth/azure/login/', data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Company not found', response.data['error'])
    
    def test_azure_login_missing_code(self):
        """Test Azure AD login with missing authorization code"""
        data = {
            'company': 'testcompany.com'
            # Missing code
        }
        
        response = self.client.post('/api/v1/azure-rbac/auth/azure/login/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Authorization code is required', response.data['error'])


class RoleManagementAPITest(APITestCase):
    """Test Role Management API"""
    
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            domain='testcompany.com',
            azure_tenant_id=str(uuid.uuid4()),
            azure_client_id='test-client-id',
            azure_client_secret='test-secret',
            azure_redirect_uri='http://localhost:3000/callback'
        )
        
        self.user = User.objects.create_user(
            email='admin@testcompany.com',
            name='Admin User'
        )
        
        # Create admin role
        self.admin_role = EnhancedRole.objects.create(
            tenant_id=self.company.id,
            name='admin',
            display_name='Administrator',
            manage_users=True,
            manage_account=True,
            priority=100
        )
        
        # Assign admin role to user
        UserRoleAssignment.objects.create(
            user=self.user,
            role=self.admin_role,
            company=self.company,
            assignment_source='direct',
            is_active=True
        )
        
        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        access_token['company_id'] = str(self.company.id)
        access_token['permissions'] = ['roles.manage']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    def test_get_roles(self):
        """Test getting roles for company"""
        response = self.client.get('/api/v1/azure-rbac/roles/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('roles', response.data)
        self.assertEqual(len(response.data['roles']), 1)
        self.assertEqual(response.data['roles'][0]['name'], 'admin')
    
    def test_create_role(self):
        """Test creating a new role"""
        data = {
            'name': 'user',
            'display_name': 'User',
            'description': 'Standard user role',
            'role_type': 'company',
            'manage_scans': True,
            'priority': 10
        }
        
        response = self.client.post('/api/v1/azure-rbac/roles/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'user')
        self.assertEqual(response.data['display_name'], 'User')
        self.assertEqual(response.data['status'], 'created')
        
        # Verify role was created in database
        role = EnhancedRole.objects.get(
            tenant_id=self.company.id,
            name='user'
        )
        self.assertEqual(role.display_name, 'User')
        self.assertTrue(role.manage_scans)
    
    def test_create_role_duplicate_name(self):
        """Test creating role with duplicate name"""
        data = {
            'name': 'admin',  # Already exists
            'display_name': 'Another Admin',
            'description': 'Duplicate admin role'
        }
        
        response = self.client.post('/api/v1/azure-rbac/roles/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already exists', response.data['error'])


class UserRoleAssignmentAPITest(APITestCase):
    """Test User Role Assignment API"""
    
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            domain='testcompany.com',
            azure_tenant_id=str(uuid.uuid4()),
            azure_client_id='test-client-id',
            azure_client_secret='test-secret',
            azure_redirect_uri='http://localhost:3000/callback'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@testcompany.com',
            name='Admin User'
        )
        
        self.regular_user = User.objects.create_user(
            email='user@testcompany.com',
            name='Regular User'
        )
        
        # Create roles
        self.admin_role = EnhancedRole.objects.create(
            tenant_id=self.company.id,
            name='admin',
            display_name='Administrator',
            manage_users=True,
            priority=100
        )
        
        self.user_role = EnhancedRole.objects.create(
            tenant_id=self.company.id,
            name='user',
            display_name='User',
            manage_scans=True,
            priority=10
        )
        
        # Assign admin role to admin user
        UserRoleAssignment.objects.create(
            user=self.admin_user,
            role=self.admin_role,
            company=self.company,
            assignment_source='direct',
            is_active=True
        )
        
        # Create JWT token for admin user
        refresh = RefreshToken.for_user(self.admin_user)
        access_token = refresh.access_token
        access_token['company_id'] = str(self.company.id)
        access_token['permissions'] = ['users.manage']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    def test_assign_role_to_user(self):
        """Test assigning role to user"""
        data = {
            'user_id': str(self.regular_user.id),
            'role_id': str(self.user_role.id),
            'assignment_source': 'direct'
        }
        
        response = self.client.post('/api/v1/azure-rbac/user-roles/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user_email'], self.regular_user.email)
        self.assertEqual(response.data['role_name'], self.user_role.display_name)
        self.assertEqual(response.data['status'], 'assigned')
        
        # Verify assignment was created in database
        assignment = UserRoleAssignment.objects.get(
            user=self.regular_user,
            role=self.user_role,
            company=self.company
        )
        self.assertTrue(assignment.is_active)
        self.assertEqual(assignment.assignment_source, 'direct')
    
    def test_get_user_role_assignments(self):
        """Test getting user role assignments"""
        response = self.client.get('/api/v1/azure-rbac/user-roles/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('assignments', response.data)
        self.assertEqual(len(response.data['assignments']), 1)
        self.assertEqual(response.data['assignments'][0]['user_email'], self.admin_user.email)
    
    def test_remove_role_assignment(self):
        """Test removing role assignment"""
        # First assign a role
        assignment = UserRoleAssignment.objects.create(
            user=self.regular_user,
            role=self.user_role,
            company=self.company,
            assignment_source='direct',
            is_active=True
        )
        
        data = {
            'assignment_id': str(assignment.id)
        }
        
        response = self.client.delete('/api/v1/azure-rbac/user-roles/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'removed')
        
        # Verify assignment was deactivated
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)


class AuditLogAPITest(APITestCase):
    """Test Audit Log API"""
    
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            domain='testcompany.com',
            azure_tenant_id=str(uuid.uuid4()),
            azure_client_id='test-client-id',
            azure_client_secret='test-secret',
            azure_redirect_uri='http://localhost:3000/callback'
        )
        
        self.user = User.objects.create_user(
            email='admin@testcompany.com',
            name='Admin User'
        )
        
        # Create audit log entries
        AuditLog.objects.create(
            user=self.user,
            company=self.company,
            action_type='login',
            action_description='User logged in',
            success=True
        )
        
        AuditLog.objects.create(
            user=self.user,
            company=self.company,
            action_type='role_assigned',
            action_description='Role assigned to user',
            success=True
        )
        
        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        access_token['company_id'] = str(self.company.id)
        access_token['permissions'] = ['audit.access']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    def test_get_audit_logs(self):
        """Test getting audit logs"""
        response = self.client.get('/api/v1/azure-rbac/audit/logs/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('logs', response.data)
        self.assertIn('pagination', response.data)
        self.assertEqual(len(response.data['logs']), 2)
    
    def test_get_audit_logs_filtered(self):
        """Test getting filtered audit logs"""
        response = self.client.get('/api/v1/azure-rbac/audit/logs/?action_type=login')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['logs']), 1)
        self.assertEqual(response.data['logs'][0]['action_type'], 'login')
    
    def test_get_audit_logs_pagination(self):
        """Test audit logs pagination"""
        response = self.client.get('/api/v1/azure-rbac/audit/logs/?page=1&page_size=1')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['logs']), 1)
        self.assertEqual(response.data['pagination']['page'], 1)
        self.assertEqual(response.data['pagination']['page_size'], 1)
        self.assertEqual(response.data['pagination']['total_count'], 2)
