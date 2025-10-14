/**
 * Next.js middleware for tenant security enforcement.
 * Automatically handles tenant context, authentication, and security validation.
 */

import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import { 
  tenantSecurityManager, 
  TenantContext, 
  SecurityError,
  getTenantContext,
  validateTenantAccess,
  hasPermission
} from '@/lib/tenant-security';

// Security configuration
const SECURITY_CONFIG = {
  // Routes that require authentication
  protectedRoutes: [
    '/dashboard',
    '/settings',
    '/users',
    '/tenants',
    '/admin',
    '/api/protected'
  ],
  
  // Routes that require specific permissions
  permissionRoutes: {
    '/admin': ['admin_access'],
    '/settings': ['manage_settings'],
    '/users': ['invite_users'],
    '/analytics': ['view_analytics']
  },
  
  // Routes that require tenant isolation
  tenantIsolatedRoutes: [
    '/api/tenants',
    '/api/users',
    '/api/data',
    '/api/reports'
  ],
  
  // Public routes that don't require authentication
  publicRoutes: [
    '/',
    '/login',
    '/register',
    '/forgot-password',
    '/reset-password',
    '/api/auth',
    '/api/health',
    '/api/status'
  ]
};

/**
 * Main middleware function for tenant security.
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  try {
    // Skip security checks for public routes
    if (isPublicRoute(pathname)) {
      return NextResponse.next();
    }
    
    // Get tenant context
    const tenantContext = await getTenantContext(request);
    
    // Handle unauthenticated requests
    if (!tenantContext) {
      return handleUnauthenticatedRequest(request);
    }
    
    // Validate tenant access
    if (!validateTenantAccessForRequest(request, tenantContext)) {
      return handleTenantAccessDenied(request, tenantContext);
    }
    
    // Check permissions for protected routes
    if (isProtectedRoute(pathname)) {
      const permissionCheck = await checkRoutePermissions(request, tenantContext, pathname);
      if (!permissionCheck.allowed) {
        return handlePermissionDenied(request, tenantContext, permissionCheck.requiredPermission);
      }
    }
    
    // Enforce tenant isolation for isolated routes
    if (isTenantIsolatedRoute(pathname)) {
      const isolationCheck = await checkTenantIsolation(request, tenantContext);
      if (!isolationCheck.allowed) {
        return handleTenantIsolationViolation(request, tenantContext, isolationCheck.violation);
      }
    }
    
    // Add security headers
    const response = NextResponse.next();
    addSecurityHeaders(response, tenantContext);
    
    // Add tenant context to headers for API routes
    if (pathname.startsWith('/api/')) {
      response.headers.set('X-Tenant-ID', tenantContext.tenantId);
      response.headers.set('X-Tenant-Name', tenantContext.tenantName);
      response.headers.set('X-User-ID', tenantContext.userId);
    }
    
    return response;
    
  } catch (error) {
    console.error('Tenant security middleware error:', error);
    return handleSecurityError(request, error);
  }
}

/**
 * Check if route is public (doesn't require authentication).
 */
function isPublicRoute(pathname: string): boolean {
  return SECURITY_CONFIG.publicRoutes.some(route => 
    pathname === route || pathname.startsWith(route + '/')
  );
}

/**
 * Check if route is protected (requires authentication).
 */
function isProtectedRoute(pathname: string): boolean {
  return SECURITY_CONFIG.protectedRoutes.some(route => 
    pathname.startsWith(route)
  );
}

/**
 * Check if route requires tenant isolation.
 */
function isTenantIsolatedRoute(pathname: string): boolean {
  return SECURITY_CONFIG.tenantIsolatedRoutes.some(route => 
    pathname.startsWith(route)
  );
}

/**
 * Validate tenant access for the request.
 */
function validateTenantAccessForRequest(request: NextRequest, tenantContext: TenantContext): boolean {
  // Extract tenant from subdomain or headers
  const requestTenant = extractTenantFromRequest(request);
  
  if (!requestTenant) {
    return false;
  }
  
  // Validate tenant access
  return validateTenantAccess(tenantContext, requestTenant);
}

