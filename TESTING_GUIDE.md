# Multi-Tenant Security Implementation Testing Guide

## 🎯 Overview
This guide will help you test the complete multi-tenant security implementation we've built. The system includes:

- **Database-level tenant isolation** with unique constraints
- **Automatic tenant detection** from subdomains
- **JWT tokens with tenant information**
- **API endpoint protection** with tenant decorators
- **Frontend tenant routing** and error handling
- **Comprehensive audit logging**

## 🚀 Quick Start Testing

### 1. Backend API Testing

#### Test Tenant Registration
```bash
# Register a new tenant
curl -X POST http://localhost:8080/api/v1/tenant/register \
  -H "Content-Type: application/vnd.api+json" \
  -d '{
    "data": {
      "type": "registration",
      "attributes": {
        "company_name": "Test Company 1",
        "subdomain": "testcompany1",
        "email": "admin@testcompany1.com",
        "password": "securepass123",
        "first_name": "John",
        "last_name": "Doe"
      }
    }
  }'
```

#### Test Tenant Login
```bash
# Login to tenant (simulate subdomain access)
curl -X POST http://localhost:8080/api/v1/tenant/login \
  -H "Content-Type: application/vnd.api+json" \
  -H "Host: testcompany1.localhost:8080" \
  -d '{
    "data": {
      "type": "tokens",
      "attributes": {
        "email": "admin@testcompany1.com",
        "password": "securepass123"
      }
    }
  }'
```

#### Test Cross-Tenant Access Prevention
```bash
# Try to access another tenant's data (should fail)
curl -X GET http://localhost:8080/api/v1/users/me \
  -H "Authorization: Bearer YOUR_TOKEN_FROM_TENANT1" \
  -H "Host: testcompany2.localhost:8080"
```

### 2. Frontend Testing

#### Test Tenant-Specific URLs
1. **Access tenant subdomain**: `http://testcompany1.localhost:3000`
2. **Login page**: `http://testcompany1.localhost:3000/sign-in`
3. **Dashboard**: `http://testcompany1.localhost:3000/dashboard`

#### Test Tenant Isolation
1. **Wrong tenant access**: Try accessing `http://testcompany2.localhost:3000` with tenant1 credentials
2. **Missing tenant**: Try accessing `http://localhost:3000` (should redirect)

### 3. Database Testing

#### Run Django Tests
```bash
cd api/src/backend
python manage.py test tests.test_tenant_isolation
```

#### Test Database Constraints
```bash
# This should fail - duplicate subdomain
python manage.py shell
>>> from api.models import Tenant
>>> Tenant.objects.create(name="Duplicate", subdomain="testcompany1")
```

## 🔍 Detailed Testing Scenarios

### Scenario 1: Tenant Registration Flow
1. **Register new tenant** via API
2. **Verify tenant created** in database
3. **Verify user created** with correct primary_tenant
4. **Test immediate login** with returned tokens
5. **Verify JWT contains tenant info**

### Scenario 2: Cross-Tenant Security
1. **Create two tenants** (tenant1, tenant2)
2. **Create users** for each tenant
3. **Login to tenant1** and get token
4. **Try to access tenant2** with tenant1 token
5. **Verify access denied** with proper error message

### Scenario 3: Subdomain Middleware
1. **Access without subdomain** - should redirect
2. **Access with invalid subdomain** - should show error
3. **Access with valid subdomain** - should work
4. **Check tenant context** in request

### Scenario 4: API Endpoint Protection
1. **Test @require_tenant decorator** - endpoints should reject requests without tenant
2. **Test @require_tenant_admin decorator** - only admins should access admin endpoints
3. **Test tenant-scoped queries** - should only return tenant's data

### Scenario 5: Frontend Tenant Routing
1. **Test middleware** - should extract tenant from hostname
2. **Test tenant validation** - should redirect to correct tenant
3. **Test error handling** - should show tenant-specific errors
4. **Test login flow** - should work with tenant context

## 🛠️ Manual Testing Commands

