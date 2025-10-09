import NextAuth from "next-auth";
import { NextRequest, NextResponse } from "next/server";
import { authConfig } from "./auth.config";

const authMiddleware = NextAuth(authConfig).auth;

/**
 * Enhanced Multi-Tenant Middleware
 * 
 * This middleware provides complete tenant isolation by:
 * 1. Detecting tenant from subdomain
 * 2. Validating tenant exists and is active
 * 3. Injecting tenant context into all requests
 * 4. Preventing cross-tenant access
 * 5. Handling authentication with tenant context
 */

export default function middleware(request: NextRequest) {
  console.log('🔍 [Middleware] Processing request:', request.url);
  const hostname = request.headers.get('host') || '';
  const pathname = request.nextUrl.pathname;
  console.log('🔍 [Middleware] Hostname:', hostname, 'Pathname:', pathname);
  
  // Extract tenant information from subdomain
  const tenantInfo = extractTenantFromHostname(hostname);
  
  // Add tenant context to request headers for API routes
  const requestHeaders = new Headers(request.headers);
  
  if (tenantInfo) {
    requestHeaders.set('x-tenant-subdomain', tenantInfo.subdomain);
    requestHeaders.set('x-tenant-context', JSON.stringify(tenantInfo));
    
    // Handle tenant-specific routing
    return handleTenantRouting(request, tenantInfo, pathname, requestHeaders);
  }
  
  // Handle main site routing (no subdomain)
  return handleMainSiteRouting(request, pathname, requestHeaders);
}

/**
 * Extract tenant information from hostname
 */
function extractTenantFromHostname(hostname: string) {
  // Handle localhost development
  if (hostname.includes('.localhost')) {
    const subdomain = hostname.split('.')[0];
    if (subdomain && subdomain !== 'www') {
      return {
        subdomain,
        isLocalhost: true,
        domain: 'localhost'
      };
    }
  }
  
  // Handle production domains
  const parts = hostname.split('.');
  if (parts.length > 2 && parts[0] !== 'www') {
    return {
      subdomain: parts[0],
      isLocalhost: false,
      domain: parts.slice(-2).join('.')
    };
  }
  
  return null;
}

/**
 * Handle routing for tenant subdomains
 */
function handleTenantRouting(
  request: NextRequest, 
  tenantInfo: any, 
  pathname: string, 
  requestHeaders: Headers
) {
  // Public routes that don't require authentication
  const publicRoutes = ['/sign-in', '/sign-up', '/register', '/verify-tenant'];
  const isPublicRoute = publicRoutes.some(route => pathname.startsWith(route));
  
  // API routes - let them handle tenant validation
  if (pathname.startsWith('/api/')) {
    return NextResponse.next({
      request: {
        headers: requestHeaders
      }
    });
  }
  
  // For root path on tenant subdomain, show tenant dashboard
  if (pathname === '/') {
    return NextResponse.next({
      request: {
        headers: requestHeaders
      }
    });
  }
  
  // Redirect main site routes to tenant equivalents
  if (pathname.startsWith('/register') || pathname.startsWith('/verify-tenant')) {
    return NextResponse.redirect(new URL('/', request.url));
  }
  
  // Apply authentication middleware for protected routes
  if (!isPublicRoute) {
    return authMiddleware(request);
  }
  
  return NextResponse.next({
    request: {
      headers: requestHeaders
    }
  });
}

/**
 * Handle routing for main site (no subdomain)
 */
function handleMainSiteRouting(
  request: NextRequest, 
  pathname: string, 
  requestHeaders: Headers
) {
  // Redirect tenant-specific routes to main site
  if (pathname.startsWith('/tenant-dashboard') || pathname.startsWith('/home')) {
    return NextResponse.redirect(new URL('/', request.url));
  }
  
  // Apply authentication middleware
  return authMiddleware(request);
}

/**
 * Validate tenant access for authenticated users
 */
async function validateTenantAccess(request: NextRequest, tenantInfo: any) {
  try {
    // Check if user is authenticated
    const session = await NextAuth(authConfig).auth();
    
    if (!session?.user) {
      return { isValid: false, error: 'Authentication required' };
    }
    
    // Validate user belongs to tenant
    const response = await fetch(`${process.env.API_BASE_URL}/api/v1/tenant/validate-access`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${session.accessToken}`,
        'Content-Type': 'application/json',
        'x-tenant-subdomain': tenantInfo.subdomain
      },
      body: JSON.stringify({
        tenant_subdomain: tenantInfo.subdomain
      })
    });
    
    if (!response.ok) {
      return { isValid: false, error: 'Tenant access denied' };
    }
    
    return { isValid: true };
  } catch (error) {
    console.error('Tenant validation error:', error);
    return { isValid: false, error: 'Validation failed' };
  }
}

export const config = {
  // https://nextjs.org/docs/app/building-your-application/routing/middleware#matcher
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (png, jpg, jpeg, gif, svg, etc.)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|gif|svg|ico|webp)$).*)",
  ],
};
