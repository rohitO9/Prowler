from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from api.decorators import require_tenant, require_tenant_admin
from api.models import Resource
from api.serializers import ResourceSerializer
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_tenant  # ✅ Ensures tenant context exists
def list_resources(request):
    """
    List all resources for current tenant
    GET /api/v1/resources
    """
    # ✅ Filter by tenant automatically
    resources = Resource.objects.filter(tenant=request.tenant)
    
    serializer = ResourceSerializer(resources, many=True)
    
    return Response({
        'data': serializer.data,
        'meta': {
            'tenant': request.tenant.subdomain,
            'count': resources.count(),
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_tenant
def create_resource(request):
    """
    Create new resource for current tenant
    POST /api/v1/resources
    """
    serializer = ResourceSerializer(data=request.data)
    
    if serializer.is_valid():
        # ✅ Automatically set tenant
        resource = serializer.save(tenant=request.tenant)
        
        logger.info(
            f"Resource created: {resource.id} by {request.user.email} "
            f"in tenant {request.tenant.subdomain}"
        )
        
        return Response({
            'data': ResourceSerializer(resource).data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_tenant
def get_resource(request, resource_id):
    """
    Get single resource by ID
    GET /api/v1/resources/{id}
    """
    try:
        # ✅ CRITICAL: Filter by tenant to prevent access to other tenants' resources
        resource = Resource.objects.get(
            id=resource_id,
            tenant=request.tenant  # This prevents cross-tenant access!
        )
    except Resource.DoesNotExist:
        return Response({
            'errors': [{
                'status': '404',
                'code': 'resource_not_found',
                'title': 'Not Found',
                'detail': f'Resource {resource_id} not found in your organization',
            }]
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = ResourceSerializer(resource)
    return Response({'data': serializer.data})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@require_tenant_admin  # ✅ Only admins can delete
def delete_resource(request, resource_id):
    """
    Delete resource (admin only)
    DELETE /api/v1/resources/{id}
    """
    try:
        resource = Resource.objects.get(
            id=resource_id,
            tenant=request.tenant
        )
    except Resource.DoesNotExist:
        return Response({
            'errors': [{
                'status': '404',
                'code': 'resource_not_found',
                'title': 'Not Found',
                'detail': 'Resource not found',
            }]
        }, status=status.HTTP_404_NOT_FOUND)
    
    resource.delete()
    
    logger.info(
        f"Resource deleted: {resource_id} by {request.user.email} "
        f"in tenant {request.tenant.subdomain}"
    )
    
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_tenant
def list_users(request):
    """
    List all users in current tenant
    GET /api/v1/users
    """
    from api.models import User
    from api.serializers import UserSerializer
    
    # ✅ Only users in this tenant
    users = User.objects.filter(primary_tenant=request.tenant)
    
    serializer = UserSerializer(users, many=True)
    
    return Response({
        'data': serializer.data,
        'meta': {
            'tenant': request.tenant.subdomain,
            'count': users.count(),
        }
    })
