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
  const publicPaths = ['/sign-in', '/sign-up', '/register', '/health'];
  const isPublicPath = publicPaths.some(path => 
    request.nextUrl.pathname.startsWith(path)
  );
  
  // If no tenant subdomain
  if (!tenant) {
    // Redirect to tenant selection or main landing page
    if (!isPublicPath && request.nextUrl.pathname !== '/') {
      return NextResponse.redirect(new URL('/', request.url));
    }
    return NextResponse.next();
  }
  
  // ✅ CRITICAL: Check if user is authenticated for protected routes
  const protectedRoutes = ['/home', '/dashboard', '/profile', '/settings', '/admin'];
  const isProtectedRoute = protectedRoutes.some(route => 
    request.nextUrl.pathname.startsWith(route)
  );
  
  // If accessing protected route without authentication, redirect to sign-in
  if (isProtectedRoute && !session?.user) {
    console.log(`🔒 [Middleware] Unauthenticated access to protected route: ${request.nextUrl.pathname}`);
    return NextResponse.redirect(new URL('/sign-in?message=session_expired', request.url));
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
      
      // Redirect to correct tenant or logout
      const correctUrl = new URL(request.nextUrl.pathname, request.url);
      correctUrl.hostname = `${userTenant.toLowerCase()}.localhost`;
      
      return NextResponse.redirect(correctUrl);
    }
    
    // If user has no tenant info, they shouldn't access tenant-specific pages
    if (!userTenant && tenant) {
      console.error(
        `🚨 [Middleware] User has no tenant info but trying to access tenant: ${tenant}`
      );
      
      // Redirect to logout or tenant selection
      return NextResponse.redirect(new URL('/sign-in', request.url));
    }
    
    // ✅ CRITICAL: Prevent cross-tenant access (case-insensitive)
    // If user is trying to access a different tenant's dashboard, deny access
    if (userTenant && tenant && userTenant.toLowerCase() !== tenant.toLowerCase()) {
      console.error(
        `🚨 [Middleware] Cross-tenant access denied! ` +
        `User belongs to: ${userTenant}, trying to access: ${tenant}`
      );
      
      // Show error page or redirect to user's correct tenant
      const errorUrl = new URL('/sign-in?error=tenant_mismatch', request.url);
      errorUrl.hostname = `${userTenant.toLowerCase()}.localhost`;
      
      return NextResponse.redirect(errorUrl);
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