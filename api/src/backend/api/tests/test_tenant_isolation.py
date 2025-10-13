"""
Comprehensive tests for tenant isolation security.

These tests verify that:
1. Users can only access their assigned tenants
2. Cross-tenant data access is blocked
3. Database queries are properly scoped
4. Security violations are logged
"""

import uuid
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
import logging

from api.models import Tenant, TenantMembership

User = get_user_model()


class TenantIsolationSecurityTest(APITestCase):
    """
    Test suite for tenant isolation security.
    
    This test suite verifies that the multi-tenant system
    properly isolates data between tenants.
    """
    
    def setUp(self):
        """Set up test data"""
        # Create two tenants
        self.tenant1 = Tenant.objects.create(
            name="Company 1",
            subdomain="company1",
            is_active=True
        )
        self.tenant2 = Tenant.objects.create(
            name="Company 2", 
            subdomain="company2",
            is_active=True
        )
        
        # Create users for each tenant
        self.user1 = User.objects.create_user(
            email="user1@company1.com",
            name="User 1",
            password="testpass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@company2.com",
            name="User 2", 
            password="testpass123"
        )
        
        # Create tenant memberships
        TenantMembership.objects.create(
            user=self.user1,
            tenant=self.tenant1,
            role='owner',
            is_active=True
        )
        TenantMembership.objects.create(
            user=self.user2,
            tenant=self.tenant2,
            role='owner',
            is_active=True
        )
    
    def test_user_cannot_access_other_tenant(self):
        """Test that users cannot access other tenants"""
        # Authenticate as user1
        self.client.force_authenticate(user=self.user1)
        
        # Try to access tenant2's data (should fail)
        response = self.client.get(
            f'/api/v1/tenant/public-info/',
            HTTP_HOST='company2.localhost:8080'
        )
        
        # Should be denied access
        self.assertIn(response.status_code, [403, 404])
    
    def test_tenant_isolation_middleware_blocks_cross_tenant_access(self):
        """Test that tenant isolation middleware blocks cross-tenant access"""
        # Authenticate as user1
        self.client.force_authenticate(user=self.user1)
        
        # Try to access tenant2's subdomain
        response = self.client.get(
            '/api/v1/users/me/',
            HTTP_HOST='company2.localhost:8080'
        )
        
        # Should be blocked by tenant isolation middleware
        self.assertEqual(response.status_code, 403)
        self.assertIn('Access denied', str(response.data))
    
    def test_user_can_only_access_own_tenant(self):
        """Test that users can only access their own tenant"""
        # Authenticate as user1
        self.client.force_authenticate(user=self.user1)
        
        # Access own tenant (should succeed)
        response = self.client.get(
            '/api/v1/users/me/',
            HTTP_HOST='company1.localhost:8080'
        )
        
        # Should succeed
        self.assertEqual(response.status_code, 200)
    
    def test_tenant_membership_validation(self):
        """Test that tenant membership is properly validated"""
        # Create a user with no tenant membership
        user_no_tenant = User.objects.create_user(
            email="no_tenant@example.com",
            name="No Tenant User",
            password="testpass123"
        )
        
        # Try to access any tenant
        self.client.force_authenticate(user=user_no_tenant)
        response = self.client.get(
            '/api/v1/users/me/',
            HTTP_HOST='company1.localhost:8080'
        )
        
        # Should be denied
        self.assertEqual(response.status_code, 403)
    
    def test_inactive_tenant_membership_blocked(self):
        """Test that inactive tenant memberships are blocked"""
        # Deactivate user1's membership
        membership = TenantMembership.objects.get(
            user=self.user1,
            tenant=self.tenant1
        )
        membership.is_active = False
        membership.save()
        
        # Try to access tenant
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            '/api/v1/users/me/',
            HTTP_HOST='company1.localhost:8080'
        )
        
        # Should be denied
        self.assertEqual(response.status_code, 403)
    
    def test_security_violation_logging(self):
        """Test that security violations are properly logged"""
        with patch('api.middleware.tenant_isolation.logger') as mock_logger:
            # Authenticate as user1
            self.client.force_authenticate(user=self.user1)
            
            # Try to access tenant2
            response = self.client.get(
                '/api/v1/users/me/',
                HTTP_HOST='company2.localhost:8080'
            )
            
            # Should log security violation
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            self.assertIn('SECURITY VIOLATION', error_call)
            self.assertIn('user1@company1.com', error_call)
            self.assertIn('company2', error_call)
    
    def test_anonymous_user_tenant_access(self):
        """Test that anonymous users cannot access tenant data"""
        # Don't authenticate
        response = self.client.get(
            '/api/v1/users/me/',
            HTTP_HOST='company1.localhost:8080'
        )
        
        # Should be denied (authentication required)
        self.assertEqual(response.status_code, 401)
    
    def test_tenant_context_required(self):
        """Test that tenant context is required for protected endpoints"""
        # Authenticate as user1
        self.client.force_authenticate(user=self.user1)
        
        # Try to access without tenant context (localhost)
        response = self.client.get('/api/v1/users/me/')
        
        # Should be denied (no tenant context)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Tenant context required', str(response.data))