/**
 * Extract tenant identifier from request.
 */
function extractTenantFromRequest(request: NextRequest): string | null {
  // Method 1: Extract from subdomain
  const host = request.headers.get('host') || '';
  const subdomain = extractSubdomainFromHost(host);
  
  if (subdomain) {
    return subdomain;
  }
  
  // Method 2: Extract from headers
  const tenantId = request.headers.get('X-Tenant-ID');
  if (tenantId) {
    return tenantId;
  }
  
  // Method 3: Extract from URL path
  const pathname = request.nextUrl.pathname;
  const tenantMatch = pathname.match(/\/api\/tenants\/([^\/]+)/);
  
  if (tenantMatch) {
    return tenantMatch[1];
  }
  
  return null;
}

/**
 * Extract subdomain from host.
 */
function extractSubdomainFromHost(host: string): string | null {
  // Handle localhost development
  if (host.includes('localhost') || host.includes('127.0.0.1')) {
    const parts = host.split('.');
    if (parts.length > 1 && parts[0] !== 'localhost' && parts[0] !== '127') {
      return parts[0];
    }
  }
  
  // Handle production domains
  const parts = host.split('.');
  if (parts.length >= 3) {
    return parts[0];
  }
  
  return null;
}

/**
 * Check route permissions.
 */
async function checkRoutePermissions(
  request: NextRequest, 
  tenantContext: TenantContext, 
  pathname: string
): Promise<{ allowed: boolean; requiredPermission?: string }> {
  // Get required permissions for this route
  const requiredPermissions = getRequiredPermissions(pathname);
  
  if (requiredPermissions.length === 0) {
    return { allowed: true };
  }
  
  // Check if user has any of the required permissions
  for (const permission of requiredPermissions) {
    if (hasPermission(tenantContext, permission)) {
      return { allowed: true };
    }
  }
  
  return { 
    allowed: false, 
    requiredPermission: requiredPermissions[0] 
  };
}

/**
 * Get required permissions for a route.
 */
function getRequiredPermissions(pathname: string): string[] {
  for (const [route, permissions] of Object.entries(SECURITY_CONFIG.permissionRoutes)) {
    if (pathname.startsWith(route)) {
      return permissions;
    }
  }
  return [];
}

/**
 * Check tenant isolation for the request.
 */
async function checkTenantIsolation(
  request: NextRequest, 
  tenantContext: TenantContext
): Promise<{ allowed: boolean; violation?: string }> {
  // Extract resource tenant ID from request
  const resourceTenantId = extractResourceTenantId(request);
  
  if (!resourceTenantId) {
    return { allowed: true };
  }
  
  // Validate tenant access
  if (!validateTenantAccess(tenantContext, resourceTenantId)) {
    return { 
      allowed: false, 
      violation: `Cross-tenant access attempt: ${tenantContext.tenantId} -> ${resourceTenantId}` 
    };
  }
  
  return { allowed: true };
}

/**
 * Extract resource tenant ID from request.
 */
function extractResourceTenantId(request: NextRequest): string | null {
  const pathname = request.nextUrl.pathname;
  
  // Extract from URL path
  const tenantMatch = pathname.match(/\/api\/tenants\/([^\/]+)/);
  if (tenantMatch) {
    return tenantMatch[1];
  }
  
  // Extract from headers
  return request.headers.get('X-Resource-Tenant-ID');
}

/**
 * Handle unauthenticated requests.
 */
function handleUnauthenticatedRequest(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  
  // Redirect to login for protected routes
  if (isProtectedRoute(pathname)) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(loginUrl);
  }
  
  // Return 401 for API routes
  if (pathname.startsWith('/api/')) {
    return NextResponse.json(
      { error: 'Authentication required', code: 'UNAUTHENTICATED' },
      { status: 401 }
    );
  }
  
  return NextResponse.next();
}

