from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from api.base_views import BaseUserViewset
from api.models import User
from api.v1.serializers import UserSerializer, UserCreateSerializer, UserUpdateSerializer

class UserViewSet(BaseUserViewset):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    filterset_fields = ["email", "company_name", "is_active"]
    search_fields = ["name", "email", "company_name"]

    def set_required_permissions(self):
        self.required_permissions = ["manage_users"]

    def get_queryset(self):
        return User.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        # Allow anonymous user registration
        if self.action == "create":
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
