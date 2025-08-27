"""
Azure AD Serializers
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from api.v1.models import Tenant, Role, Membership

User = get_user_model()


class AzureADUserSerializer(serializers.ModelSerializer):
    """Serializer for Azure AD user data"""
    
    azure_ad_id = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    full_name = serializers.CharField(max_length=255, required=False)
    photo_url = serializers.URLField(required=False)
    groups = serializers.ListField(child=serializers.CharField(), required=False)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'azure_ad_id', 'photo_url', 'groups', 'is_active',
            'email_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AzureADTokenSerializer(serializers.Serializer):
    """Serializer for Azure AD token response"""
    
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField()
    scope = serializers.CharField(required=False)
    id_token = serializers.CharField(required=False)


class AzureADUserInfoSerializer(serializers.Serializer):
    """Serializer for Azure AD user information"""
    
    id = serializers.CharField()
    displayName = serializers.CharField(required=False)
    givenName = serializers.CharField(required=False)
    surname = serializers.CharField(required=False)
    mail = serializers.EmailField(required=False)
    userPrincipalName = serializers.CharField(required=False)
    businessPhones = serializers.ListField(child=serializers.CharField(), required=False)
    jobTitle = serializers.CharField(required=False)
    officeLocation = serializers.CharField(required=False)
    preferredLanguage = serializers.CharField(required=False)
    mobilePhone = serializers.CharField(required=False)
    department = serializers.CharField(required=False)
    companyName = serializers.CharField(required=False)


class AzureADGroupSerializer(serializers.Serializer):
    """Serializer for Azure AD group information"""
    
    id = serializers.CharField()
    displayName = serializers.CharField()
    description = serializers.CharField(required=False)
    mail = serializers.EmailField(required=False)
    mailEnabled = serializers.BooleanField(required=False)
    securityEnabled = serializers.BooleanField(required=False)


class AzureADAuthRequestSerializer(serializers.Serializer):
    """Serializer for Azure AD authentication request"""
    
    code = serializers.CharField(help_text="Authorization code from Azure AD")
    state = serializers.CharField(required=False, help_text="State parameter for CSRF protection")
    tenant_id = serializers.UUIDField(required=False, help_text="Target tenant ID")
    redirect_uri = serializers.URLField(required=False, help_text="Redirect URI")


class AzureADAuthResponseSerializer(serializers.Serializer):
    """Serializer for Azure AD authentication response"""
    
    access = serializers.CharField(help_text="JWT access token")
    refresh = serializers.CharField(help_text="JWT refresh token")
    user = AzureADUserSerializer(help_text="User information")
    tenant_id = serializers.UUIDField(required=False, help_text="Tenant ID")
    tenant_name = serializers.CharField(required=False, help_text="Tenant name")


class AzureADConfigSerializer(serializers.Serializer):
    """Serializer for Azure AD configuration"""
    
    client_id = serializers.CharField(help_text="Azure AD application client ID")
    tenant_id = serializers.CharField(help_text="Azure AD tenant ID")
    redirect_uri = serializers.URLField(help_text="Redirect URI for authentication")
    authority = serializers.URLField(help_text="Azure AD authority URL")
    scopes = serializers.ListField(child=serializers.CharField(), help_text="Required scopes")


class AzureADErrorSerializer(serializers.Serializer):
    """Serializer for Azure AD error responses"""
    
    error = serializers.CharField(help_text="Error message")
    error_description = serializers.CharField(required=False, help_text="Detailed error description")
    error_code = serializers.CharField(required=False, help_text="Azure AD error code")
    timestamp = serializers.DateTimeField(required=False, help_text="Error timestamp")


class AzureADUserSyncSerializer(serializers.Serializer):
    """Serializer for Azure AD user synchronization"""
    
    user_id = serializers.UUIDField(help_text="User ID to sync")
    sync_groups = serializers.BooleanField(default=True, help_text="Whether to sync user groups")
    sync_photo = serializers.BooleanField(default=False, help_text="Whether to sync user photo")
    force_update = serializers.BooleanField(default=False, help_text="Force update existing user data")


class AzureADGroupMappingSerializer(serializers.Serializer):
    """Serializer for Azure AD group to role mapping"""
    
    azure_group_id = serializers.CharField(help_text="Azure AD group ID")
    role_id = serializers.UUIDField(help_text="Local role ID")
    role_name = serializers.CharField(help_text="Role name")
    is_active = serializers.BooleanField(default=True, help_text="Whether mapping is active")


class AzureADTenantMappingSerializer(serializers.Serializer):
    """Serializer for Azure AD tenant mapping"""
    
    tenant_id = serializers.UUIDField(help_text="Local tenant ID")
    azure_group_id = serializers.CharField(help_text="Azure AD group ID for tenant")
    azure_group_name = serializers.CharField(help_text="Azure AD group name")
    is_active = serializers.BooleanField(default=True, help_text="Whether mapping is active") 