from django.contrib import admin
from django.urls import include, path
from django.http import HttpResponseRedirect
from django.utils.http import urlencode

def azure_callback_redirect(request):
    """Redirect Azure callback to the correct endpoint while preserving query parameters"""
    # Get the current query parameters
    query_params = request.GET.urlencode()
    # Build the new URL with query parameters
    new_url = f"/api/v1/auth/azure/callback"
    if query_params:
        new_url += f"?{query_params}"
    return HttpResponseRedirect(new_url)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("api.v1.urls")),
    # Redirect the old Azure callback URL to the correct endpoint
    path("auth/azure/callback", azure_callback_redirect, name="azure-callback-redirect"),
]
