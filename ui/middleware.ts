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
  
  // If user is authenticated
  if (session?.user) {
    const userTenant = session.user.tenant_subdomain;
    
    // ✅ CRITICAL: Validate user's tenant matches URL tenant
    if (userTenant !== tenant) {
      console.error(
        `🚨 [Middleware] Tenant mismatch! ` +
        `User tenant: ${userTenant}, URL tenant: ${tenant}`
      );
      
      // Redirect to correct tenant or logout
      const correctUrl = new URL(request.nextUrl.pathname, request.url);
      correctUrl.hostname = `${userTenant}.localhost`;
      
      return NextResponse.redirect(correctUrl);
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