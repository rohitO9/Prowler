from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.decorators import require_tenant


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_tenant
def get_current_user(request):
    """
    Get current authenticated user
    GET /api/v1/users/me
    """
    from api.serializers import UserSerializer
    
    # ✅ Validate user belongs to request tenant
    if request.user.primary_tenant_id != request.tenant.id:
        return Response({
            'errors': [{
                'status': '403',
                'code': 'tenant_mismatch',
                'title': 'Access Denied',
                'detail': 'You do not belong to this organization',
            }]
        }, status=403)
    
    serializer = UserSerializer(request.user)
    
    return Response({
        'data': {
            'type': 'users',
            'id': str(request.user.id),
            'attributes': serializer.data,
            'relationships': {
                'tenant': {
                    'data': {
                        'type': 'tenants',
                        'id': str(request.tenant.id),
                        'attributes': {
                            'name': request.tenant.name,
                            'subdomain': request.tenant.subdomain,
                        }
                    }
                }
            }
        }
    })
