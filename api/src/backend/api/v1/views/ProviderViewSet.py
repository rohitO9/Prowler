from api.base_views import BaseRLSViewSet
from api.models import Provider
from api.v1.serializers import (
    ProviderSerializer,
    ProviderCreateSerializer,
    ProviderUpdateSerializer,
)


class ProviderViewSet(BaseRLSViewSet):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer

    filterset_fields = ["provider", "uid", "alias", "connected"]
    search_fields = ["uid", "alias"]

    def set_required_permissions(self):
        self.required_permissions = ["manage_providers"]

    def get_queryset(self):
        return Provider.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return ProviderCreateSerializer
        if self.action in ["update", "partial_update"]:
            return ProviderUpdateSerializer
        return ProviderSerializer