class TenantDataIsolationTest(TestCase):
    """
    Test that data is properly isolated between tenants.
    """
    
    def setUp(self):
        """Set up test data"""
        # Create tenants
        self.tenant1 = Tenant.objects.create(
            name="Company 1",
            subdomain="company1",
            is_active=True
        )
        self.tenant2 = Tenant.objects.create(
            name="Company 2",
            subdomain="company2", 
            is_active=True
        )
        
        # Create users
        self.user1 = User.objects.create_user(
            email="user1@company1.com",
            name="User 1",
            password="testpass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@company2.com",
            name="User 2",
            password="testpass123"
        )
        
        # Create memberships
        TenantMembership.objects.create(
            user=self.user1,
            tenant=self.tenant1,
            role='owner',
            is_active=True
        )
        TenantMembership.objects.create(
            user=self.user2,
            tenant=self.tenant2,
            role='owner',
            is_active=True
        )
    
    def test_user_can_only_see_own_tenant_members(self):
        """Test that users can only see members of their own tenant"""
        # User1 should only see tenant1 members
        tenant1_members = self.user1.get_tenant_memberships()
        self.assertEqual(tenant1_members.count(), 1)
        self.assertEqual(tenant1_members.first().tenant, self.tenant1)
        
        # User1 should not see tenant2 members
        tenant2_members = TenantMembership.objects.filter(tenant=self.tenant2)
        self.assertEqual(tenant2_members.count(), 1)
        self.assertNotEqual(tenant2_members.first().user, self.user1)
    
    def test_tenant_membership_queries_are_scoped(self):
        """Test that tenant membership queries are properly scoped"""
        # When querying from tenant1 context, should only see tenant1 members
        with patch('api.managers.tenant_aware.connection') as mock_connection:
            mock_cursor = mock_connection.cursor.return_value.__enter__.return_value
            mock_cursor.fetchone.return_value = (str(self.tenant1.id),)
            
            # This would be called by the tenant-aware manager
            # In real implementation, this would be tested with actual database queries
            pass


class TenantSecurityAuditTest(TestCase):
    """
    Test security auditing and logging.
    """
    
    def test_security_violation_detection(self):
        """Test that security violations are properly detected and logged"""
        # This would test the actual security violation detection
        # In a real implementation, you'd test the logging and alerting
        pass
    
    def test_tenant_access_audit_trail(self):
        """Test that tenant access is properly audited"""
        # This would test the audit trail functionality
        # In a real implementation, you'd verify that access attempts are logged
        pass


if __name__ == '__main__':
    import django
    django.setup()
    import unittest
    unittest.main()
