"""
SCIM 2.0 API Views for Azure AD Integration
"""

import logging
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError

from api.v1.authentication.scim_auth import SCIMTokenAuthentication
from api.services.azure_scim_service import AzureSCIMService

logger = logging.getLogger(__name__)


@api_view(['GET'])
@authentication_classes([SCIMTokenAuthentication])
@permission_classes([AllowAny])
def scim_list_users(request):
    """
    GET /scim/v2/Users
    List users for SCIM provisioning
    """
    try:
        tenant = request.user  # From SCIMTokenAuthentication
        
        # Get query parameters
        start_index = int(request.GET.get('startIndex', 1))
        count = int(request.GET.get('count', 100))
        filter_param = request.GET.get('filter', '')
        
        # Get users for tenant
        from api.models import User
        users = User.objects.filter(
            tenant_memberships__tenant=tenant,
            is_sso_user=True,
            is_active=True
        ).distinct()
        
        # Apply filter if provided
        if filter_param and 'userName eq' in filter_param:
            email = filter_param.split('"')[1]
            users = users.filter(email=email)
        
        total_results = users.count()
        users = users[start_index-1:start_index+count-1]
        
        # Format users for SCIM response
        scim_service = AzureSCIMService(tenant)
        resources = []
        for user in users:
            resources.append(scim_service._format_scim_user(user))
        
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": total_results,
            "startIndex": start_index,
            "itemsPerPage": count,
            "Resources": resources
        })
        
    except Exception as e:
        logger.error(f"SCIM list users error: {e}")
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "500",
            "detail": str(e)
        }, status=500)


@api_view(['POST'])
@authentication_classes([SCIMTokenAuthentication])
@permission_classes([AllowAny])
def scim_create_user(request):
    """
    POST /scim/v2/Users
    Create user via SCIM provisioning
    """
    try:
        tenant = request.user
        scim_service = AzureSCIMService(tenant)
        
        user = scim_service.handle_user_create(request.data)
        
        return Response(scim_service._format_scim_user(user), status=201)
        
    except Exception as e:
        logger.error(f"SCIM create user error: {e}")
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "500",
            "detail": str(e)
        }, status=500)


@api_view(['GET'])
@authentication_classes([SCIMTokenAuthentication])
@permission_classes([AllowAny])
def scim_get_user(request, azure_user_id):
    """
    GET /scim/v2/Users/{azure_user_id}
    Get user by Azure AD ID
    """
    try:
        tenant = request.user
        
        from api.models import User
        user = User.objects.get(
            azure_id=azure_user_id,
            primary_tenant=tenant,
            is_sso_user=True
        )
        
        scim_service = AzureSCIMService(tenant)
        return Response(scim_service._format_scim_user(user))
        
    except User.DoesNotExist:
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "404",
            "detail": "User not found"
        }, status=404)
    except Exception as e:
        logger.error(f"SCIM get user error: {e}")
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "500",
            "detail": str(e)
        }, status=500)


@api_view(['PATCH'])
@authentication_classes([SCIMTokenAuthentication])
@permission_classes([AllowAny])
def scim_update_user(request, azure_user_id):
    """
    PATCH /scim/v2/Users/{azure_user_id}
    Update user via SCIM provisioning
    """
    try:
        tenant = request.user
        scim_service = AzureSCIMService(tenant)
        
        user = scim_service.handle_user_update(azure_user_id, request.data)
        
        return Response(scim_service._format_scim_user(user))
        
    except ValueError as e:
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "404",
            "detail": str(e)
        }, status=404)
    except Exception as e:
        logger.error(f"SCIM update user error: {e}")
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "500",
            "detail": str(e)
        }, status=500)


@api_view(['DELETE'])
@authentication_classes([SCIMTokenAuthentication])
@permission_classes([AllowAny])
def scim_delete_user(request, azure_user_id):
    """
    DELETE /scim/v2/Users/{azure_user_id}
    Delete user via SCIM provisioning
    """
    try:
        tenant = request.user
        scim_service = AzureSCIMService(tenant)
        
        scim_service.handle_user_delete(azure_user_id)
        
        return Response(status=204)
        
    except ValueError as e:
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "404",
            "detail": str(e)
        }, status=404)
    except Exception as e:
        logger.error(f"SCIM delete user error: {e}")
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "500",
            "detail": str(e)
        }, status=500)


@api_view(['GET'])
@authentication_classes([SCIMTokenAuthentication])
@permission_classes([AllowAny])
def scim_service_provider_config(request):
    """
    GET /scim/v2/ServiceProviderConfig
    SCIM service provider configuration
    """
    return Response({
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "patch": {
            "supported": True
        },
        "bulk": {
            "supported": False,
            "maxOperations": 0,
            "maxPayloadSize": 0
        },
        "filter": {
            "supported": True,
            "maxResults": 200
        },
        "changePassword": {
            "supported": False
        },
        "sort": {
            "supported": False
        },
        "etag": {
            "supported": False
        },
        "authenticationSchemes": [
            {
                "name": "OAuth Bearer Token",
                "description": "Authentication scheme using the OAuth Bearer Token Standard",
                "specUri": "http://www.rfc-editor.org/info/rfc6750",
                "type": "oauthbearertoken",
                "primary": True
            }
        ]
    })
