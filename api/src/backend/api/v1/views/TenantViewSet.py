from api.base_views import BaseTenantViewset
from api.models import Tenant
from api.v1.serializers import TenantSerializer


class TenantViewSet(BaseTenantViewset):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer

    filterset_fields = ["name"]
    search_fields = ["name"]


    def set_required_permissions(self):
        self.required_permissions = ["manage_account"]

    def get_queryset(self):
        return Tenant.objects.all()
