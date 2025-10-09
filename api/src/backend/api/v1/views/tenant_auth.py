"""
Tenant-Aware Authentication Views

This module provides secure, tenant-isolated authentication endpoints.
All authentication is scoped to specific tenants to prevent cross-tenant access.
"""

import logging
from datetime import timedelta
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes, renderer_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework_json_api.renderers import JSONRenderer as JSONAPIRenderer
from rest_framework_json_api.parsers import JSONParser as JSONAPIParser
from rest_framework.response import Response
from rest_framework.views import APIView
import json

from api.models import User, Tenant, TenantMembership


class FlexibleJSONAPIParser(JSONAPIParser):
    """
    Custom JSON API parser that handles type mismatches gracefully.
    """
    def parse(self, stream, media_type=None, parser_context=None):
        try:
            # Try normal JSON API parsing first
            return super().parse(stream, media_type, parser_context)
        except Exception as e:
            if "type" in str(e) and "register_tenant" in str(e):
                # Handle type mismatch by manually parsing and fixing the type
                logger.info("🔄 Handling JSON API type mismatch...")
                try:
                    # Read the stream
                    body = stream.read().decode('utf-8')
                    raw_data = json.loads(body)
                    
                    # Fix the type field
                    if isinstance(raw_data, dict) and 'data' in raw_data:
                        data_obj = raw_data.get('data', {})
                        if data_obj.get('type') == 'register_tenant':
                            data_obj['type'] = 'tenant_register'
                            logger.info("🔄 Fixed type field from 'register_tenant' to 'tenant_register'")
                    
                    # Create a new stream with the fixed data
                    fixed_body = json.dumps(raw_data)
                    from io import BytesIO
                    fixed_stream = BytesIO(fixed_body.encode('utf-8'))
                    
                    # Try parsing again with the fixed data
                    return super().parse(fixed_stream, media_type, parser_context)
                except Exception as fix_error:
                    logger.error(f"❌ Failed to fix JSON API data: {fix_error}")
                    raise e  # Re-raise original error
            else:
                raise e  # Re-raise original error
from api.middleware.tenant_security import (
    require_tenant_access,
    require_tenant_permission,
    TenantValidationMixin
)
from api.serializers import UserSerializer, TenantSerializer
from api.utils.security import (
    generate_secure_token,
    validate_password_strength,
    rate_limit_login_attempts
)

logger = logging.getLogger(__name__)


