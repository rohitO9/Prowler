from config.django.base import *  # noqa
from config.env import env

DEBUG = env.bool("DJANGO_DEBUG", default=False)
# ALLOWED_HOSTS: Include domain, server IP, and localhost for production
# Set DJANGO_ALLOWED_HOSTS in .env file, e.g.:
# DJANGO_ALLOWED_HOSTS=vulneralq.anantacloud.com,107.21.175.192,localhost,127.0.0.1
# Note: Remove quotes from the value in .env file - quotes will be treated as part of the hostname
_allowed_hosts = env.list("DJANGO_ALLOWED_HOSTS", default=["vulneralq.anantacloud.com", "107.21.175.192", "localhost", "127.0.0.1"])
# Strip quotes from each host if present (handles cases where .env has quoted values)
ALLOWED_HOSTS = [host.strip('"\'') for host in _allowed_hosts]

# Database
# TODO Use Django database routers https://docs.djangoproject.com/en/5.0/topics/db/multi-db/#automatic-database-routing
DATABASES = {
    "prowler_user": {
        "ENGINE": "psqlextra.backend",
        "NAME": env("POSTGRES_DB", default="prowler_db"),
        "USER": env("POSTGRES_USER", default="prowler"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="prowler"),
        "HOST": env("POSTGRES_HOST", default="postgres-db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    },
    "admin": {
        "ENGINE": "psqlextra.backend",
        "NAME": env("POSTGRES_DB", default="prowler_db"),
        "USER": env("POSTGRES_ADMIN_USER", default="prowler"),
        "PASSWORD": env("POSTGRES_ADMIN_PASSWORD", default="S3cret"),
        "HOST": env("POSTGRES_HOST", default="postgres-db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    },
}
DATABASES["default"] = DATABASES["prowler_user"]

# Add SECRET_KEY with default
SECRET_KEY = env("SECRET_KEY", default="your-secret-key-here-change-this-in-production")

# Production CORS Configuration
# Override CORS settings from base.py for production
# Set these in .env file:
# CORS_ALLOWED_ORIGINS=https://vulneralq.anantacloud.com
# CORS_ALLOWED_ORIGIN_REGEXES=^https://.*\.vulneralq\.anantacloud\.com$,^https://vulneralq\.anantacloud\.com$
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "https://vulneralq.anantacloud.com",
    ]
)

CORS_ALLOWED_ORIGIN_REGEXES = env.list(
    "CORS_ALLOWED_ORIGIN_REGEXES",
    default=[
        r"^https://.*\.vulneralq\.anantacloud\.com$",
        r"^https://vulneralq\.anantacloud\.com$",
    ]
)

CORS_ALLOW_CREDENTIALS = True