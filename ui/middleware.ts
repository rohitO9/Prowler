import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getTenantFromHostname } from '@/lib/tenant';
import { auth } from '@/auth.config';

export async function middleware(request: NextRequest) {
  const hostname = request.headers.get('host') || '';
  const tenant = getTenantFromHostname(hostname);
  const session = await auth();
  
  console.log('🔍 [Middleware] Processing:', {
    hostname,
    tenant,
    path: request.nextUrl.pathname,
    authenticated: !!session?.user,
  });
  
  // Public paths that don't need tenant
  const publicPaths = [
    '/sign-in', 
    '/sign-up', 
    '/register', 
    '/health',
    '/accept-invite',
    '/azure-callback',
    '/api/validate-invite',
    '/api/accept-invite',
    '/api/tenant-info',
    '/api/sso-config',
    '/api/v1/tenant/register',
    '/api/v1/tenant/register-tenant',
    '/api/v1/tenant/public-info',
    '/api/v1/tenant/sync-users',
    '/api/v1/tenant/invite-user',
    '/api/v1/tenant/users'
  ];
  const isPublicPath = publicPaths.some(path => 
    request.nextUrl.pathname.startsWith(path)
  );
  
  // If no tenant subdomain (main domain)
  if (!tenant) {
    // Allow access to landing page and public paths
    if (request.nextUrl.pathname === '/' || isPublicPath) {
      return NextResponse.next();
    }
    // Redirect other paths to landing page
    return NextResponse.redirect(new URL('/', request.url));
  }
  
  // ✅ SIMPLE RULE: If no token, redirect to sign-in for any non-public page
  const isPublicRoute = request.nextUrl.pathname === '/' || isPublicPath;
  
  if (!isPublicRoute && !session?.user) {
    console.log(`🔒 [Middleware] No token - redirecting to sign-in: ${request.nextUrl.pathname}`);
    return NextResponse.redirect(new URL(`http://${tenant}.localhost:3000/sign-in?message=session_expired`, request.url));
  }
  
  // If user is authenticated
  if (session?.user) {
    // Get tenant from session (stored in JWT token)
    const userTenant = (session as any).tenantName;
    
    // ✅ CRITICAL: Validate user's tenant matches URL tenant (case-insensitive)
    if (userTenant && userTenant.toLowerCase() !== tenant.toLowerCase()) {
      console.error(
        `🚨 [Middleware] Tenant mismatch! ` +
        `User tenant: ${userTenant}, URL tenant: ${tenant}`
      );
      
      // Redirect to sign-in with cross-tenant error message
      const signInUrl = new URL(`http://${userTenant.toLowerCase()}.localhost:3000/sign-in?error=cross_tenant_access`, request.url);
      
      return NextResponse.redirect(signInUrl);
    }
    
    // If user has no tenant info, allow access but don't redirect (user info might not be loaded yet)
    if (!userTenant && tenant) {
      console.log(
        `ℹ️ [Middleware] User has no tenant info yet, allowing access to: ${request.nextUrl.pathname}`
      );
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