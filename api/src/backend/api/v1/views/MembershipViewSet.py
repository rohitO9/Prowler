from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

class MembershipViewSet(ViewSet):
    def list(self, request):
        return Response({"message": "MembershipViewSet list"})
