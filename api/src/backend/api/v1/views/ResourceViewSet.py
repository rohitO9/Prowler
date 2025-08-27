from api.base_views import BaseRLSViewSet
from api.models import Resource
from api.v1.serializers import ResourceSerializer


class ResourceViewSet(BaseRLSViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    filterset_fields = [
        "provider",
        "region",
        "service",
        "type",
    ]
    search_fields = ["uid", "name", "region", "service", "type"]

    def set_required_permissions(self):
        self.required_permissions = []

    def get_queryset(self):
        return Resource.objects.all()
