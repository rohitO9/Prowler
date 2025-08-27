import logging
from django.conf import settings
from django.contrib.auth import get_user_model, logout as django_logout
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import requests
import jwt
from datetime import datetime, timedelta
from django.views import View
from django.http import HttpResponseRedirect
from urllib.parse import urlencode

from api.models import Tenant
# from api.v1.models.azure_ad import AzureADUserProfile  # Temporarily disabled
from api.v1.serializers import UserSerializer
from api.v1.utils.azure_ad_utils import AzureADUtils
from api.models import Membership


logger = logging.getLogger(__name__)
User = get_user_model()


class AzureADSocialLoginView(TokenObtainPairView):
    """
    Azure AD OAuth2 authentication endpoint.
    Handles Azure AD authentication and user creation/retrieval.
    """
    resource_name = 'token'
    permission_classes = [AllowAny]
    parser_classes = [
        JSONParser,
        FormParser,
        MultiPartParser,
    ]

    def post(self, request, *args, **kwargs):
        try:
            # Debug: Log the request data
            logger.info(f"Request data: {request.data}")
            logger.info(f"Request content type: {request.content_type}")
            
            # Get the authorization code from request
            auth_code = request.data.get('code')
            logger.info(f"Authorization code: {auth_code[:50] if auth_code else 'None'}...")
            
            if not auth_code:
                return Response(
                    {'error': 'Authorization code is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Exchange authorization code for access token
            token_data = self._exchange_code_for_token(auth_code)
            if not token_data or 'access_token' not in token_data:
                return Response(
                    {'error': 'Failed to exchange authorization code for token'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            access_token_azure = token_data['access_token']

            # Get user info from Azure AD
            user_info = self._get_user_info(access_token_azure)
            if not user_info:
                return Response(
                    {'error': 'Failed to get user information from Azure AD'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create or get user
            user = self._get_or_create_user(user_info)
            if not user:
                return Response(
                    {'error': 'Failed to create or retrieve user'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Detect or create tenant from Azure AD
            tenant = self._get_or_create_tenant_from_azure(user_info, access_token_azure)
            
            # Create user membership in tenant
            if tenant:
                self._ensure_user_membership(user, tenant)
            
            # Optional: sync groups to roles
            AzureADUtils.sync_user_groups(user, access_token_azure)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # Set tenant context in JWT token
            if tenant:
                access_token['tenant_id'] = str(tenant.id)
                access_token['tenant_name'] = tenant.name
                access_token['user_tenant_role'] = 'member'  # Default role
                
                # Get user's role in this tenant
                try:
                    membership = Membership.objects.get(user=user, tenant=tenant)
                    access_token['user_tenant_role'] = membership.role
                except Membership.DoesNotExist:
                    pass
            
            # Add trial information to JWT token
            access_token['trial_start'] = user.trial_start.isoformat() if user.trial_start else None
            access_token['trial_end'] = user.trial_end.isoformat() if user.trial_end else None
            access_token['is_trial_active'] = user.is_trial_active
            access_token['trial_days_remaining'] = self._calculate_trial_days_remaining(user)

            serialized_user = UserSerializer(user).data

            return Response(
                data={
                    "access": str(access_token),
                    "refresh": str(refresh),
                    "user": serialized_user,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Azure AD authentication error: {str(e)}")
            return Response(
                {'error': 'Authentication failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _exchange_code_for_token(self, auth_code):
        """Exchange authorization code for access token"""
        try:
            # Debug: Log Azure AD settings
            logger.info(f"AZURE_AD_TENANT_ID: {getattr(settings, 'AZURE_AD_TENANT_ID', 'NOT_SET')}")
            logger.info(f"AZURE_AD_CLIENT_ID: {getattr(settings, 'AZURE_AD_CLIENT_ID', 'NOT_SET')}")
            logger.info(f"AZURE_AD_CLIENT_SECRET: {'SET' if getattr(settings, 'AZURE_AD_CLIENT_SECRET', None) else 'NOT_SET'}")
            logger.info(f"AZURE_AD_REDIRECT_URI: {getattr(settings, 'AZURE_AD_REDIRECT_URI', 'NOT_SET')}")
            
            token_url = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/oauth2/v2.0/token"
            logger.info(f"Token URL: {token_url}")
            
            data = {
                'client_id': settings.AZURE_AD_CLIENT_ID,
                'client_secret': settings.AZURE_AD_CLIENT_SECRET,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': settings.AZURE_AD_REDIRECT_URI,
                'scope': 'openid profile email'
            }
            logger.info(f"Token exchange data: {data}")

            response = requests.post(token_url, data=data)
            logger.info(f"Token exchange response status: {response.status_code}")
            logger.info(f"Token exchange response: {response.text[:200]}...")
            
            response.raise_for_status()
            
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Token exchange error: {str(e)}")
            return None

    def _get_user_info(self, access_token):
        """Get user information from Azure AD"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers=headers
            )
            response.raise_for_status()
            
            return response.json()
        except requests.RequestException as e:
            logger.error(f"User info error: {str(e)}")
            return None

    def _get_or_create_user(self, user_info):
        """Create or retrieve user based on Azure AD information."""
        try:
            azure_id = user_info.get('id')
            email = user_info.get('mail') or user_info.get('userPrincipalName')

            if not email:
                logger.error("No email found in Azure AD user info")
                return None

            # Find existing user by email (simplified approach)
            user = User.objects.filter(email=email).first()
            if not user:
                # Compose a reasonable name from Azure info or email local-part
                display_name = user_info.get('displayName')
                if not display_name:
                    given = user_info.get('givenName') or ''
                    surname = user_info.get('surname') or ''
                    display_name = (given + ' ' + surname).strip() or email.split('@')[0]

                # Create user with a random password (Azure AD users don't need local passwords)
                from django.contrib.auth.hashers import make_password
                import secrets
                
                # Generate a random password that will never be used
                random_password = secrets.token_urlsafe(32)
                
                user = User.objects.create(
                    email=email,
                    name=display_name,
                    is_active=True,
                    password=make_password(random_password),  # Required by AbstractBaseUser
                )
                
                # Start 7-day trial for new Azure AD users
                user.start_trial(days=7)
                logger.info(f"Created new user: {email} with 7-day trial")
            else:
                # For existing users, check if they need trial activation
                if not user.trial_start and not user.is_trial_active:
                    user.start_trial(days=7)
                    logger.info(f"Started 7-day trial for existing user: {email}")
                else:
                    # Update trial status for existing users
                    user.check_trial_status()
                    logger.info(f"Retrieved existing user: {email} with trial status: {user.is_trial_active}")

            # Store Azure AD ID in user metadata if needed (optional)
            # For now, we'll just log it
            if azure_id:
                logger.info(f"Azure AD user {azure_id} mapped to Django user {user.id}")

            return user
        except Exception as e:
            logger.error(f"User creation/retrieval error: {str(e)}")
            logger.error(f"User info received: {user_info}")
            return None

    def _get_or_create_tenant_from_azure(self, user_info, access_token_azure):
        """Get or create tenant based on Azure AD information."""
        try:
            # Extract domain from user's email
            email = user_info.get('mail') or user_info.get('userPrincipalName')
            if not email:
                return None
            
            domain = email.split('@')[1] if '@' in email else None
            if not domain:
                return None
            
            # Try to find existing tenant by domain
            tenant = Tenant.objects.filter(name__icontains=domain).first()
            
            if not tenant:
                # Create new tenant based on domain
                tenant_name = f"{domain.title()} Organization"
                tenant = Tenant.objects.create(name=tenant_name)
                logger.info(f"Created new tenant: {tenant_name} for domain: {domain}")
            else:
                logger.info(f"Found existing tenant: {tenant.name} for domain: {domain}")
            
            return tenant
            
        except Exception as e:
            logger.error(f"Tenant creation/retrieval error: {str(e)}")
            return None

    def _ensure_user_membership(self, user, tenant):
        """Ensure user has membership in the tenant."""
        try:
            from api.models import Membership
            
            # Check if membership already exists
            membership = Membership.objects.filter(user=user, tenant=tenant).first()
            
            if not membership:
                # Create membership with default role
                membership = Membership.objects.create(
                    user=user,
                    tenant=tenant,
                    role=Membership.RoleChoices.MEMBER
                )
                logger.info(f"Created membership for user {user.email} in tenant {tenant.name}")
            else:
                logger.info(f"Membership already exists for user {user.email} in tenant {tenant.name}")
            
            return membership
            
        except Exception as e:
            logger.error(f"Membership creation error: {str(e)}")
            return None

    def _calculate_trial_days_remaining(self, user):
        """Calculate remaining trial days for user."""
        try:
            if not user.trial_end or not user.is_trial_active:
                return 0
            
            from django.utils import timezone
            now = timezone.now()
            
            if now > user.trial_end:
                return 0
            
            remaining = user.trial_end - now
            return max(0, remaining.days)
            
        except Exception as e:
            logger.error(f"Error calculating trial days remaining: {str(e)}")
            return 0


class AzureLoginView(View):
    def get(self, request):
        query = {
            "client_id": settings.AZURE_AD_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.AZURE_AD_REDIRECT_URI,
            "response_mode": "query",
            "scope": " ".join(settings.AZURE_AD_SCOPES),
            "state": "optional-csrf",
            "prompt": "select_account",
        }
        url = f"{settings.AZURE_AD_AUTHORITY}/oauth2/v2.0/authorize?{urlencode(query)}"
        return HttpResponseRedirect(url)


class AzureCallbackView(View):
    def get(self, request):
        code = request.GET.get("code")
        if not code:
            return JsonResponse({"detail": "Missing code"}, status=400)

        token_url = f"{settings.AZURE_AD_AUTHORITY}/oauth2/v2.0/token"
        data = {
            "client_id": settings.AZURE_AD_CLIENT_ID,
            "client_secret": settings.AZURE_AD_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.AZURE_AD_REDIRECT_URI,
        }
        resp = requests.post(token_url, data=data)
        if not resp.ok:
            return JsonResponse({"detail": "Token exchange failed"}, status=400)

        tokens = resp.json()
        access_token_azure = tokens.get("access_token")
        user_info_resp = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token_azure}"},
        )
        if not user_info_resp.ok:
            return JsonResponse({"detail": "Failed to load user info"}, status=400)

        info = user_info_resp.json()
        view = AzureADSocialLoginView()
        user = view._get_or_create_user(info)
        if not user:
            return JsonResponse({"detail": "Failed to create user"}, status=500)

        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        serialized_user = UserSerializer(user).data
        return JsonResponse(
            {"access": str(access_token), "refresh": str(refresh), "user": serialized_user}
        )


class AzureLogoutView(View):
    def post(self, request):
        try:
            django_logout(request)
        except Exception:
            pass
        return JsonResponse({"detail": "Logged out"})


@api_view(['GET'])
@permission_classes([AllowAny])
def azure_ad_config(request):
    """
    Return Azure AD configuration for frontend
    """
    return Response({
        'client_id': settings.AZURE_AD_CLIENT_ID,
        'tenant_id': settings.AZURE_AD_TENANT_ID,
        'redirect_uri': settings.AZURE_AD_REDIRECT_URI,
        'authority': f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}",
        'scopes': list(getattr(settings, 'AZURE_AD_SCOPES', ['openid', 'profile', 'email']))
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def trial_status(request):
    """
    Check trial status for a user (for testing purposes)
    """
    try:
        email = request.GET.get('email')
        if not email:
            return Response(
                {'error': 'Email parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check trial status
        user.check_trial_status()
        
        return Response({
            'user_email': user.email,
            'trial_start': user.trial_start.isoformat() if user.trial_start else None,
            'trial_end': user.trial_end.isoformat() if user.trial_end else None,
            'is_trial_active': user.is_trial_active,
            'trial_days_remaining': max(0, (user.trial_end - timezone.now()).days) if user.trial_end and user.is_trial_active else 0
        })
        
    except Exception as e:
        logger.error(f"Trial status check error: {str(e)}")
        return Response(
            {'error': f'Trial status check failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def azure_ad_test(request):
    """
    Test Azure AD authentication without database dependencies
    """
    # Set parser classes for this function
    from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
    request.parsers = [JSONParser(), FormParser(), MultiPartParser()]
    
    try:
        # Debug: Log the request data
        logger.info(f"Test endpoint - Request data: {request.data}")
        logger.info(f"Test endpoint - Request content type: {request.content_type}")
        
        # Check if request.data is empty (parsing issue)
        if not request.data:
            logger.error("Request data is empty - JSON parsing issue")
            return Response(
                {'error': 'Request data is empty. Make sure to send JSON with Content-Type: application/json'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        auth_code = request.data.get('code')
        if not auth_code:
            return Response(
                {'error': 'Authorization code is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"Testing Azure AD with code: {auth_code[:50]}...")
        
        # Create a temporary view instance to use its methods
        temp_view = AzureADSocialLoginView()
        
        # Test token exchange
        token_data = temp_view._exchange_code_for_token(auth_code)
        if not token_data or 'access_token' not in token_data:
            return Response(
                {'error': 'Failed to exchange authorization code for token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        access_token_azure = token_data['access_token']
        logger.info("✅ Token exchange successful")
        
        # Test user info retrieval
        user_info = temp_view._get_user_info(access_token_azure)
        if not user_info:
            return Response(
                {'error': 'Failed to get user information from Azure AD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"✅ User info retrieved: {user_info.get('mail', 'No email')}")
        
        # Return success without creating database user
        return Response({
            'status': 'success',
            'message': 'Azure AD authentication test successful',
            'user_info': {
                'email': user_info.get('mail') or user_info.get('userPrincipalName'),
                'name': user_info.get('displayName'),
                'azure_id': user_info.get('id')
            },
            'trial_info': {
                'trial_duration_days': 7,
                'note': 'New users get 7-day trial automatically'
            },
            'note': 'User not created in database (test mode)'
        })
        
    except Exception as e:
        logger.error(f"Azure AD test error: {str(e)}")
        return Response(
            {'error': f'Test failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )