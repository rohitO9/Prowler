# Production Changes Summary

## Quick Checklist for Production Deployment

### ✅ Already Fixed (Frontend)
- [x] Updated all `localhost:3000` references to `vulneralq.anantacloud.com`
- [x] Updated API URL helper to use production domain
- [x] Fixed redirect URLs after tenant registration
- [x] Updated subdomain detection logic

### 🔧 Required Changes

#### 1. Backend API (Django) - **REQUIRED**

**File: `api/.env`** - Add these environment variables:
```bash
# CORS Configuration
CORS_ALLOWED_ORIGINS=https://vulneralq.anantacloud.com
CORS_ALLOWED_ORIGIN_REGEXES=^https://.*\.vulneralq\.anantacloud\.com$,^https://vulneralq\.anantacloud\.com$

# Django Settings
DJANGO_ALLOWED_HOSTS=vulneralq.anantacloud.com,*.vulneralq.anantacloud.com
DJANGO_DEBUG=False
SECRET_KEY=your-strong-secret-key-here

# Frontend URL
FRONTEND_URL=https://vulneralq.anantacloud.com
```

**Files Updated:**
- ✅ `api/src/backend/config/django/base.py` - CORS now uses env vars
- ✅ `api/src/backend/config/django/production.py` - Production CORS config
- ✅ `api/src/backend/config/settings.py` - FRONTEND_URL uses env var

#### 2. Frontend (Next.js) - **REQUIRED**

**File: `ui/.env.production` or `ui/.env.local`** - Add:
```bash
NODE_ENV=production
NEXT_PUBLIC_API_BASE_URL=https://api.vulneralq.anantacloud.com/api/v1
# OR if API is on same domain:
# NEXT_PUBLIC_API_BASE_URL=https://vulneralq.anantacloud.com:8080/api/v1

AUTH_URL=https://vulneralq.anantacloud.com
NEXTAUTH_URL=https://vulneralq.anantacloud.com
NEXTAUTH_SECRET=your-nextauth-secret
```

#### 3. Server Infrastructure - **REQUIRED**

1. **DNS Configuration:**
   - `vulneralq.anantacloud.com` → Your server IP
   - `*.vulneralq.anantacloud.com` → Your server IP (wildcard)
   - `api.vulneralq.anantacloud.com` → Your server IP (if separate)

2. **Nginx Configuration:**
   - Configure reverse proxy (see PRODUCTION_DEPLOYMENT.md)
   - Set up SSL/HTTPS certificates
   - Configure subdomain routing

3. **SSL Certificate:**
   ```bash
   sudo certbot --nginx -d vulneralq.anantacloud.com -d *.vulneralq.anantacloud.com
   ```

#### 4. Docker (if using) - **OPTIONAL**

**File: `docker-compose.prod.yml`** - Update environment variables:
```yaml
services:
  api:
    environment:
      - CORS_ALLOWED_ORIGINS=https://vulneralq.anantacloud.com
      - DJANGO_ALLOWED_HOSTS=vulneralq.anantacloud.com,*.vulneralq.anantacloud.com
      - FRONTEND_URL=https://vulneralq.anantacloud.com
      
  ui:
    environment:
      - NEXT_PUBLIC_API_BASE_URL=https://api.vulneralq.anantacloud.com/api/v1
      - AUTH_URL=https://vulneralq.anantacloud.com
```

## Critical Steps

1. **Set Environment Variables** - Both backend and frontend
2. **Update CORS Settings** - Backend must allow production domain
3. **Configure DNS** - Wildcard subdomain for tenants
4. **Set up SSL** - HTTPS is required
5. **Test** - Verify all redirects and API calls work

## Testing After Deployment

1. ✅ Main domain loads: `https://vulneralq.anantacloud.com`
2. ✅ Tenant registration works
3. ✅ Subdomain redirect: `https://{subdomain}.vulneralq.anantacloud.com`
4. ✅ API calls work (check browser console for CORS errors)
5. ✅ No "localhost" references in UI
6. ✅ All redirects use HTTPS

## Files Modified

### Backend:
- `api/src/backend/config/django/base.py` - CORS env vars
- `api/src/backend/config/django/production.py` - Production CORS
- `api/src/backend/config/settings.py` - FRONTEND_URL env var

### Frontend:
- `ui/src/components/TenantRegistration.tsx` - Updated URLs
- `ui/src/components/TenantSetup.tsx` - Updated URLs
- `ui/src/components/LandingPage.tsx` - Updated URLs
- `ui/src/components/TenantVerification.tsx` - Updated URLs
- `ui/app/page.tsx` - Updated URLs
- `ui/lib/helper.ts` - API URL helper

See `PRODUCTION_DEPLOYMENT.md` for detailed instructions.