/**
 * Handle tenant access denied.
 */
function handleTenantAccessDenied(request: NextRequest, tenantContext: TenantContext): NextResponse {
  const { pathname } = request.nextUrl;
  
  // Log security violation
  console.warn(`[SECURITY] Tenant access denied for user ${tenantContext.userEmail} to ${pathname}`);
  
  // Return 403 for API routes
  if (pathname.startsWith('/api/')) {
    return NextResponse.json(
      { 
        error: 'Tenant access denied', 
        code: 'TENANT_ACCESS_DENIED',
        message: `Access denied to tenant ${tenantContext.tenantName}`,
        tenantId: tenantContext.tenantId
      },
      { status: 403 }
    );
  }
  
  // Redirect to tenant selection or error page
  const errorUrl = new URL('/tenant-access-denied', request.url);
  return NextResponse.redirect(errorUrl);
}

/**
 * Handle permission denied.
 */
function handlePermissionDenied(
  request: NextRequest, 
  tenantContext: TenantContext, 
  requiredPermission: string
): NextResponse {
  const { pathname } = request.nextUrl;
  
  // Log security violation
  console.warn(`[SECURITY] Permission denied for user ${tenantContext.userEmail}: ${requiredPermission}`);
  
  // Return 403 for API routes
  if (pathname.startsWith('/api/')) {
    return NextResponse.json(
      { 
        error: 'Permission denied', 
        code: 'PERMISSION_DENIED',
        message: `Required permission: ${requiredPermission}`,
        requiredPermission
      },
      { status: 403 }
    );
  }
  
  // Redirect to permission denied page
  const errorUrl = new URL('/permission-denied', request.url);
  errorUrl.searchParams.set('permission', requiredPermission);
  return NextResponse.redirect(errorUrl);
}

/**
 * Handle tenant isolation violation.
 */
function handleTenantIsolationViolation(
  request: NextRequest, 
  tenantContext: TenantContext, 
  violation: string
): NextResponse {
  const { pathname } = request.nextUrl;
  
  // Log critical security violation
  console.error(`[SECURITY] CRITICAL: Tenant isolation violation: ${violation}`);
  
  // Return 403 for API routes
  if (pathname.startsWith('/api/')) {
    return NextResponse.json(
      { 
        error: 'Tenant isolation violation', 
        code: 'TENANT_ISOLATION_VIOLATION',
        message: 'Access denied: Cross-tenant data access not allowed',
        violation
      },
      { status: 403 }
    );
  }
  
  // Redirect to security error page
  const errorUrl = new URL('/security-error', request.url);
  return NextResponse.redirect(errorUrl);
}

/**
 * Handle security errors.
 */
function handleSecurityError(request: NextRequest, error: any): NextResponse {
  const { pathname } = request.nextUrl;
  
  console.error(`[SECURITY] Error in middleware:`, error);
  
  // Return 500 for API routes
  if (pathname.startsWith('/api/')) {
    return NextResponse.json(
      { 
        error: 'Security validation failed', 
        code: 'SECURITY_ERROR',
        message: 'An error occurred during security validation'
      },
      { status: 500 }
    );
  }
  
  // Redirect to error page
  const errorUrl = new URL('/error', request.url);
  return NextResponse.redirect(errorUrl);
}

/**
 * Add security headers to response.
 */
function addSecurityHeaders(response: NextResponse, tenantContext: TenantContext): void {
  // Add tenant context headers
  response.headers.set('X-Tenant-ID', tenantContext.tenantId);
  response.headers.set('X-Tenant-Name', tenantContext.tenantName);
  response.headers.set('X-User-ID', tenantContext.userId);
  response.headers.set('X-Security-Level', tenantContext.securityLevel);
  
  // Add security headers
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  
  // Add CSP header for tenant isolation
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "connect-src 'self'",
    `frame-ancestors 'none'`
  ].join('; ');
  
  response.headers.set('Content-Security-Policy', csp);
}

// Configure middleware
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|public/).*)',
  ],
};
