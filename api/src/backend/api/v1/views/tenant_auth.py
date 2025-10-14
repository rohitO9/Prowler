from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from api.models import Tenant, User, TenantMembership
import logging

logger = logging.getLogger(__name__)


def get_tokens_for_user(user, tenant):
    """
    Generate JWT tokens with tenant information
    """
    refresh = RefreshToken.for_user(user)
    
    # ✅ Add tenant claims to JWT
    refresh['tenant_id'] = str(tenant.id)
    refresh['tenant_name'] = tenant.name
    refresh['tenant_subdomain'] = tenant.subdomain
    
    # ✅ Add user metadata
    refresh['email'] = user.email
    refresh['is_admin'] = user.is_staff or user.is_superuser
    
    # ✅ Add tenant-specific permissions (future)
    # refresh['permissions'] = get_user_permissions(user, tenant)
    
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def tenant_login(request):
    """
    Login user to specific tenant
    POST /api/v1/tenant/login
    
    Required in subdomain context (e.g., company1.localhost)
    """
    try:
        # Get tenant from subdomain (set by middleware)
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            # Try to extract from request data as fallback
            data = request.data.get('data', {})
            attributes = data.get('attributes', {})
            tenant_subdomain = attributes.get('tenant_subdomain')
            
            if tenant_subdomain:
                try:
                    tenant = Tenant.objects.get(
                        subdomain=tenant_subdomain,
                        is_active=True
                    )
                except Tenant.DoesNotExist:
                    return Response({
                        'errors': [{
                            'status': '404',
                            'code': 'tenant_not_found',
                            'title': 'Tenant Not Found',
                            'detail': f'Organization "{tenant_subdomain}" not found',
                        }]
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    'errors': [{
                        'status': '400',
                        'code': 'missing_tenant',
                        'title': 'Tenant Required',
                        'detail': 'Please access via your organization subdomain',
                    }]
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get credentials
        data = request.data.get('data', {})
        attributes = data.get('attributes', {})
        email = attributes.get('email', '').strip()
        password = attributes.get('password')
        
        if not email or not password:
            return Response({
                'errors': [{
                    'status': '400',
                    'code': 'missing_credentials',
                    'title': 'Missing Credentials',
                    'detail': 'Email and password are required',
                }]
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"Login attempt for {email} on tenant {tenant.subdomain}")
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        
        if not user:
            logger.warning(f"Failed login attempt for {email} on tenant {tenant.subdomain}")
            return Response({
                'errors': [{
                    'status': '401',
                    'code': 'invalid_credentials',
                    'title': 'Invalid Credentials',
                    'detail': 'Email or password is incorrect',
                }]
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # ✅ CRITICAL: Verify user belongs to this tenant
        if user.primary_tenant_id != tenant.id:
            logger.error(
                f"🚨 SECURITY: User {email} (tenant: {user.primary_tenant.subdomain}) "
                f"attempted login to {tenant.subdomain}"
            )
            return Response({
                'errors': [{
                    'status': '403',
                    'code': 'wrong_tenant',
                    'title': 'Access Denied',
                    'detail': f'You do not have access to {tenant.name}. Please use your organization\'s subdomain.',
                    'meta': {
                        'your_tenant': user.primary_tenant.subdomain,
                        'your_tenant_url': f'http://{user.primary_tenant.subdomain}.localhost:3000',
                    }
                }]
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if user is active
        if not user.is_active:
            return Response({
                'errors': [{
                    'status': '403',
                    'code': 'user_inactive',
                    'title': 'Account Inactive',
                    'detail': 'Your account has been deactivated',
                }]
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate tokens
        tokens = get_tokens_for_user(user, tenant)
        
        logger.info(f"✅ Successful login: {email} on tenant {tenant.subdomain}")
        
        # Return JSON:API format
        return Response({
            'data': {
                'type': 'authentication',
                'id': str(user.id),
                'attributes': {
                    'access_token': tokens['access'],
                    'refresh_token': tokens['refresh'],
                    'token_type': 'Bearer',
                }
            },
            'included': [{
                'type': 'users',
                'id': str(user.id),
                'attributes': {
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_active': user.is_active,
                }
            }, {
                'type': 'tenants',
                'id': str(tenant.id),
                'attributes': {
                    'name': tenant.name,
                    'subdomain': tenant.subdomain,
                }
            }]
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return Response({
            'errors': [{
                'status': '500',
                'code': 'server_error',
                'title': 'Server Error',
                'detail': 'An unexpected error occurred during login',
            }]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def tenant_register(request):
    """
    Register new tenant with initial user
    POST /api/v1/tenant/register
    
    Creates both tenant and user in atomic transaction
    """
    try:
        # Debug: Log the raw request data
        logger.info(f"Raw request data: {request.data}")
        
        # Handle both nested and flat data formats
        if 'data' in request.data and isinstance(request.data.get('data'), dict):
            # Nested format: {data: {attributes: {...}}}
            data = request.data.get('data', {})
            attributes = data.get('attributes', {})
        else:
            # Flat format: {company_name: ..., email: ..., etc.}
            attributes = request.data
        
        # Debug: Log parsed data
        logger.info(f"Parsed attributes: {attributes}")
        
        # Extract registration data
        email = attributes.get('email', '').strip()
        password = attributes.get('password')
        first_name = attributes.get('first_name', '').strip()
        last_name = attributes.get('last_name', '').strip()
        
        # Get subdomain from request payload (sent by frontend)
        subdomain = attributes.get('subdomain', '').strip().lower()
        logger.info(f"🔍 [TENANT_REGISTER] Subdomain from payload: {subdomain}")
        
        # Fallback: try to auto-detect from request host if not provided
        if not subdomain:
            host = request.META.get('HTTP_HOST', '')
            logger.info(f"🔍 [TENANT_REGISTER] HTTP_HOST fallback: {host}")
            if '.localhost' in host:
                subdomain = host.split('.')[0].lower()
                logger.info(f"✅ Auto-detected subdomain from host: {subdomain}")
        
        # Debug: Log extracted values
        logger.info(f"Extracted values: subdomain={subdomain}, email={email}, password={'***' if password else None}, first_name={first_name}, last_name={last_name}")
        
        # Validation
        errors = []
        
        if not subdomain:
            errors.append({'field': 'subdomain', 'message': 'Subdomain is required - please access via tenant subdomain (e.g., company1.localhost:3000)'})
        elif not subdomain.replace('-', '').isalnum():
            errors.append({'field': 'subdomain', 'message': 'Subdomain can only contain letters, numbers, and hyphens'})
        
        if not email:
            errors.append({'field': 'email', 'message': 'Email is required'})
        
        if not password or len(password) < 8:
            errors.append({'field': 'password', 'message': 'Password must be at least 8 characters'})
        
        if not first_name:
            errors.append({'field': 'first_name', 'message': 'First name is required'})
        
        if not last_name:
            errors.append({'field': 'last_name', 'message': 'Last name is required'})
        
        if errors:
            return Response({
                'errors': [{
                    'status': '400',
                    'code': 'validation_error',
                    'title': 'Validation Error',
                    'detail': 'Please correct the errors below',
                    'meta': {'field_errors': errors}
                }]
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if tenant already exists
        existing_tenant = Tenant.objects.filter(subdomain=subdomain).first()
        
        if existing_tenant:
            # CASE 1: Tenant exists - register user to existing tenant
            logger.info(f"Tenant exists: {existing_tenant.name} ({subdomain}) - registering user")
            
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                return Response({
                    'errors': [{
                        'status': '409',
                        'code': 'user_exists',
                        'title': 'User Already Exists',
                        'detail': 'A user with this email already exists',
                    }]
                }, status=status.HTTP_409_CONFLICT)
            
            # Create user and assign to existing tenant
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    primary_tenant=existing_tenant,
                    is_active=True
                )
                
                # Create tenant membership
                try:
                    membership = TenantMembership.objects.create(
                        user=user,
                        tenant=existing_tenant,
                        role='member'
                    )
                    logger.info(f"Created TenantMembership: {membership.id} for user {user.email} in tenant {existing_tenant.subdomain}")
                except Exception as e:
                    logger.error(f"Failed to create TenantMembership: {e}")
                    raise e
                
                logger.info(f"Created user: {user.email} for existing tenant {existing_tenant.subdomain}")
                
                # Generate JWT tokens
                tokens = get_tokens_for_user(user, existing_tenant)
                
                return Response({
                    'data': {
                        'type': 'user_registration',
                        'id': str(user.id),
                        'attributes': {
                            'access_token': tokens['access'],
                            'refresh_token': tokens['refresh'],
                            'tenant_subdomain': existing_tenant.subdomain,
                            'redirect_url': f'http://{existing_tenant.subdomain}.localhost:3000/dashboard',
                        }
                    }
                }, status=status.HTTP_201_CREATED)
        else:
            # CASE 2: Tenant doesn't exist - create new tenant with user
            logger.info(f"Creating new tenant: {subdomain}")
            
            # Auto-generate company name from subdomain
            company_name = subdomain.replace('-', ' ').replace('_', ' ').title()
            logger.info(f"Auto-generated company name from subdomain: {company_name}")
        
        # ✅ Check for duplicate user email
        if User.objects.filter(email=email).exists():
            return Response({
                'errors': [{
                    'status': '409',
                    'code': 'email_exists',
                    'title': 'Email Already Registered',
                    'detail': f'An account with email "{email}" already exists',
                }]
            }, status=status.HTTP_409_CONFLICT)
        
        # ✅ Create tenant and user in atomic transaction
        with transaction.atomic():
            # Create tenant
            tenant = Tenant.objects.create(
                name=company_name,
                subdomain=subdomain,
                is_active=True,
            )
            
            logger.info(f"Created tenant: {tenant.name} ({tenant.subdomain})")
            
            # Create user
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                primary_tenant=tenant,
                is_active=True,
            )
            
            logger.info(f"Created user: {user.email} for tenant {tenant.subdomain}")
            
            # Generate tokens for immediate login
            tokens = get_tokens_for_user(user, tenant)
            
            return Response({
                'data': {
                    'type': 'registration',
                    'id': str(tenant.id),
                    'attributes': {
                        'access_token': tokens['access'],
                        'refresh_token': tokens['refresh'],
                        'tenant_subdomain': tenant.subdomain,
                        'redirect_url': f'http://{tenant.subdomain}.localhost:3000/dashboard',
                    }
                },
                'included': [{
                    'type': 'users',
                    'id': str(user.id),
                    'attributes': {
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    }
                }, {
                    'type': 'tenants',
                    'id': str(tenant.id),
                    'attributes': {
                        'name': tenant.name,
                        'subdomain': tenant.subdomain,
                    }
                }]
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        return Response({
            'errors': [{
                'status': '500',
                'code': 'server_error',
                'title': 'Server Error',
                'detail': 'An unexpected error occurred during registration',
            }]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)