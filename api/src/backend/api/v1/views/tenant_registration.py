import secrets
import string
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from datetime import timedelta
import logging
import random
import string

from api.models import Tenant, TenantMembership
from api.v1.serializers import TenantSerializer, UserSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


def generate_temp_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%^&*()-_"
    return "".join(random.choice(chars) for _ in range(length))


@api_view(['POST'])
@permission_classes([AllowAny])
def register_tenant(request):
    """
    Accepts JSON:API payloads or flattened payloads. Normalizes incoming payload to
    `attributes` dict, logs detailed info and validates required fields.
    """
    logger.info("=== TENANT REGISTRATION REQUEST START ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")

    try:
        raw = request.data or {}
        logger.info(f"Raw request data: {raw}")
    except Exception:
        raw = {}
        logger.exception("Failed to read request.data")

    # Normalize payload to attributes dict (accept both JSON:API and flattened forms)
    attributes = {}
    if isinstance(raw, dict):
        if 'data' in raw and isinstance(raw.get('data'), dict):
            data_obj = raw.get('data') or {}
            # JSON:API: data.attributes
            if isinstance(data_obj.get('attributes'), dict):
                attributes = data_obj.get('attributes') or {}
            else:
                # sometimes frontend or middleware flattens into data object directly
                attributes = data_obj
        elif isinstance(raw.get('attributes'), dict):
            attributes = raw.get('attributes') or {}
        else:
            # frontend sent flattened attributes at root
            attributes = raw

    logger.info(f"Normalized attributes: {attributes}")

    # Accept alt field names (tenant_name or name)
    tenant_name = attributes.get('tenant_name') or attributes.get('name')
    subdomain = attributes.get('subdomain')
    contact_email = attributes.get('contact_email') or attributes.get('contactEmail')
    admin_first_name = attributes.get('admin_first_name') or attributes.get('adminFirstName')
    admin_last_name = attributes.get('admin_last_name') or attributes.get('adminLastName')
    admin_email = attributes.get('admin_email') or attributes.get('adminEmail')

    contact_phone = attributes.get('contact_phone', '')
    address = attributes.get('address', '')
    logo_url = attributes.get('logo_url', '')
    theme_color = attributes.get('theme_color', '#3B82F6')
    secondary_color = attributes.get('secondary_color', '#1E40AF')

    # Log extracted values (avoid logging sensitive data)
    logger.info("=== FIELD EXTRACTION RESULTS ===")
    logger.info(f"tenant_name: {repr(tenant_name)} (type: {type(tenant_name)})")
    logger.info(f"subdomain: {repr(subdomain)} (type: {type(subdomain)})")
    logger.info(f"contact_email: {repr(contact_email)} (type: {type(contact_email)})")
    logger.info(f"contact_phone: {repr(contact_phone)}")
    logger.info(f"address: {repr(address)}")
    logger.info(f"logo_url: {repr(logo_url)}")
    logger.info(f"theme_color: {repr(theme_color)}")
    logger.info(f"secondary_color: {repr(secondary_color)}")
    logger.info(f"admin_first_name: {repr(admin_first_name)}")
    logger.info(f"admin_last_name: {repr(admin_last_name)}")
    logger.info(f"admin_email: {repr(admin_email)}")

    # Validate required fields
    missing = []
    if not tenant_name:
        missing.append('tenant_name')
    if not subdomain:
        missing.append('subdomain')
    if not contact_email:
        missing.append('contact_email')
    if not admin_first_name:
        missing.append('admin_first_name')
    if not admin_last_name:
        missing.append('admin_last_name')
    if not admin_email:
        missing.append('admin_email')

    if missing:
        logger.error(f"❌ VALIDATION FAILED - Missing fields: {missing}")
        return Response(
            {"errors": [{"detail": f"Missing required fields: {missing}"}]},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Proceed with tenant creation (wrap in transaction)
    try:
        with transaction.atomic():
            # Create Tenant
            tenant = Tenant.objects.create(
                name=tenant_name,
                subdomain=subdomain,
                contact_email=contact_email,
                contact_phone=contact_phone,
                address=address,
                logo_url=logo_url,
                theme_color=theme_color,
                secondary_color=secondary_color
            )
            logger.info(f"Tenant created: id={getattr(tenant, 'id', None)} subdomain={getattr(tenant, 'subdomain', None)}")

            # Create admin user (temporary password)
            temp_password = generate_temp_password()
            user = None

            try:
                # Prefer manager.create_user when available
                if hasattr(User.objects, "create_user"):
                    user_kwargs = {
                        'email': admin_email,
                        'first_name': admin_first_name,
                        'last_name': admin_last_name,
                        'password': temp_password,
                        'is_active': True,
                    }
                    
                    # Add tenant_id if User model has it
                    if hasattr(User, 'tenant_id'):
                        user_kwargs['tenant_id'] = tenant
                    elif hasattr(User, 'tenant'):
                        user_kwargs['tenant'] = tenant
                    
                    user = User.objects.create_user(**user_kwargs)
                else:
                    raise AttributeError("create_user not available")
            except Exception as e:
                logger.debug(f"create_user failed or unavailable: {e}. Falling back to safe create.")
                # Build kwargs only with model fields accepted by User.__init__
                model_fields = {f.name for f in User._meta.get_fields() if hasattr(f, "attname")}
                fallback_kwargs = {}
                candidates = {
                    "email": admin_email,
                    "first_name": admin_first_name,
                    "last_name": admin_last_name,
                    "is_active": True,
                }
                
                # Add tenant relationship if it exists
                if 'tenant_id' in model_fields:
                    candidates['tenant_id'] = tenant
                elif 'tenant' in model_fields:
                    candidates['tenant'] = tenant

                for k, v in candidates.items():
                    if k in model_fields:
                        fallback_kwargs[k] = v

                # Create user with allowed fields, set password if available
                user = User.objects.create(**fallback_kwargs)
                if hasattr(user, "set_password"):
                    user.set_password(temp_password)
                user.save()

            logger.info(f"Admin user created: id={getattr(user, 'id', None)} email={getattr(user, 'email', None)}")

            # Create tenant membership
            try:
                membership = TenantMembership.objects.create(
                    tenant=tenant,
                    user=user,
                    role='owner'  # Use string directly
                )
                logger.info(f"TenantMembership created for user={getattr(user, 'id', None)} tenant={getattr(tenant, 'id', None)} role=owner")
            except Exception as membership_error:
                logger.error(f"Failed to create tenant membership: {membership_error}")
                raise Exception(f"Cannot create tenant membership: {membership_error}")

            # Optionally send welcome email (safe logging)
            try:
                # Skip email sending for now to avoid configuration issues
                logger.info(f"Would send registration email to {admin_email} with temp password: {temp_password}")
                # send_mail(
                #     subject=f"Your {tenant.name} account",
                #     message=f"Welcome {admin_first_name}. Your temporary password is {temp_password}",
                #     from_email=settings.DEFAULT_FROM_EMAIL,
                #     recipient_list=[admin_email],
                #     fail_silently=False
                # )
                logger.info(f"Email sending skipped for testing")
            except Exception:
                logger.exception("Failed to send registration email")

            tenant_data = TenantSerializer(tenant).data
            return Response({"data": tenant_data}, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception(f"Tenant registration failed during DB operations: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response(
            {"errors": [{"detail": f"Internal error while creating tenant: {str(e)}"}]},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def send_tenant_confirmation_email(tenant, admin_user, temp_password):
    """Send confirmation email to the admin user"""
    try:
        # Create verification token (you might want to use a more secure method)
        verification_token = secrets.token_urlsafe(32)
        
        # Store verification token (you might want to create a separate model for this)
        # For now, we'll use a simple approach
        
        verification_url = f"{settings.FRONTEND_URL}/verify-tenant?token={verification_token}&email={admin_user.email}"
        tenant_url = f"http://{tenant.subdomain}.localhost:3000"  # Update for production
        
        subject = f"Welcome to {tenant.name} - Verify Your Account"
        
        message = f"""
        Hello {admin_user.first_name},
        
        Welcome to {tenant.name}! Your tenant account has been created successfully.
        
        Tenant Details:
        - Company: {tenant.name}
        - Subdomain: {tenant.subdomain}
        - Access URL: {tenant_url}
        
        Your temporary login credentials:
        - Email: {admin_user.email}
        - Password: {temp_password}
        
        Please verify your account by clicking the link below:
        {verification_url}
        
        After verification, you can:
        1. Log in to your tenant dashboard
        2. Customize your company settings
        3. Invite team members
        4. Configure your security settings
        
        This is a temporary password. Please change it after your first login.
        
        If you have any questions, please contact our support team.
        
        Best regards,
        The Prowler Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_user.email],
            fail_silently=False,
        )
        
        logger.info(f"Sent confirmation email to {admin_user.email} for tenant {tenant.name}")
        
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {str(e)}")


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_tenant(request):
    """
    Verify tenant email and activate admin user
    """
    try:
        data = request.data.get('data', {})
        attributes = data.get('attributes', {})
        
        email = attributes.get('email')
        token = attributes.get('verification_token')
        
        if not email or not token:
            return Response(
                {"errors": [{"detail": "Email and verification token are required"}]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find the user and tenant
        try:
            user = User.objects.get(email=email)
            tenant = Tenant.objects.get(admin_user=user)
        except (User.DoesNotExist, Tenant.DoesNotExist):
            return Response(
                {"errors": [{"detail": "Invalid verification link"}]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the token (in a real implementation, you'd store and validate this properly)
        # For now, we'll just activate the user
        user.is_active = True
        user.is_verified = True
        user.save()
        
        tenant.is_verified = True
        tenant.save()
        
        logger.info(f"Verified tenant {tenant.name} and activated admin user {user.email}")
        
        return Response({
            "data": {
                "type": "tenants",
                "id": str(tenant.id),
                "attributes": {
                    "name": tenant.name,
                    "subdomain": tenant.subdomain,
                    "status": "verified",
                    "message": "Tenant verified successfully. You can now log in to your dashboard."
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error verifying tenant: {str(e)}")
        return Response(
            {"errors": [{"detail": "Failed to verify tenant"}]},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def check_subdomain_availability(request):
    """
    Check if a subdomain is available
    """
    subdomain = request.GET.get('subdomain')
    
    if not subdomain:
        return Response(
            {"errors": [{"detail": "Subdomain parameter is required"}]},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate subdomain format
    if not subdomain.replace('-', '').replace('_', '').isalnum():
        return Response(
            {"errors": [{"detail": "Subdomain can only contain letters, numbers, hyphens, and underscores"}]},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check reserved subdomains
    reserved_subdomains = ['www', 'api', 'admin', 'app', 'mail', 'ftp', 'blog', 'shop', 'support', 'help']
    if subdomain.lower() in reserved_subdomains:
        return Response({
            "data": {
                "attributes": {
                    "subdomain": subdomain,
                    "available": False,
                    "reason": "This subdomain is reserved"
                }
            }
        })
    
    is_available = not Tenant.objects.filter(subdomain=subdomain).exists()
    
    return Response({
        "data": {
            "attributes": {
                "subdomain": subdomain,
                "available": is_available,
                "reason": "Available" if is_available else "Already taken"
            }
        }
    })