### Create Test Data
```bash
cd api/src/backend
python manage.py shell

# Create test tenants
from api.models import Tenant, User
tenant1 = Tenant.objects.create(name="Test Company 1", subdomain="test1", is_active=True)
tenant2 = Tenant.objects.create(name="Test Company 2", subdomain="test2", is_active=True)

# Create test users
user1 = User.objects.create_user(
    email="user1@test1.com",
    password="testpass123",
    primary_tenant=tenant1
)
user2 = User.objects.create_user(
    email="user2@test2.com", 
    password="testpass123",
    primary_tenant=tenant2
)
```

### Test Database Constraints
```bash
# This should fail - duplicate subdomain
python manage.py shell
>>> from api.models import Tenant
>>> Tenant.objects.create(name="Duplicate", subdomain="test1")
# Should raise IntegrityError
```

### Test JWT Token Contents
```bash
# Login and decode JWT to verify tenant info
python manage.py shell
>>> from rest_framework_simplejwt.tokens import RefreshToken
>>> from api.models import User, Tenant
>>> user = User.objects.get(email="user1@test1.com")
>>> tenant = user.primary_tenant
>>> refresh = RefreshToken.for_user(user)
>>> refresh['tenant_id'] = str(tenant.id)
>>> refresh['tenant_subdomain'] = tenant.subdomain
>>> print(refresh.access_token)
```

## 🧪 Automated Testing

### Run All Tests
```bash
cd api/src/backend
python manage.py test
```

### Run Specific Test Suite
```bash
python manage.py test tests.test_tenant_isolation
```

### Run with Coverage
```bash
pip install coverage
coverage run manage.py test
coverage report
coverage html
```

## 🔒 Security Verification

### 1. Database Level
- ✅ Unique constraints on subdomain
- ✅ Foreign key constraints
- ✅ Check constraints for validation
- ✅ Indexes for performance

### 2. Application Level
- ✅ Middleware tenant detection
- ✅ JWT token tenant validation
- ✅ API endpoint protection
- ✅ Query filtering by tenant

### 3. Frontend Level
- ✅ Tenant extraction from hostname
- ✅ Middleware tenant validation
- ✅ Error handling for tenant mismatches
- ✅ Redirect to correct tenant

## 📊 Expected Results

### Successful Tests Should Show:
1. **Tenant registration** creates tenant and user
2. **Login** returns JWT with tenant info
3. **Cross-tenant access** is blocked
4. **API endpoints** require tenant context
5. **Frontend routing** works with subdomains
6. **Database constraints** prevent duplicates

### Error Cases Should Show:
1. **Duplicate subdomain** registration fails
2. **Wrong tenant login** is blocked
3. **Missing tenant** requests are rejected
4. **Invalid tokens** are rejected
5. **Cross-tenant data access** is prevented

## 🚨 Troubleshooting

### Common Issues:
1. **Import errors** - Check all imports in models.py
2. **Indentation errors** - Fix Python indentation
3. **Database constraints** - Run migrations
4. **Middleware order** - Check settings.py
5. **Frontend routing** - Check middleware.ts

### Debug Commands:
```bash
# Check Django configuration
python manage.py check

# Check migrations
python manage.py showmigrations

# Check database
python manage.py dbshell

# Check logs
tail -f logs/django.log
```

## ✅ Success Criteria

The implementation is successful when:
1. ✅ **No duplicate tenants** can be created
2. ✅ **Users can only access their tenant**
3. ✅ **API endpoints are tenant-scoped**
4. ✅ **Frontend routing works with subdomains**
5. ✅ **All tests pass**
6. ✅ **Security violations are logged**
7. ✅ **Performance is acceptable**

## 🎉 Next Steps

After successful testing:
1. **Deploy to staging** environment
2. **Run load tests** with multiple tenants
3. **Monitor security logs** for violations
4. **Set up monitoring** and alerting
5. **Document API** for frontend team
6. **Train team** on multi-tenant concepts

---

**Happy Testing! 🚀**

This comprehensive multi-tenant security implementation provides:
- **Database-level isolation** with constraints
- **Application-level security** with middleware
- **API-level protection** with decorators  
- **Frontend-level routing** with tenant detection
- **Audit logging** for security monitoring
- **Comprehensive testing** for verification
