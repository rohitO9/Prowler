# Production Deployment Guide

This document outlines all the changes needed to deploy the application to production with the domain `https://vulneralq.anantacloud.com`.

## 1. Backend API Configuration (Django)

### 1.1 Update CORS Settings

**File:** `api/src/backend/config/django/base.py` (or create production-specific settings)

Update the `CORS_ALLOWED_ORIGINS` to include your production domain:

```python
CORS_ALLOWED_ORIGINS = [
    "https://vulneralq.anantacloud.com",
    "https://*.vulneralq.anantacloud.com",  # Allow all subdomains
    # Keep localhost for development if needed
    "http://localhost:3000",
    "http://localhost:8080",
]

# Or use environment variable for dynamic configuration
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "https://vulneralq.anantacloud.com",
        "https://*.vulneralq.anantacloud.com",
    ]
)
```

**Alternative:** Use `CORS_ALLOW_ALL_ORIGINS = True` for development, but **NEVER** in production. Instead, use:

```python
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vulneralq\.anantacloud\.com$",
    r"^https://vulneralq\.anantacloud\.com$",
]
```

### 1.2 Update ALLOWED_HOSTS

**File:** `api/src/backend/config/django/production.py`

```python
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        "vulneralq.anantacloud.com",
        "*.vulneralq.anantacloud.com",  # Allow all subdomains
        "api.vulneralq.anantacloud.com",  # If API is on separate subdomain
    ]
)
```

### 1.3 Update Frontend URL for Email Links

**File:** `api/src/backend/config/settings.py` or environment variables

```python
FRONTEND_URL = env("FRONTEND_URL", default="https://vulneralq.anantacloud.com")
```

### 1.4 Environment Variables for Backend

Create/update `.env` file in the `api` directory:

```bash
# Django Settings
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=vulneralq.anantacloud.com,*.vulneralq.anantacloud.com,api.vulneralq.anantacloud.com
SECRET_KEY=your-production-secret-key-here

# CORS Settings
CORS_ALLOWED_ORIGINS=https://vulneralq.anantacloud.com,https://*.vulneralq.anantacloud.com

# Frontend URL
FRONTEND_URL=https://vulneralq.anantacloud.com

# Database (Production)
POSTGRES_HOST=your-production-db-host
POSTGRES_DB=your-production-db-name
POSTGRES_USER=your-production-db-user
POSTGRES_PASSWORD=your-production-db-password
POSTGRES_ADMIN_USER=your-production-admin-user
POSTGRES_ADMIN_PASSWORD=your-production-admin-password

# Redis/Valkey (Production)
REDIS_URL=redis://your-production-redis-host:6379/0

# Email Configuration (Production)
EMAIL_HOST=smtp.your-email-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@vulneralq.anantacloud.com
```

## 2. Frontend Configuration (Next.js)

### 2.1 Environment Variables

Create/update `.env.local` or `.env.production` in the `ui` directory:

```bash
# Next.js Environment
NODE_ENV=production

# API Base URL
NEXT_PUBLIC_API_BASE_URL=https://api.vulneralq.anantacloud.com/api/v1
# OR if API is on same domain:
# NEXT_PUBLIC_API_BASE_URL=https://vulneralq.anantacloud.com:8080/api/v1

# Auth URL
AUTH_URL=https://vulneralq.anantacloud.com

# NextAuth Configuration
NEXTAUTH_URL=https://vulneralq.anantacloud.com
NEXTAUTH_SECRET=your-nextauth-secret-key

# Social OAuth (if using)
SOCIAL_GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
SOCIAL_GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret
SOCIAL_GOOGLE_OAUTH_CALLBACK_URL=https://vulneralq.anantacloud.com/api/auth/callback/google

SOCIAL_GITHUB_OAUTH_CLIENT_ID=your-github-client-id
SOCIAL_GITHUB_OAUTH_CLIENT_SECRET=your-github-client-secret
SOCIAL_GITHUB_OAUTH_CALLBACK_URL=https://vulneralq.anantacloud.com/api/auth/callback/github

# Azure AD (if using)
AZURE_AD_TENANT_ID=your-azure-tenant-id
AZURE_AD_CLIENT_ID=your-azure-client-id
AZURE_AD_REDIRECT_URI=https://vulneralq.anantacloud.com/api/auth/callback/azure
```

### 2.2 Update next.config.js (if needed)

The current `next.config.js` already has production CSP headers configured. Ensure it's set correctly for production.

## 3. Docker Configuration

### 3.1 Update docker-compose.yml for Production

**File:** `docker-compose.yml`

Create a `docker-compose.prod.yml` or update the existing one:

