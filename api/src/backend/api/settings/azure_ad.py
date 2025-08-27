"""
Azure AD Configuration Settings
"""

import os
from typing import List

# Azure AD Application Settings
AZURE_AD_CLIENT_ID = os.getenv('AZURE_AD_CLIENT_ID', '')
AZURE_AD_CLIENT_SECRET = os.getenv('AZURE_AD_CLIENT_SECRET', '')
AZURE_AD_TENANT_ID = os.getenv('AZURE_AD_TENANT_ID', '')
AZURE_AD_REDIRECT_URI = os.getenv('AZURE_AD_REDIRECT_URI', 'http://localhost:3000/auth/callback/azure')

# Azure AD Graph API Settings
AZURE_AD_GRAPH_API_VERSION = 'v1.0'
AZURE_AD_GRAPH_API_BASE_URL = 'https://graph.microsoft.com'

# Azure AD Authentication Settings
AZURE_AD_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_AD_TENANT_ID}"
AZURE_AD_SCOPES = ['openid', 'profile', 'email', 'User.Read']

# Azure AD Token Settings
AZURE_AD_TOKEN_EXPIRY_BUFFER = 300  # 5 minutes buffer for token expiry

# Azure AD User Mapping Settings
AZURE_AD_USER_MAPPING = {
    'id': 'azure_ad_id',
    'mail': 'email',
    'userPrincipalName': 'email',
    'givenName': 'first_name',
    'surname': 'last_name',
    'displayName': 'full_name',
}

# Azure AD Group Mapping (for role assignment)
AZURE_AD_GROUP_MAPPING = {
    'admin_group_id': os.getenv('AZURE_AD_ADMIN_GROUP_ID', ''),
    'user_group_id': os.getenv('AZURE_AD_USER_GROUP_ID', ''),
}

# Azure AD Feature Flags
AZURE_AD_ENABLED = os.getenv('AZURE_AD_ENABLED', 'False').lower() == 'true'
AZURE_AD_AUTO_CREATE_USERS = os.getenv('AZURE_AD_AUTO_CREATE_USERS', 'True').lower() == 'true'
AZURE_AD_SYNC_GROUPS = os.getenv('AZURE_AD_SYNC_GROUPS', 'False').lower() == 'true'

# Azure AD Logging
AZURE_AD_LOG_LEVEL = os.getenv('AZURE_AD_LOG_LEVEL', 'INFO')

# Azure AD Security Settings
AZURE_AD_REQUIRE_EMAIL_VERIFICATION = os.getenv('AZURE_AD_REQUIRE_EMAIL_VERIFICATION', 'False').lower() == 'true'
AZURE_AD_ALLOWED_DOMAINS = os.getenv('AZURE_AD_ALLOWED_DOMAINS', '').split(',') if os.getenv('AZURE_AD_ALLOWED_DOMAINS') else []

# Azure AD Session Settings
AZURE_AD_SESSION_TIMEOUT = int(os.getenv('AZURE_AD_SESSION_TIMEOUT', '3600'))  # 1 hour default
AZURE_AD_REFRESH_TOKEN_EXPIRY = int(os.getenv('AZURE_AD_REFRESH_TOKEN_EXPIRY', '2592000'))  # 30 days default

# Azure AD Error Messages
AZURE_AD_ERROR_MESSAGES = {
    'invalid_code': 'Invalid authorization code provided',
    'token_exchange_failed': 'Failed to exchange authorization code for token',
    'user_info_failed': 'Failed to retrieve user information from Azure AD',
    'user_creation_failed': 'Failed to create or retrieve user account',
    'domain_not_allowed': 'Your email domain is not allowed to access this application',
    'email_not_verified': 'Email verification is required for Azure AD users',
    'group_sync_failed': 'Failed to sync user groups from Azure AD',
} 