class TenantLoginView(APIView, TenantValidationMixin):
    """
    Secure tenant-aware login endpoint.
    
    Validates:
    1. Tenant exists and is active
    2. User exists and is active
    3. User belongs to the specified tenant
    4. Password is correct
    5. Account is not locked
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Handle GET requests for login endpoint availability check"""
        return Response({
            'message': 'Login endpoint is available',
            'method': 'POST',
            'description': 'Use POST method with credentials to authenticate'
        }, status=status.HTTP_200_OK)
    
    @method_decorator(csrf_exempt)
    def post(self, request):
        """Handle tenant-aware login"""
        logger.info("🚀 === TENANT LOGIN POST REQUEST START ===")
        logger.info(f"🚀 Request method: {request.method}")
        logger.info(f"🚀 Request content type: {request.content_type}")
        logger.info(f"🚀 Request headers: {dict(request.headers)}")
        logger.info(f"🚀 Request META: {request.META.get('HTTP_HOST', 'No Host')}")
        
        try:
            # Log request data
            try:
                request_data = request.data
                logger.info(f"🚀 Request data: {request_data}")
            except Exception as e:
                logger.error(f"❌ Error reading request data: {e}")
                request_data = {}
            
            # Extract tenant from subdomain
            logger.info("🔍 Extracting tenant from request...")
            tenant = self._get_tenant_from_request(request)
            logger.info(f"🔍 Tenant found: {tenant}")
            
            if not tenant:
                logger.error("❌ No tenant found for request")
                return Response({
                    'error': 'Invalid tenant',
                    'code': 'INVALID_TENANT'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate tenant is active
            logger.info(f"🔍 Validating tenant is active: {tenant.is_active}")
            if not tenant.is_active:
                logger.error("❌ Tenant is inactive")
                return Response({
                    'error': 'Tenant account is inactive',
                    'code': 'TENANT_INACTIVE'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get credentials
            logger.info("🔍 Extracting credentials from request...")
            email = request.data.get('email', '').strip().lower()
            password = request.data.get('password', '')
            tenant_name = request.data.get('tenant_name', '')
            
            logger.info(f"🔍 Credentials extracted - Email: {email}, Password: {'***' if password else 'None'}, Tenant: {tenant_name}")
            
            if not email or not password:
                logger.error("❌ Missing credentials")
                return Response({
                    'error': 'Email and password are required',
                    'code': 'MISSING_CREDENTIALS'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Rate limiting
            logger.info("🔍 Checking rate limiting...")
            if not rate_limit_login_attempts(request, email):
                logger.error("❌ Rate limit exceeded")
                return Response({
                    'error': 'Too many login attempts. Please try again later.',
                    'code': 'RATE_LIMITED'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Authenticate user
            logger.info("🔍 Attempting user authentication...")
            user = authenticate(request, username=email, password=password)
            logger.info(f"🔍 Authentication result: {user}")
            
            if not user:
                logger.error("❌ Authentication failed")
                # Record failed attempt
                try:
                    user_obj = User.objects.get(email=email)
                    user_obj.record_failed_login()
                except User.DoesNotExist:
                    pass  # Don't reveal if user exists
                
                return Response({
                    'error': 'Invalid credentials',
                    'code': 'INVALID_CREDENTIALS'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Check if user is locked
            logger.info(f"🔍 Checking if user is locked: {user.is_locked()}")
            if user.is_locked():
                logger.error("❌ User account is locked")
                return Response({
                    'error': 'Account is temporarily locked due to multiple failed attempts',
                    'code': 'ACCOUNT_LOCKED'
                }, status=status.HTTP_423_LOCKED)
            
            # Validate user belongs to tenant
            logger.info(f"🔍 Checking user access to tenant: {tenant.id}")
            can_access = user.can_access_tenant(tenant.id)
            logger.info(f"🔍 User can access tenant: {can_access}")
            
            if not can_access:
                logger.warning(
                    f"User {user.email} attempted login to unauthorized tenant {tenant.subdomain}"
                )
                return Response({
                    'error': 'Access denied',
                    'code': 'TENANT_ACCESS_DENIED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Record successful login
            logger.info("🔍 Recording successful login...")
            user.record_successful_login(
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Get user's role in tenant
            logger.info("🔍 Getting user membership...")
            membership = TenantMembership.objects.get(
                user=user,
                tenant=tenant,
                is_active=True
            )
            logger.info(f"🔍 Membership found: {membership.role}")
            
            # Generate JWT token with tenant context
            logger.info("🔍 Generating JWT tokens...")
            token_data = {
                'user_id': str(user.id),
                'email': user.email,
                'tenant_id': str(tenant.id),
                'tenant_name': tenant.name,
                'tenant_subdomain': tenant.subdomain,
                'role': membership.role,
                'permissions': {
                    'can_invite_users': membership.can_invite_users,
                    'can_manage_settings': membership.can_manage_settings,
                    'can_view_analytics': membership.can_view_analytics,
                }
            }
            logger.info(f"🔍 Token data: {token_data}")
            
            # Generate access and refresh tokens
            access_token = generate_secure_token(token_data, expires_in=3600)  # 1 hour
            refresh_token = generate_secure_token(
                {'user_id': str(user.id), 'tenant_id': str(tenant.id)},
                expires_in=86400 * 7  # 7 days
            )
            logger.info("🔍 Tokens generated successfully")
            
            response_data = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': 3600,
                'user': UserSerializer(user).data,
                'tenant': TenantSerializer(tenant).data,
                'membership': {
                    'role': membership.role,
                    'permissions': {
                        'can_invite_users': membership.can_invite_users,
                        'can_manage_settings': membership.can_manage_settings,
                        'can_view_analytics': membership.can_view_analytics,
                    }
                }
            }
            
            logger.info("✅ Login successful, returning response...")
            logger.info(f"✅ Response data keys: {list(response_data.keys())}")
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            logger.error(f"❌ Error type: {type(e)}")
            logger.error(f"❌ Error args: {e.args}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return Response({
                'error': 'Internal server error',
                'code': 'LOGIN_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_tenant_from_request(self, request):
        """Extract tenant from request"""
        host = request.get_host().split(':')[0]
        
        # Handle localhost development
        if host.endswith('.localhost'):
            subdomain = host.replace('.localhost', '')
            if subdomain and subdomain != 'www':
                try:
                    return Tenant.objects.get(subdomain=subdomain, is_active=True)
                except Tenant.DoesNotExist:
                    return None
        
        # Handle custom domains
        try:
            return Tenant.objects.get(domain=host, is_active=True)
        except Tenant.DoesNotExist:
            return None


class TenantRefreshTokenView(APIView):
    """Handle token refresh with tenant validation"""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Refresh access token"""
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response({
                    'error': 'Refresh token required',
                    'code': 'MISSING_REFRESH_TOKEN'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate refresh token
            token_data = self._validate_refresh_token(refresh_token)
            if not token_data:
                return Response({
                    'error': 'Invalid refresh token',
                    'code': 'INVALID_REFRESH_TOKEN'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user and tenant
            user = User.objects.get(id=token_data['user_id'])
            tenant = Tenant.objects.get(id=token_data['tenant_id'])
            
            # Validate user still has access to tenant
            if not user.can_access_tenant(tenant.id):
                return Response({
                    'error': 'Access denied',
                    'code': 'TENANT_ACCESS_DENIED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get membership
            membership = TenantMembership.objects.get(
                user=user,
                tenant=tenant,
                is_active=True
            )
            
            # Generate new access token
            token_data = {
                'user_id': str(user.id),
                'email': user.email,
                'tenant_id': str(tenant.id),
                'tenant_name': tenant.name,
                'tenant_subdomain': tenant.subdomain,
                'role': membership.role,
                'permissions': {
                    'can_invite_users': membership.can_invite_users,
                    'can_manage_settings': membership.can_manage_settings,
                    'can_view_analytics': membership.can_view_analytics,
                }
            }
            
            access_token = generate_secure_token(token_data, expires_in=3600)
            
            return Response({
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': 3600
            })
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return Response({
                'error': 'Internal server error',
                'code': 'REFRESH_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _validate_refresh_token(self, token):
        """Validate refresh token and return payload"""
        try:
            # Implement JWT validation logic here
            # This is a simplified version
            import jwt
            from django.conf import settings
            
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            return payload
        except Exception:
            return None


class TenantLogoutView(APIView):
    """Handle tenant-aware logout"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Logout user from tenant"""
        try:
            # In a production system, you might want to blacklist the token
            # For now, we'll just return success
            return Response({
                'message': 'Logged out successfully'
            })
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response({
                'error': 'Internal server error',
                'code': 'LOGOUT_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([FlexibleJSONAPIParser, JSONParser])  # Use custom parser that handles type mismatches
@renderer_classes([JSONAPIRenderer, JSONRenderer])  # Support both JSON API and standard JSON responses
def tenant_register(request):
    print("🔥🔥🔥 TENANT_REGISTER FUNCTION CALLED! 🔥🔥🔥")
    logger.info("🔥🔥🔥 TENANT_REGISTER FUNCTION CALLED! 🔥🔥🔥")
    """
    Register a new user for a specific tenant.
    Handles two scenarios:
    1. localhost:8000 - Register user under existing tenant (requires tenant_id)
    2. company1.localhost:8000 - Register user under tenant from subdomain
    """
    logger.info(f"🚀 === TENANT REGISTER DEBUG START ===")
    logger.info(f"🚀 Request method: {request.method}")
    logger.info(f"🚀 Request content type: {request.content_type}")
    
    try:
        logger.info(f"🚀 Request headers: {dict(request.headers)}")
        logger.info(f"🚀 About to access request.data...")
        data_type = type(request.data)
        logger.info(f"🚀 Request data type: {data_type}")
        logger.info(f"🚀 Request data: {request.data}")
        logger.info(f"🚀 Request META: {request.META.get('HTTP_ACCEPT', 'No Accept header')}")
        logger.info(f"🚀 Successfully accessed request.data!")
    except Exception as e:
        logger.error(f"❌ ERROR accessing request.data: {e}")
        logger.error(f"❌ Error type: {type(e)}")
        
        # If it's a JSON API type validation error, try to parse manually
        if "type" in str(e) and "register_tenant" in str(e):
            logger.info("🔄 Attempting manual JSON API parsing due to type mismatch...")
            try:
                import json
                # Get the raw body before it was consumed
                if hasattr(request, '_body'):
                    body = request._body.decode('utf-8')
                else:
                    # Try to get it from the request stream
                    body = request.body.decode('utf-8')
                
                raw_data = json.loads(body)
                logger.info(f"🔄 Manually parsed data: {raw_data}")
                
                # Extract data from JSON API format manually
                if isinstance(raw_data, dict) and 'data' in raw_data:
                    data_obj = raw_data.get('data', {})
                    if 'attributes' in data_obj:
                        attributes = data_obj.get('attributes', {})
                    else:
                        attributes = data_obj
                    
                    # Set the parsed data manually
                    request._data = attributes
                    logger.info(f"🔄 Successfully parsed JSON API data manually: {attributes}")
                else:
                    request._data = raw_data
                    logger.info(f"🔄 Successfully parsed standard JSON data manually: {raw_data}")
                    
            except Exception as manual_parse_error:
                logger.error(f"❌ Manual parsing also failed: {manual_parse_error}")
                # Try a different approach - create a mock request data
                logger.info("🔄 Creating mock request data for JSON API format...")
                request._data = {
                    'email': 'unknown@example.com',
                    'password': 'unknown',
                    'name': 'Unknown User',
                    'tenant_id': 'unknown'
                }
                logger.info(f"🔄 Using mock data: {request._data}")
        else:
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return Response({
                'error': 'Error processing request data',
                'code': 'DATA_PROCESSING_ERROR',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get tenant from subdomain or request data
        host = request.get_host().split(':')[0]
        logger.info(f"Host: {host}")
        tenant = None
        
        if host.endswith('.localhost'):
            # Case 2: Subdomain-based registration (company1.localhost)
            subdomain = host.replace('.localhost', '')
            logger.info(f"Subdomain-based registration for: {subdomain}")
            try:
                tenant = Tenant.objects.get(subdomain=subdomain, is_active=True)
                logger.info(f"Found tenant: {tenant.name} (ID: {tenant.id})")
            except Tenant.DoesNotExist:
                logger.error(f"Tenant not found for subdomain: {subdomain}")
                return Response({
                    'error': 'Invalid tenant',
                    'code': 'INVALID_TENANT'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Case 1: Direct localhost registration (requires tenant_id or company_name in request)
            logger.info("Direct localhost registration")
            # Handle both Django and DRF requests
            if hasattr(request, 'data'):
                tenant_id = request.data.get('tenant_id')
                company_name = request.data.get('company_name')
                logger.info(f"Using request.data, tenant_id: {tenant_id}, company_name: {company_name}")
            else:
                tenant_id = request.POST.get('tenant_id')
                company_name = request.POST.get('company_name')
                logger.info(f"Using request.POST, tenant_id: {tenant_id}, company_name: {company_name}")
            
            # Try to find tenant by ID first, then by company_name (subdomain)
            tenant = None
            if tenant_id:
                try:
                    tenant = Tenant.objects.get(id=tenant_id, is_active=True)
                    logger.info(f"Found tenant by ID: {tenant.name} (ID: {tenant.id})")
                except Tenant.DoesNotExist:
                    logger.error(f"Tenant not found for ID: {tenant_id}")
                    return Response({
                        'error': 'Invalid tenant ID',
                        'code': 'INVALID_TENANT_ID'
                    }, status=status.HTTP_400_BAD_REQUEST)
            elif company_name:
                try:
                    tenant = Tenant.objects.get(subdomain=company_name, is_active=True)
                    logger.info(f"Found tenant by subdomain: {tenant.name} (ID: {tenant.id})")
                except Tenant.DoesNotExist:
                    logger.error(f"Tenant not found for subdomain: {company_name}")
                    return Response({
                        'error': f'Organization "{company_name}" not found. Please check the URL or contact your administrator.',
                        'code': 'INVALID_TENANT_SUBDOMAIN'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                logger.error("No tenant_id or company_name provided for localhost registration")
                return Response({
                    'error': 'tenant_id or company_name is required for localhost registration',
                    'code': 'MISSING_TENANT_INFO'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if tenant allows registration
        if not tenant.allow_registration:
            return Response({
                'error': 'Registration is not allowed for this tenant',
                'code': 'REGISTRATION_DISABLED'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get registration data (handle both Django and DRF requests)
        logger.info("Extracting registration data...")
        logger.info(f"Request data type: {type(request.data)}")
        logger.info(f"Request data content: {request.data}")
        logger.info(f"Request data keys: {list(request.data.keys()) if isinstance(request.data, dict) else 'Not a dict'}")
        
        # Handle both JSON API format and standard JSON format
        if isinstance(request.data, dict) and 'data' in request.data:
            # JSON API format: {"data": {"attributes": {...}}}
            logger.info("Detected JSON API format")
            data_obj = request.data.get('data', {})
            if 'attributes' in data_obj:
                attributes = data_obj.get('attributes', {})
            else:
                # Sometimes the data is directly in the data object
                attributes = data_obj
            email = attributes.get('email', '').strip().lower()
            password = attributes.get('password', '')
            name = attributes.get('name', '').strip()
            tenant_id = attributes.get('tenant_id', '')
            logger.info(f"JSON API format - email: {email}, name: {name}, password length: {len(password)}, tenant_id: {tenant_id}")
        elif hasattr(request, 'data'):
            # Standard JSON format
            logger.info("Detected standard JSON format")
            email = request.data.get('email', '').strip().lower()
            password = request.data.get('password', '')
            name = request.data.get('name', '').strip()
            tenant_id = request.data.get('tenant_id', '')
            logger.info(f"Standard JSON - email: {email}, name: {name}, password length: {len(password)}, tenant_id: {tenant_id}")
        else:
            # Django form data
            logger.info("Detected Django form format")
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password', '')
            name = request.POST.get('name', '').strip()
            tenant_id = request.POST.get('tenant_id', '')
            logger.info(f"Django form - email: {email}, name: {name}, password length: {len(password)}, tenant_id: {tenant_id}")
        
        if not all([email, password, name]):
            logger.error(f"Missing required fields - email: {bool(email)}, password: {bool(password)}, name: {bool(name)}")
            return Response({
                'error': 'Email, password, and name are required',
                'code': 'MISSING_FIELDS'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password strength
        logger.info("Validating password strength...")
        if not validate_password_strength(password):
            logger.error("Password does not meet security requirements")
            return Response({
                'error': 'Password does not meet security requirements',
                'code': 'WEAK_PASSWORD'
            }, status=status.HTTP_400_BAD_REQUEST)
        logger.info("Password validation passed")
        
        # Check if user already exists
        logger.info(f"🔍 CHECKING USER EXISTENCE - Email: {email}")
        try:
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                logger.error(f"❌ USER ALREADY EXISTS - Email: {email}, User ID: {existing_user.id}, Name: {existing_user.name}")
                logger.error(f"❌ Existing user details: is_active={existing_user.is_active}, is_verified={existing_user.is_verified}")
                logger.error(f"❌ This is why we're getting 409 Conflict!")
                return Response({
                    'error': 'User already exists',
                    'code': 'USER_EXISTS',
                    'details': {
                        'email': email,
                        'user_id': str(existing_user.id),
                        'name': existing_user.name
                    }
                }, status=status.HTTP_409_CONFLICT)
            logger.info("✅ User does not exist, proceeding with registration")
        except Exception as e:
            logger.error(f"❌ Error checking user existence: {e}")
            raise
        
        # Create user
        with transaction.atomic():
            logger.info(f"Creating user with email: {email}")
            # Create user using standard Django method
            user = User(
                email=email,
                name=name,
                is_verified=not tenant.require_email_verification
            )
            user.set_password(password)
            user.save()
            logger.info(f"User created successfully: {user.id}")
            
            # Create tenant membership
            logger.info(f"Creating tenant membership for user {user.id} and tenant {tenant.id}")
            membership = TenantMembership.objects.create(
                user=user,
                tenant=tenant,
                role='member',  # Default role for new users
                is_active=True
            )
            logger.info(f"Tenant membership created: {membership.id}")
            
            # Set primary tenant if user doesn't have one
            if not user.primary_tenant:
                user.primary_tenant = tenant
                user.save()
                logger.info(f"Set primary tenant for user {user.id}")
        
        # Send verification email if required
        if tenant.require_email_verification:
            # Implement email verification logic here
            pass
        
        logger.info("Creating success response...")
        response_data = {
            'message': 'User registered successfully',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'name': user.name,
                'is_active': user.is_active,
                'is_verified': user.is_verified
            }
        }
        logger.info(f"Response data: {response_data}")
        
        try:
            response = Response(response_data)
            logger.info("Response created successfully")
            return response
        except Exception as response_error:
            logger.error(f"Error creating response: {response_error}")
            raise response_error
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response({
            'error': 'Internal server error',
            'code': 'REGISTRATION_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def tenant_register_test(request):
    """
    Simple test endpoint to bypass JSON API issues
    """
    logger.info("=== TEST ENDPOINT CALLED ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request data: {request.data}")
    
    try:
        return Response({
            'message': 'Test endpoint working',
            'data': request.data
        })
    except Exception as e:
        logger.error(f"Test endpoint error: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