```yaml
services:
  api:
    environment:
      - DJANGO_PORT=8080
      - DJANGO_DEBUG=False
      - DJANGO_ALLOWED_HOSTS=vulneralq.anantacloud.com,*.vulneralq.anantacloud.com
      - CORS_ALLOWED_ORIGINS=https://vulneralq.anantacloud.com,https://*.vulneralq.anantacloud.com
      - FRONTEND_URL=https://vulneralq.anantacloud.com
    # Remove port mapping if behind reverse proxy
    # ports:
    #   - "8080:8080"

  ui:
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_BASE_URL=https://api.vulneralq.anantacloud.com/api/v1
      - AUTH_URL=https://vulneralq.anantacloud.com
    # Remove port mapping if behind reverse proxy
    # ports:
    #   - "3000:3000"
```

## 4. Server/Infrastructure Configuration

### 4.1 DNS Configuration

Configure DNS records for your domain:

```
# Main domain
vulneralq.anantacloud.com          A    <your-server-ip>

# Wildcard subdomain (for tenant subdomains)
*.vulneralq.anantacloud.com        A    <your-server-ip>

# API subdomain (if API is on separate subdomain)
api.vulneralq.anantacloud.com      A    <your-server-ip>
```

### 4.2 Reverse Proxy Configuration (Nginx)

**File:** `/etc/nginx/sites-available/vulneralq.anantacloud.com`

```nginx
# Main domain and subdomains
server {
    listen 80;
    server_name vulneralq.anantacloud.com *.vulneralq.anantacloud.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name vulneralq.anantacloud.com *.vulneralq.anantacloud.com;
    
    # SSL Configuration
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Frontend (Next.js)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers (if not handled by Django)
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
        add_header Access-Control-Allow-Credentials true always;
        
        if ($request_method = OPTIONS) {
            return 204;
        }
    }
}
```

**If API is on separate subdomain:**

```nginx
# API subdomain
server {
    listen 443 ssl http2;
    server_name api.vulneralq.anantacloud.com;
    
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4.3 SSL Certificate

Obtain SSL certificate using Let's Encrypt:

```bash
# Install certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d vulneralq.anantacloud.com -d *.vulneralq.anantacloud.com

# Auto-renewal (already configured by certbot)
```

## 5. Database Migration

Run migrations on production database:

```bash
cd api
python manage.py migrate
python manage.py collectstatic --noinput
```

## 6. Security Checklist

- [ ] Set `DJANGO_DEBUG=False` in production
- [ ] Use strong `SECRET_KEY` (generate new one, don't use default)
- [ ] Use strong database passwords
- [ ] Configure proper CORS origins (no wildcards in production)
- [ ] Enable HTTPS/SSL
- [ ] Configure proper ALLOWED_HOSTS
- [ ] Set secure cookie flags in Django
- [ ] Configure proper email settings
- [ ] Enable rate limiting (if applicable)
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy for database
- [ ] Review and update CSP headers
- [ ] Enable security headers in Nginx

## 7. Testing Checklist

After deployment, test:

- [ ] Main domain loads: `https://vulneralq.anantacloud.com`
- [ ] Tenant registration works
- [ ] Subdomain redirects work: `https://{subdomain}.vulneralq.anantacloud.com`
- [ ] API calls work from frontend
- [ ] CORS is properly configured (no CORS errors in browser console)
- [ ] Authentication flows work
- [ ] Email invitations work (check FRONTEND_URL in emails)
- [ ] SSL certificate is valid
- [ ] All redirects use HTTPS

## 8. Monitoring

Set up monitoring for:

- Application logs
- Error tracking (Sentry, if configured)
- Database performance
- API response times
- SSL certificate expiration
- Disk space and server resources

## 9. Quick Reference: Key Files to Update

1. **Backend:**
   - `api/src/backend/config/django/base.py` - CORS settings
   - `api/src/backend/config/django/production.py` - ALLOWED_HOSTS
   - `api/.env` - Environment variables

2. **Frontend:**
   - `ui/.env.local` or `ui/.env.production` - Environment variables
   - Already updated: `ui/lib/helper.ts` - API URL helper
   - Already updated: All component files with localhost references

3. **Infrastructure:**
   - Nginx configuration
   - DNS records
   - SSL certificates
   - Docker compose (if using)

## 10. Deployment Steps

1. Update all configuration files
2. Set environment variables
3. Build frontend: `cd ui && npm run build`
4. Run database migrations
5. Configure Nginx
6. Set up SSL certificates
7. Start services (Docker or systemd)
8. Test all functionality
9. Monitor logs for errors

---

**Note:** Always test in a staging environment first before deploying to production!

