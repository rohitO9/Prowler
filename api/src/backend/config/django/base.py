from datetime import timedelta

from config.custom_logging import LOGGING  # noqa
from config.env import BASE_DIR, env  # noqa
from config.settings.celery import *  # noqa
from config.settings.partitions import *  # noqa
from config.settings.sentry import *  # noqa
from config.settings.social_login import *  # noqa
from api.settings.azure_ad import *  # noqa

SECRET_KEY = env("SECRET_KEY", default="secret")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
# For development, allow all hosts (including dynamic subdomains)
ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "psqlextra",
    "api",
    # "api_rls",        # Add this
    "api.v1",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "drf_spectacular_jsonapi",
    "django_guid",
    "rest_framework_json_api",
    "django_celery_results",
    "django_celery_beat",
    "rest_framework_simplejwt.token_blacklist",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.github",
    "dj_rest_auth",  # Added for password reset endpoints
    "dj_rest_auth.registration",
    "rest_framework.authtoken",
]

DATABASES = {
    'default': {
        'ENGINE': 'psqlextra.backend',
        'NAME': env.str('DJANGO_DB_NAME', 'prowler_db'),
        'USER': env.str('DJANGO_DB_USER', 'prowler_user'),
        'PASSWORD': env.str('DJANGO_DB_PASSWORD', 'postgres'),
        'HOST': env.str('DJANGO_DB_HOST', 'localhost'),
        'PORT': env.str('DJANGO_DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 60,
        },
    },
    'prowler_user': {
        'ENGINE': 'psqlextra.backend',
        'NAME': env.str('DJANGO_DB_NAME', 'prowler_db'),  # Same database
        'USER': env.str('DJANGO_DB_USER', 'prowler_user'),
        'PASSWORD': env.str('DJANGO_DB_PASSWORD', 'postgres'),
        'HOST': env.str('DJANGO_DB_HOST', 'localhost'),
        'PORT': env.str('DJANGO_DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 60,
        },
    },
    'admin': {
        'ENGINE': 'psqlextra.backend',
        'NAME': env.str('DJANGO_DB_NAME', 'prowler_db'),  # same DB as default
        'USER': env.str('POSTGRES_ADMIN_USER', 'postgres'),  # Postgres superuser for GRANTs
        'PASSWORD': env.str('POSTGRES_ADMIN_PASSWORD', 'postgres'),
        'HOST': env.str('DJANGO_DB_HOST', 'localhost'),
        'PORT': env.str('DJANGO_DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 60,
        },
    },
}
MIDDLEWARE = [
    "django_guid.middleware.guid_middleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
    # ✅ CRITICAL ORDER: Multi-tenant security middleware
    # 1. Extract tenant from subdomain (before tenant isolation)
    "api.middleware.subdomain.SubdomainMiddleware",
    
    # 2. Validate tenant access (after auth, uses request.user)
    "api.middleware.tenant_isolation.TenantIsolationMiddleware",
    
    # 3. Audit logging (should be last to capture full request)
    "api.middleware.tenant_audit.TenantAuditMiddleware",
    
    # Additional middleware
    "api.middleware.APILoggingMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

SITE_ID = 1

# CORS Configuration - Use environment variable for production
# In production, set CORS_ALLOWED_ORIGINS in .env file:
# CORS_ALLOWED_ORIGINS=https://vulneralq.anantacloud.com,https://*.vulneralq.anantacloud.com
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost", 
        "http://127.0.0.1", 
        "http://localhost:3000", 
        "http://localhost:8080",
        "http://company1.localhost:3000",
        "http://company2.localhost:3000", 
        "http://test.localhost:3000",
        "http://google.localhost:3000",
        "http://companynew.localhost:3000",
        "http://testcompany.localhost:3000",
        # Note: Wildcard subdomains in CORS_ALLOWED_ORIGINS don't work
        # Use CORS_ALLOWED_ORIGIN_REGEXES for wildcard support
    ]
)

# For wildcard subdomain support (e.g., *.vulneralq.anantacloud.com)
CORS_ALLOWED_ORIGIN_REGEXES = env.list(
    "CORS_ALLOWED_ORIGIN_REGEXES",
    default=[
        r"^http://.*\.localhost:3000$",  # Development: *.localhost:3000
    ]
)

# In production, add this to .env:
# CORS_ALLOWED_ORIGIN_REGEXES=^https://.*\.vulneralq\.anantacloud\.com$,^https://vulneralq\.anantacloud\.com$

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # Add templates directory (templates/ at backend root)
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular_jsonapi.schemas.openapi.JsonApiAutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "PAGE_SIZE": 10,
    "EXCEPTION_HANDLER": "api.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "drf_spectacular_jsonapi.schemas.pagination.JsonApiPageNumberPagination",
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework_json_api.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_RENDERER_CLASSES": ("api.renderers.APIJSONRenderer",),
    "DEFAULT_METADATA_CLASS": "rest_framework_json_api.metadata.JSONAPIMetadata",
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework_json_api.filters.QueryParameterValidationFilter",
        "rest_framework_json_api.filters.OrderingFilter",
        "rest_framework_json_api.django_filters.backends.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "SEARCH_PARAM": "filter[search]",
    "TEST_REQUEST_RENDERER_CLASSES": (
        "rest_framework_json_api.renderers.JSONRenderer",
    ),
    "TEST_REQUEST_DEFAULT_FORMAT": "vnd.api+json",
    "JSON_API_UNIFORM_EXCEPTIONS": True,
}

