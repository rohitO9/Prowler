from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

class OverviewViewSet(ViewSet):
    def list(self, request):
        return Response({"message": "OverviewViewSet list"})
