"""
Django REST Framework Serializers

This module provides serializers for API data validation and transformation.
"""

from rest_framework import serializers
from api.models import User, Tenant, TenantMembership
from api.models import TenantOAuthConfig, TenantOAuthUser


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'is_active', 'is_verified',
            'date_joined', 'primary_tenant'
        ]
        read_only_fields = ['id', 'date_joined']


class TenantSerializer(serializers.ModelSerializer):
    """Serializer for Tenant model"""
    
    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'subdomain', 'domain', 'is_active',
            'is_verified', 'created_at', 'logo_url', 'theme_color'
        ]
        read_only_fields = ['id', 'created_at']


class TenantMembershipSerializer(serializers.ModelSerializer):
    """Serializer for TenantMembership model"""
    
    user = UserSerializer(read_only=True)
    tenant = TenantSerializer(read_only=True)
    
    class Meta:
        model = TenantMembership
        fields = [
            'id', 'user', 'tenant', 'role', 'is_active',
            'joined_at', 'can_invite_users', 'can_manage_settings',
            'can_view_analytics'
        ]
        read_only_fields = ['id', 'joined_at']


class TenantOAuthConfigSerializer(serializers.ModelSerializer):
    """Serializer for TenantOAuthConfig model (without secrets)"""
    
    class Meta:
        model = TenantOAuthConfig
        fields = [
            'id', 'provider', 'client_id', 'redirect_uri',
            'provider_tenant_id', 'scopes', 'allowed_domains',
            'is_active', 'auto_create_users', 'require_email_verification',
            'last_used', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_used']


class TenantOAuthConfigCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating TenantOAuthConfig (with secrets)"""
    
    class Meta:
        model = TenantOAuthConfig
        fields = [
            'provider', 'client_id', 'client_secret', 'redirect_uri',
            'provider_tenant_id', 'scopes', 'allowed_domains',
            'auto_create_users', 'require_email_verification'
        ]


class TenantOAuthUserSerializer(serializers.ModelSerializer):
    """Serializer for TenantOAuthUser model (without tokens)"""
    
    user = UserSerializer(read_only=True)
    oauth_config = TenantOAuthConfigSerializer(read_only=True)
    
    class Meta:
        model = TenantOAuthUser
        fields = [
            'id', 'user', 'oauth_config', 'provider_user_id',
            'provider_email', 'is_active', 'last_login',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login data"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserRegisterSerializer(serializers.Serializer):
    """Serializer for user registration data"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    name = serializers.CharField(max_length=255)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return data


class TenantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new tenant"""
    
    class Meta:
        model = Tenant
        fields = [
            'name', 'subdomain', 'domain', 'contact_email',
            'contact_phone', 'address', 'logo_url', 'theme_color'
        ]


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    token = serializers.CharField()
    password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField()
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    current_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField()
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return data
