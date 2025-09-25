from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status

class InvitationViewSet(ViewSet):
    def list(self, request):
        return Response({"message": "InvitationViewSet list"})
    
    def create(self, request):
        return Response(
            {"message": "Create method not implemented yet"}, 
            status=status.HTTP_501_NOT_IMPLEMENTED
        )