from api.base_views import BaseRLSViewSet
from api.models import Scan
from api.v1.serializers import (
    ScanSerializer,
    ScanCreateSerializer,
    ScanUpdateSerializer,
)


class ScanViewSet(BaseRLSViewSet):
    queryset = Scan.objects.all()
    serializer_class = ScanSerializer

    filterset_fields = ["provider", "state", "trigger"]
    search_fields = ["name"]

    def set_required_permissions(self):
        self.required_permissions = ["manage_scans"]

    def get_queryset(self):
        return Scan.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return ScanCreateSerializer
        if self.action in ["update", "partial_update"]:
            return ScanUpdateSerializer
        return ScanSerializer
