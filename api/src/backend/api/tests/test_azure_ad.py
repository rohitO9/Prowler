"""
Tests for Azure AD integration
"""

import json
import uuid
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from api.v1.models.azure_ad import (
    AzureADGroupMapping,
    AzureADTenantMapping,
    AzureADUserSync,
    AzureADUserProfile,
    AzureADAuditLog,
    AzureADTokenCache,
)
from api.v1.models import User, Role, Tenant
from api.v1.utils.azure_ad_utils import AzureADUtils

User = get_user_model()


class AzureADViewsTestCase(APITestCase):
    """Test cases for Azure AD views"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            description='Test tenant for Azure AD'
        )

    @patch('api.v1.views.azure_ad.requests.post')
    @patch('api.v1.views.azure_ad.requests.get')
    def test_azure_ad_authentication_success(self, mock_get, mock_post):
        """Test successful Azure AD authentication"""
        # Mock token exchange response
        mock_post.return_value.json.return_value = {
            'access_token': 'mock_access_token',
            'refresh_token': 'mock_refresh_token',
            'expires_in': 3600
        }
        mock_post.return_value.raise_for_status.return_value = None

        # Mock user info response
        mock_get.return_value.json.return_value = {
            'id': 'azure_user_id_123',
            'mail': 'test@example.com',
            'givenName': 'Test',
            'surname': 'User',
            'displayName': 'Test User'
        }
        mock_get.return_value.raise_for_status.return_value = None

        url = reverse('token-azure')
        data = {
            'code': 'mock_auth_code',
            'tenant_id': str(self.tenant.id)
        }

        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)

    @patch('api.v1.views.azure_ad.requests.post')
    def test_azure_ad_authentication_invalid_code(self, mock_post):
        """Test Azure AD authentication with invalid code"""
        mock_post.return_value.raise_for_status.side_effect = Exception('Invalid code')

        url = reverse('token-azure')
        data = {'code': 'invalid_code'}

        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_azure_ad_config_endpoint(self):
        """Test Azure AD configuration endpoint"""
        url = reverse('azure-config')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('client_id', response.data)
        self.assertIn('tenant_id', response.data)
        self.assertIn('redirect_uri', response.data)


class AzureADUtilsTestCase(TestCase):
    """Test cases for Azure AD utilities"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.role = Role.objects.create(name='admin')
        self.tenant = Tenant.objects.create(name='Test Tenant')

    @patch('api.v1.utils.azure_ad_utils.requests.get')
    def test_validate_token_success(self, mock_get):
        """Test successful token validation"""
        # Mock public keys response
        mock_get.return_value.json.return_value = {
            'keys': [{
                'kid': 'test_kid',
                'n': 'test_n',
                'e': 'AQAB'
            }]
        }
        mock_get.return_value.raise_for_status.return_value = None

        # Mock JWT token
        token = 'mock.jwt.token'
        
        with patch('api.v1.utils.azure_ad_utils.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                'aud': 'test_client_id',
                'iss': 'https://login.microsoftonline.com/test_tenant/v2.0',
                'sub': 'test_user_id'
            }
            
            is_valid, token_data = AzureADUtils.validate_token(token)
            
            self.assertTrue(is_valid)
            self.assertIn('sub', token_data)

    def test_validate_token_expired(self):
        """Test token validation with expired token"""
        with patch('api.v1.utils.azure_ad_utils.jwt.decode') as mock_decode:
            mock_decode.side_effect = Exception('Token has expired')
            
            is_valid, token_data = AzureADUtils.validate_token('expired.token')
            
            self.assertFalse(is_valid)
            self.assertIn('error', token_data)

    @patch('api.v1.utils.azure_ad_utils.requests.get')
    def test_get_user_groups_success(self, mock_get):
        """Test successful user groups retrieval"""
        mock_get.return_value.json.return_value = {
            'value': [
                {'id': 'group1', 'displayName': 'Admin Group'},
                {'id': 'group2', 'displayName': 'User Group'}
            ]
        }
        mock_get.return_value.raise_for_status.return_value = None

        groups = AzureADUtils.get_user_groups('mock_access_token')
        
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]['displayName'], 'Admin Group')

    @patch('api.v1.utils.azure_ad_utils.requests.get')
    def test_get_user_groups_failure(self, mock_get):
        """Test user groups retrieval failure"""
        mock_get.return_value.raise_for_status.side_effect = Exception('API Error')

        groups = AzureADUtils.get_user_groups('mock_access_token')
        
        self.assertEqual(len(groups), 0)

    def test_validate_domain_allowed(self):
        """Test domain validation with allowed domain"""
        with self.settings(AZURE_AD_ALLOWED_DOMAINS=['example.com']):
            is_allowed = AzureADUtils.validate_domain('test@example.com')
            self.assertTrue(is_allowed)

    def test_validate_domain_not_allowed(self):
        """Test domain validation with disallowed domain"""
        with self.settings(AZURE_AD_ALLOWED_DOMAINS=['example.com']):
            is_allowed = AzureADUtils.validate_domain('test@other.com')
            self.assertFalse(is_allowed)

    def test_validate_domain_no_restrictions(self):
        """Test domain validation with no restrictions"""
        with self.settings(AZURE_AD_ALLOWED_DOMAINS=[]):
            is_allowed = AzureADUtils.validate_domain('test@any.com')
            self.assertTrue(is_allowed)


