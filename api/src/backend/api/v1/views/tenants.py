from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import Tenant
from .serializers import TenantSerializer, InvitationSerializer

class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer

    @action(detail=True, methods=['post'])
    def invitations(self, request, pk=None):
        tenant = self.get_object()
        serializer = InvitationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(tenant=tenant, invited_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)