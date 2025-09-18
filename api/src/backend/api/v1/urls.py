from django.urls import include, path
from drf_spectacular.views import SpectacularRedocView
from rest_framework_nested import routers

from api.v1.views import (
    ComplianceOverviewViewSet,
    CustomTokenObtainView,
    CustomTokenRefreshView,
    CustomTokenSwitchTenantView,
    FindingViewSet,
    GithubSocialLoginView,
    GoogleSocialLoginView,
    IntegrationViewSet,
    InvitationAcceptViewSet,
    InvitationViewSet,
    MembershipViewSet,
    OverviewViewSet,
    ProviderGroupProvidersRelationshipView,
    ProviderGroupViewSet,
    ProviderSecretViewSet,
    ProviderViewSet,
    ResourceViewSet,
    RoleProviderGroupRelationshipView,
    RoleViewSet,
    ScanViewSet,
    ScheduleView,
    SchemaView,
    TaskViewSet,
    TenantMembersViewSet,
    TenantViewSet,
    UserRoleRelationshipView,
    UserViewSet,
)
from api.v1.views.trial import TrialViewSet
from api.v1.views.azure_ad import AzureADSocialLoginView, azure_ad_config, AzureLoginView, AzureCallbackView, azure_ad_test, trial_status
from dj_rest_auth.views import PasswordResetConfirmView, PasswordResetView

router = routers.DefaultRouter(trailing_slash=False)

router.register(r"users", UserViewSet, basename="user")
router.register(r"tenants", TenantViewSet, basename="tenant")
router.register(r"providers", ProviderViewSet, basename="provider")
router.register(r"provider-groups", ProviderGroupViewSet, basename="providergroup")
router.register(r"scans", ScanViewSet, basename="scan")
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"resources", ResourceViewSet, basename="resource")
router.register(r"findings", FindingViewSet, basename="finding")
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"trial", TrialViewSet, basename="trial")
router.register(
    r"compliance-overviews", ComplianceOverviewViewSet, basename="complianceoverview"
)
router.register(r"overviews", OverviewViewSet, basename="overview")
router.register(r"schedules", ScheduleView, basename="schedule")
router.register(r"integrations", IntegrationViewSet, basename="integration")

tenants_router = routers.NestedSimpleRouter(router, r"tenants", lookup="tenant")
tenants_router.register(
    r"memberships", TenantMembersViewSet, basename="tenant-membership"
)

users_router = routers.NestedSimpleRouter(router, r"users", lookup="user")
users_router.register(r"memberships", MembershipViewSet, basename="user-membership")

urlpatterns = [
    path("tokens", CustomTokenObtainView.as_view(), name="token-obtain"),
    path("tokens/refresh", CustomTokenRefreshView.as_view(), name="token-refresh"),
    path("tokens/switch", CustomTokenSwitchTenantView.as_view(), name="token-switch"),

    path(
        "auth/password/reset",
        PasswordResetView.as_view(),
        name="auth-password-reset",
    ),
    path(
        "auth/password/reset/confirm",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),

    path(
        "providers/secrets",
        ProviderSecretViewSet.as_view({"get": "list", "post": "create"}),
        name="providersecret-list",
    ),
    path(
        "providers/secrets/<uuid:pk>",
        ProviderSecretViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="providersecret-detail",
    ),

    path(
        "tenants/invitations",
        InvitationViewSet.as_view({"get": "list", "post": "create"}),
        name="invitation-list",
    ),
    path(
        "tenants/invitations/<uuid:pk>",
        InvitationViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="invitation-detail",
    ),

    path(
        "invitations/accept",
        InvitationAcceptViewSet.as_view({"post": "accept"}),
        name="invitation-accept",
    ),

    # Fixed calls for APIViews (removed method dicts)
    path(
        "roles/<uuid:pk>/relationships/provider_groups",
        RoleProviderGroupRelationshipView.as_view(),  # no args
        name="role-provider-groups-relationship",
    ),
    path(
        "users/<uuid:pk>/relationships/roles",
        UserRoleRelationshipView.as_view(),  # no args
        name="user-roles-relationship",
    ),
    path(
        "provider-groups/<uuid:pk>/relationships/providers",
        ProviderGroupProvidersRelationshipView.as_view(),  # no args
        name="provider_group-providers-relationship",
    ),

    path("tokens/google", GoogleSocialLoginView.as_view(), name="token-google"),
    path("tokens/github", GithubSocialLoginView.as_view(), name="token-github"),
    path("tokens/azure", AzureADSocialLoginView.as_view(), name="token-azure"),
    path("tokens/azure/config", azure_ad_config, name="azure-config"),
    path("tokens/azure/test", azure_ad_test, name="azure-test"),
    path("tokens/azure/trial-status", trial_status, name="trial-status"),
    path("auth/azure/login", AzureLoginView.as_view(), name="azure-login"),
    path("auth/azure/callback", AzureCallbackView.as_view(), name="azure-callback"),

    path("", include(router.urls)),
    path("", include(tenants_router.urls)),
    path("", include(users_router.urls)),

    path("schema", SchemaView.as_view(), name="schema"),
    path("docs", SpectacularRedocView.as_view(url_name="schema"), name="docs"),
]