class AzureADModelsTestCase(TestCase):
    """Test cases for Azure AD models"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.role = Role.objects.create(name='admin')
        self.tenant = Tenant.objects.create(name='Test Tenant')

    def test_azure_ad_group_mapping_creation(self):
        """Test Azure AD group mapping creation"""
        mapping = AzureADGroupMapping.objects.create(
            azure_group_id='test_group_id',
            azure_group_name='Test Group',
            role=self.role
        )
        
        self.assertEqual(mapping.azure_group_id, 'test_group_id')
        self.assertEqual(mapping.azure_group_name, 'Test Group')
        self.assertEqual(mapping.role, self.role)
        self.assertTrue(mapping.is_active)

    def test_azure_ad_tenant_mapping_creation(self):
        """Test Azure AD tenant mapping creation"""
        mapping = AzureADTenantMapping.objects.create(
            tenant=self.tenant,
            azure_group_id='test_tenant_group_id',
            azure_group_name='Test Tenant Group'
        )
        
        self.assertEqual(mapping.tenant, self.tenant)
        self.assertEqual(mapping.azure_group_id, 'test_tenant_group_id')
        self.assertEqual(mapping.azure_group_name, 'Test Tenant Group')

    def test_azure_ad_user_sync_creation(self):
        """Test Azure AD user sync record creation"""
        sync_record = AzureADUserSync.objects.create(
            user=self.user,
            azure_user_id='azure_user_123',
            sync_type='profile',
            status='success',
            sync_data={'test': 'data'}
        )
        
        self.assertEqual(sync_record.user, self.user)
        self.assertEqual(sync_record.azure_user_id, 'azure_user_123')
        self.assertEqual(sync_record.sync_type, 'profile')
        self.assertEqual(sync_record.status, 'success')

    def test_azure_ad_token_cache_creation(self):
        """Test Azure AD token cache creation"""
        from django.utils import timezone
        from datetime import timedelta
        
        expires_at = timezone.now() + timedelta(hours=1)
        token_cache = AzureADTokenCache.objects.create(
            user=self.user,
            access_token='mock_access_token',
            refresh_token='mock_refresh_token',
            expires_at=expires_at
        )
        
        self.assertEqual(token_cache.user, self.user)
        self.assertEqual(token_cache.access_token, 'mock_access_token')
        self.assertFalse(token_cache.is_expired)

    def test_azure_ad_user_profile_creation(self):
        """Test Azure AD user profile creation"""
        profile = AzureADUserProfile.objects.create(
            user=self.user,
            azure_ad_id='azure_user_123',
            job_title='Software Engineer',
            department='Engineering',
            company_name='Test Company'
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.azure_ad_id, 'azure_user_123')
        self.assertEqual(profile.job_title, 'Software Engineer')

    def test_azure_ad_audit_log_creation(self):
        """Test Azure AD audit log creation"""
        audit_log = AzureADAuditLog.objects.create(
            user=self.user,
            action='login',
            details={'ip': '127.0.0.1'},
            ip_address='127.0.0.1',
            success=True
        )
        
        self.assertEqual(audit_log.user, self.user)
        self.assertEqual(audit_log.action, 'login')
        self.assertTrue(audit_log.success)


class AzureADManagementCommandTestCase(TestCase):
    """Test cases for Azure AD management commands"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    @patch('api.management.commands.sync_azure_ad_users.requests.post')
    @patch('api.management.commands.sync_azure_ad_users.requests.get')
    def test_sync_specific_user(self, mock_get, mock_post):
        """Test syncing a specific user"""
        # Mock token response
        mock_post.return_value.json.return_value = {
            'access_token': 'mock_access_token'
        }
        mock_post.return_value.raise_for_status.return_value = None

        # Mock user info response
        mock_get.return_value.json.return_value = {
            'id': 'azure_user_123',
            'mail': 'test@example.com',
            'givenName': 'Test',
            'surname': 'User',
            'jobTitle': 'Software Engineer',
            'department': 'Engineering'
        }
        mock_get.return_value.raise_for_status.return_value = None

        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        call_command('sync_azure_ad_users', '--user-id', 'azure_user_123', stdout=out)
        
        # Check if user profile was created
        profile = AzureADUserProfile.objects.filter(azure_ad_id='azure_user_123').first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.job_title, 'Software Engineer')

    @patch('api.management.commands.sync_azure_ad_users.requests.post')
    def test_sync_without_azure_config(self, mock_post):
        """Test sync command without Azure AD configuration"""
        with self.settings(AZURE_AD_ENABLED=False):
            from django.core.management import call_command
            from django.core.management.base import CommandError
            from io import StringIO
            
            out = StringIO()
            with self.assertRaises(CommandError):
                call_command('sync_azure_ad_users', '--all', stdout=out)


