from config.django.base import *  # noqa
from config.env import env

DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

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
