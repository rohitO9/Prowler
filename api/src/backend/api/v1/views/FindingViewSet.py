from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

class FindingViewSet(ViewSet):
    def list(self, request):
        return Response({"message": "FindingViewSet list"})