class AzureADIntegrationTestCase(APITestCase):
    """Integration tests for Azure AD functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.role = Role.objects.create(name='admin')
        self.tenant = Tenant.objects.create(name='Test Tenant')

    @patch('api.v1.views.azure_ad.AzureADUtils.validate_domain')
    @patch('api.v1.views.azure_ad.AzureADUtils.get_user_groups')
    def test_azure_ad_user_creation_with_groups(self, mock_get_groups, mock_validate_domain):
        """Test Azure AD user creation with group synchronization"""
        mock_validate_domain.return_value = True
        mock_get_groups.return_value = [
            {'id': 'admin_group_id', 'displayName': 'Admin Group'}
        ]

        # Create group mapping
        AzureADGroupMapping.objects.create(
            azure_group_id='admin_group_id',
            azure_group_name='Admin Group',
            role=self.role
        )

        # Simulate user creation with group sync
        user_info = {
            'id': 'azure_user_123',
            'mail': 'newuser@example.com',
            'givenName': 'New',
            'surname': 'User'
        }

        user = AzureADUtils.create_user_from_azure_info(user_info)
        
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.azure_ad_id, 'azure_user_123')

    def test_azure_ad_audit_logging(self):
        """Test Azure AD audit logging functionality"""
        # Create audit log entry
        audit_log = AzureADAuditLog.objects.create(
            user=self.user,
            action='login',
            details={'method': 'azure_ad'},
            ip_address='127.0.0.1',
            success=True
        )
        
        self.assertEqual(audit_log.user, self.user)
        self.assertEqual(audit_log.action, 'login')
        self.assertTrue(audit_log.success)
        
        # Test audit log querying
        login_logs = AzureADAuditLog.objects.filter(action='login')
        self.assertEqual(login_logs.count(), 1)
        self.assertEqual(login_logs.first(), audit_log) 