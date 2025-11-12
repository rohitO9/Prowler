import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getTenantFromHostname } from '@/lib/tenant';
import { auth } from '@/auth.config';

export async function middleware(request: NextRequest) {
  const hostname = request.headers.get('host') || '';
  const tenant = getTenantFromHostname(hostname);
  const session = await auth();
  
  // Production: Logging removed for performance and security
  
  // SECURITY: Multi-tenant application - all routes require tenant subdomain
  // Only exception: tenant registration page on main domain
  const isTenantRegistrationPage = request.nextUrl.pathname === '/' && !tenant;
  
  // If no tenant subdomain (main domain)
  if (!tenant) {
    // SECURITY: Only allow tenant registration page on main domain
    // All other routes require tenant subdomain
    if (isTenantRegistrationPage) {
      return NextResponse.next();
    }
    // Redirect all other paths to tenant registration page
    return NextResponse.redirect(new URL('/', request.url));
  }
  
  // With tenant subdomain: define public paths that don't require authentication
  const publicPaths = [
    '/sign-in',
    '/accept-invite',
    '/azure-callback',
    '/api/validate-invite',
    '/api/accept-invite',
    '/api/v1/tenant/public-info',
  ];
  const isPublicPath = publicPaths.some(path => 
    request.nextUrl.pathname.startsWith(path)
  );
  
  // SECURITY: Tenant validation is handled by API routes and pages
  // Middleware just enforces routing rules - actual tenant existence is validated server-side
  
  // ✅ SIMPLE RULE: If no token, redirect to sign-in for any non-public page
  const isPublicRoute = request.nextUrl.pathname === '/' || isPublicPath;
  
  if (!isPublicRoute && !session?.user) {
    return NextResponse.redirect(new URL(`http://${tenant}.localhost:3000/sign-in?message=session_expired`, request.url));
  }
  
  // If user is authenticated
  if (session?.user) {
    // Get tenant from session (stored in JWT token)
    const userTenant = (session as any).tenantName;
    
    // ✅ CRITICAL: Validate user's tenant matches URL tenant (case-insensitive)
    if (userTenant && userTenant.toLowerCase() !== tenant.toLowerCase()) {
      // Security: Tenant mismatch detected - redirect to user's correct tenant
      const signInUrl = new URL(`http://${userTenant.toLowerCase()}.localhost:3000/sign-in?error=cross_tenant_access`, request.url);
      return NextResponse.redirect(signInUrl);
    }
    
    // If user has no tenant info, allow access but don't redirect (user info might not be loaded yet)
    if (!userTenant && tenant) {
      // Don't redirect - let the page handle the missing user info
    }
  }
  
  // Add tenant to headers for API routes
  const requestHeaders = new Headers(request.headers);
  if (tenant) {
    requestHeaders.set('X-Tenant-Subdomain', tenant);
  }
  
  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - api/auth (NextAuth)
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico (favicon)
     */
    '/((?!api/auth|_next/static|_next/image|favicon.ico).*)',
  ],
};