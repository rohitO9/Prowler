from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from api.models import TenantInvitation, Tenant
from django.contrib.auth import get_user_model
from unittest.mock import patch

User = get_user_model()

class TenantInvitationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.tenant = Tenant.objects.create(name='Test Tenant')
        self.client.force_authenticate(user=self.user)
        
    def test_create_invitation(self):
        url = f'/api/v1/tenants/{self.tenant.id}/invitations/'
        data = {
            'email': 'newuser@example.com',
            'role': 'member',
            'expires_in_days': 7
        }
        
        with patch('api.utils.email.send_invitation_email'):
            response = self.client.post(url, data)
            
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TenantInvitation.objects.filter(
            email='newuser@example.com'
        ).exists())
    
    def test_list_invitations(self):
        url = f'/api/v1/tenants/{self.tenant.id}/invitations/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_revoke_invitation(self):
        invitation = TenantInvitation.objects.create(
            tenant=self.tenant,
            email='test@example.com',
            role='member',
            invited_by=self.user,
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )
        
        url = f'/api/v1/tenants/{self.tenant.id}/invitations/{invitation.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)