SPECTACULAR_SETTINGS = {
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "PREPROCESSING_HOOKS": [
        "drf_spectacular_jsonapi.hooks.fix_nested_path_parameters",
    ],
    "TITLE": "API Reference - Prowler",
}

WSGI_APPLICATION = "config.wsgi.application"

DJANGO_GUID = {
    "GUID_HEADER_NAME": "Transaction-ID",
    "VALIDATE_GUID": True,
    "RETURN_HEADER": True,
    "EXPOSE_HEADER": True,
    "INTEGRATIONS": [],
    "IGNORE_URLS": [],
    "UUID_LENGTH": 32,
}

DATABASE_ROUTERS = ["api.db_router.MainRouter"]
POSTGRES_EXTRA_DB_BACKEND_BASE = "database_backend"


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_USER_MODEL = 'api.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "api.validators.MaximumLengthValidator",
        "OPTIONS": {
            "max_length": 72,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

SIMPLE_JWT = {
    # Token lifetime settings
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("DJANGO_ACCESS_TOKEN_LIFETIME", 60)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        minutes=env.int("DJANGO_REFRESH_TOKEN_LIFETIME", 60 * 24)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    # Algorithm and keys
    "ALGORITHM": "RS256",
    "SIGNING_KEY": env.str("DJANGO_TOKEN_SIGNING_KEY", "").replace("\\n", "\n"),
    "VERIFYING_KEY": env.str("DJANGO_TOKEN_VERIFYING_KEY", "").replace("\\n", "\n"),
    # Authorization header configuration
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    # Custom serializers
    "TOKEN_OBTAIN_SERIALIZER": "api.v1.serializers.TokenSerializer",
    "TOKEN_REFRESH_SERIALIZER": "api.v1.serializers.TokenRefreshSerializer",
    # Standard JWT claims
    "TOKEN_TYPE_CLAIM": "typ",
    "JTI_CLAIM": "jti",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "sub",
    # Issuer and Audience claims, for the moment we will keep these values as default values, they may change in the future.
    "AUDIENCE": env.str("DJANGO_JWT_AUDIENCE", "https://api.prowler.com"),
    "ISSUER": env.str("DJANGO_JWT_ISSUER", "https://api.prowler.com"),
    # Additional security settings
    "UPDATE_LAST_LOGIN": True,
}

SECRETS_ENCRYPTION_KEY = env.str("DJANGO_SECRETS_ENCRYPTION_KEY", "")

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"
LANGUAGES = [
    ("en", "English"),
]

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# Email Configuration
EMAIL_BACKEND = env.str(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env.str("DJANGO_EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("DJANGO_EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("DJANGO_EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("DJANGO_EMAIL_USE_SSL", default=False)
EMAIL_HOST_USER = env.str("DJANGO_EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("DJANGO_EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env.str("DJANGO_DEFAULT_FROM_EMAIL", default="no-reply@localhost")
FRONTEND_URL = env.str("FRONTEND_URL", default="http://localhost:3000")

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cache settings
CACHE_MAX_AGE = env.int("DJANGO_CACHE_MAX_AGE", 3600)
CACHE_STALE_WHILE_REVALIDATE = env.int("DJANGO_STALE_WHILE_REVALIDATE", 60)


TESTING = False

FINDINGS_MAX_DAYS_IN_RANGE = env.int("DJANGO_FINDINGS_MAX_DAYS_IN_RANGE", 7)


# API export settings
DJANGO_TMP_OUTPUT_DIRECTORY = env.str(
    "DJANGO_TMP_OUTPUT_DIRECTORY", "/tmp/prowler_api_output"
)
DJANGO_FINDINGS_BATCH_SIZE = env.str("DJANGO_FINDINGS_BATCH_SIZE", 1000)

DJANGO_OUTPUT_S3_AWS_OUTPUT_BUCKET = env.str("DJANGO_OUTPUT_S3_AWS_OUTPUT_BUCKET", "")
DJANGO_OUTPUT_S3_AWS_ACCESS_KEY_ID = env.str("DJANGO_OUTPUT_S3_AWS_ACCESS_KEY_ID", "")
DJANGO_OUTPUT_S3_AWS_SECRET_ACCESS_KEY = env.str(
    "DJANGO_OUTPUT_S3_AWS_SECRET_ACCESS_KEY", ""
)
DJANGO_OUTPUT_S3_AWS_SESSION_TOKEN = env.str("DJANGO_OUTPUT_S3_AWS_SESSION_TOKEN", "")
DJANGO_OUTPUT_S3_AWS_DEFAULT_REGION = env.str("DJANGO_OUTPUT_S3_AWS_DEFAULT_REGION", "")

# HTTP Security Headers
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

DJANGO_DELETION_BATCH_SIZE = env.int("DJANGO_DELETION_BATCH_SIZE", 5000)
