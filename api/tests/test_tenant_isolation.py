from django.test import TestCase, Client
from api.models import Tenant, User
from rest_framework_simplejwt.tokens import RefreshToken


class TenantIsolationTest(TestCase):
    """Test suite for multi-tenant isolation"""
    
    def setUp(self):
        """Create test data"""
        # Create two separate tenants
        self.tenant1 = Tenant.objects.create(
            name='Tenant One',
            subdomain='tenant1',
            is_active=True
        )
        
        self.tenant2 = Tenant.objects.create(
            name='Tenant Two',
            subdomain='tenant2',
            is_active=True
        )
        
        # Create users for each tenant
        self.user1 = User.objects.create_user(
            email='user1@tenant1.com',
            username='user1@tenant1.com',
            password='testpass123',
            primary_tenant=self.tenant1
        )
        
        self.user2 = User.objects.create_user(
            email='user2@tenant2.com',
            username='user2@tenant2.com',
            password='testpass123',
            primary_tenant=self.tenant2
        )
    
    def test_duplicate_subdomain_prevented(self):
        """Test that duplicate subdomains are prevented by database constraint"""
        from django.db import IntegrityError
        
        with self.assertRaises(IntegrityError):
            Tenant.objects.create(
                name='Duplicate Tenant',
                subdomain='tenant1',  # Already exists!
            )
    
    def test_user_cannot_login_to_wrong_tenant(self):
        """User from tenant1 cannot login to tenant2"""
        client = Client(HTTP_HOST='tenant2.localhost:8080')
        
        response = client.post('/api/v1/tenant/login', {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'email': 'user1@tenant1.com',  # tenant1 user
                    'password': 'testpass123',
                }
            }
        }, content_type='application/vnd.api+json')
        
        self.assertEqual(response.status_code, 403)
        self.assertIn('wrong_tenant', str(response.content))
    
    def test_user_can_login_to_correct_tenant(self):
        """User can login to their own tenant"""
        client = Client(HTTP_HOST='tenant1.localhost:8080')
        
        response = client.post('/api/v1/tenant/login', {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'email': 'user1@tenant1.com',
                    'password': 'testpass123',
                }
            }
        }, content_type='application/vnd.api+json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('access_token', data['data']['attributes'])
        self.assertIn('refresh_token', data['data']['attributes'])
    
    def test_jwt_token_contains_tenant_info(self):
        """JWT token should include tenant information"""
        refresh = RefreshToken.for_user(self.user1)
        refresh['tenant_id'] = str(self.tenant1.id)
        refresh['tenant_subdomain'] = self.tenant1.subdomain
        
        # Decode and verify
        import jwt
        from django.conf import settings
        
        decoded = jwt.decode(
            str(refresh.access_token),
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
        
        self.assertEqual(decoded['tenant_id'], str(self.tenant1.id))
        self.assertEqual(decoded['tenant_subdomain'], 'tenant1')
    
    def test_jwt_from_tenant1_rejected_on_tenant2(self):
        """JWT from tenant1 should be rejected when accessing tenant2"""
        # Get token for tenant1 user
        client1 = Client(HTTP_HOST='tenant1.localhost:8080')
        login_response = client1.post('/api/v1/tenant/login', {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'email': 'user1@tenant1.com',
                    'password': 'testpass123',
                }
            }
        }, content_type='application/vnd.api+json')
        
        token = login_response.json()['data']['attributes']['access_token']
        
        # Try to use token on tenant2
        client2 = Client(HTTP_HOST='tenant2.localhost:8080')
        response = client2.get(
            '/api/v1/users/me',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(response.status_code, 403)
    
    def test_registration_prevents_duplicate_subdomain(self):
        """Registration should fail if subdomain already exists"""
        client = Client()
        
        response = client.post('/api/v1/tenant/register', {
            'data': {
                'type': 'registration',
                'attributes': {
                    'company_name': 'Test Company',
                    'subdomain': 'tenant1',  # Already exists!
                    'email': 'newuser@test.com',
                    'password': 'testpass123',
                }
            }
        }, content_type='application/vnd.api+json')
        
        self.assertEqual(response.status_code, 409)
        self.assertIn('subdomain_exists', str(response.content))
    
    def test_tenant_scoped_queryset(self):
        """Test that tenant-scoped models only return data for current tenant"""
        from api.models import Resource  # Assuming you have this model
        from api.models.managers import set_current_tenant, clear_current_tenant
        
        # Create resources for each tenant
        resource1 = Resource.objects.create(
            tenant=self.tenant1,
            name='Resource 1'
        )
        
        resource2 = Resource.objects.create(
            tenant=self.tenant2,
            name='Resource 2'
        )
        
        # Set current tenant to tenant1
        set_current_tenant(self.tenant1)
        
        # Should only see tenant1's resources
        resources = Resource.objects.all()
        self.assertEqual(resources.count(), 1)
        self.assertEqual(resources.first().id, resource1.id)
        
        # Change to tenant2
        set_current_tenant(self.tenant2)
        
        # Should only see tenant2's resources
        resources = Resource.objects.all()
        self.assertEqual(resources.count(), 1)
        self.assertEqual(resources.first().id, resource2.id)
        
        # Cleanup
        clear_current_tenant()
    
    def test_inactive_tenant_cannot_login(self):
        """Users cannot login to inactive tenants"""
        self.tenant1.is_active = False
        self.tenant1.save()
        
        client = Client(HTTP_HOST='tenant1.localhost:8080')
        
        response = client.post('/api/v1/tenant/login', {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'email': 'user1@tenant1.com',
                    'password': 'testpass123',
                }
            }
        }, content_type='application/vnd.api+json')
        
        self.assertEqual(response.status_code, 400)  # No tenant found
    
    def test_api_endpoint_requires_tenant(self):
        """API endpoints should reject requests without tenant context"""
        # Request to endpoint without subdomain
        client = Client(HTTP_HOST='localhost:8080')
        
        # Login first to get token
        client_with_tenant = Client(HTTP_HOST='tenant1.localhost:8080')
        login_response = client_with_tenant.post('/api/v1/tenant/login', {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'email': 'user1@tenant1.com',
                    'password': 'testpass123',
                }
            }
        }, content_type='application/vnd.api+json')
        
        token = login_response.json()['data']['attributes']['access_token']
        
        # Try to access endpoint without tenant subdomain
        response = client.get(
            '/api/v1/users/me',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(response.status_code, 400)  # Missing tenant


class TenantRegistrationTest(TestCase):
    """Test tenant registration flow"""
    
    def test_successful_registration(self):
        """Test successful tenant and user registration"""
        client = Client()
        
        response = client.post('/api/v1/tenant/register', {
            'data': {
                'type': 'registration',
                'attributes': {
                    'company_name': 'New Company',
                    'subdomain': 'newcompany',
                    'email': 'admin@newcompany.com',
                    'password': 'securepass123',
                    'first_name': 'John',
                    'last_name': 'Doe',
                }
            }
        }, content_type='application/vnd.api+json')
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        
        # Verify tokens returned
        self.assertIn('access_token', data['data']['attributes'])
        self.assertIn('refresh_token', data['data']['attributes'])
        
        # Verify tenant created
        tenant = Tenant.objects.get(subdomain='newcompany')
        self.assertEqual(tenant.name, 'New Company')
        
        # Verify user created
        user = User.objects.get(email='admin@newcompany.com')
        self.assertEqual(user.primary_tenant, tenant)
        self.assertTrue(user.is_active)
    
    def test_registration_validation(self):
        """Test registration validation errors"""
        client = Client()
        
        # Missing required fields
        response = client.post('/api/v1/tenant/register', {
            'data': {
                'type': 'registration',
                'attributes': {
                    'company_name': '',
                    'subdomain': '',
                }
            }
        }, content_type='application/vnd.api+json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('validation_error', str(response.content))