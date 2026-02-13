import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getTenantFromHostname } from '@/lib/tenant';
import { auth } from '@/auth.config';

/**
 * Build a tenant-aware redirect URL that works in both dev and production.
 * Uses the incoming request's protocol and base host to construct the URL.
 */
function buildTenantUrl(
  request: NextRequest,
  tenant: string,
  path: string,
): string {
  const proto = request.headers.get('x-forwarded-proto') || request.nextUrl.protocol.replace(':', '') || 'https';
  const incomingHost = request.headers.get('host') || request.nextUrl.host;

  // Remove port for comparison
  const hostWithoutPort = incomingHost.split(':')[0];
  const parts = hostWithoutPort.split('.');

  // Determine base domain (everything after the tenant part)
  // For localhost: base is "localhost" (port preserved)
  // For production 3-part domain (vulneralq.anantacloud.com): keep all 3 parts
  // For production 4+ part domain: drop the first part (the existing tenant)
  let baseDomain: string;
  const isLocal = hostWithoutPort === 'localhost' || hostWithoutPort === '127.0.0.1'
    || hostWithoutPort.endsWith('.localhost');

  if (isLocal) {
    // Preserve port for localhost
    baseDomain = incomingHost.includes(':')
      ? `localhost:${incomingHost.split(':')[1]}`
      : 'localhost:3000';
  } else if (parts.length >= 4) {
    // Already has a tenant prefix — strip it to get base domain
    baseDomain = parts.slice(1).join('.');
  } else {
    // App domain (e.g. vulneralq.anantacloud.com) — keep as-is
    baseDomain = hostWithoutPort;
  }

  return `${proto}://${tenant}.${baseDomain}${path}`;
}

export async function middleware(request: NextRequest) {
  const hostname = request.headers.get('host') || '';
  const tenant = getTenantFromHostname(hostname);
  const pathname = request.nextUrl.pathname;

  // --- Paths that are allowed WITHOUT a tenant (main domain) ---
  // Tenant registration page + its API route
  const mainDomainAllowedPaths = [
    '/',
    '/api/v1/tenant/register',
    '/api/v1/tenant/register/',
    '/api/v1/tenant/register-tenant',
    '/api/v1/tenant/register-tenant/',
    '/api/v1/tenant/public-info',
    '/api/tenant-info',
  ];

  const isMainDomainAllowed = mainDomainAllowedPaths.some(p =>
    pathname === p || pathname.startsWith(p + '/')
  ) || pathname.startsWith('/api/v1/tenant/register');

  // If no tenant subdomain (main domain)
  if (!tenant) {
    if (isMainDomainAllowed) {
      return NextResponse.next();
    }
    // Redirect all other paths to tenant registration page
    return NextResponse.redirect(new URL('/', request.url));
  }

  // --- With tenant subdomain ---
  const session = await auth();

  // Public paths that don't require authentication (within a tenant)
  const publicPaths = [
    '/sign-in',
    '/accept-invite',
    '/azure-callback',
    '/api/validate-invite',
    '/api/accept-invite',
    '/api/v1/tenant/public-info',
    '/api/v1/tenant/register',
    '/api/tenant-info',
  ];
  const isPublicPath = publicPaths.some(path =>
    pathname.startsWith(path)
  );

  const isPublicRoute = pathname === '/' || isPublicPath;

  // If not public and not authenticated → redirect to sign-in
  if (!isPublicRoute && !session?.user) {
    const signInUrl = buildTenantUrl(request, tenant, '/sign-in?message=session_expired');
    return NextResponse.redirect(new URL(signInUrl, request.url));
  }

  // If user is authenticated — validate tenant matches
  if (session?.user) {
    const userTenant = (session as any).tenantName;

    if (userTenant && userTenant.toLowerCase() !== tenant.toLowerCase()) {
      const signInUrl = buildTenantUrl(request, userTenant.toLowerCase(), '/sign-in?error=cross_tenant_access');
      return NextResponse.redirect(new URL(signInUrl, request.url));
    }
  }

  // Add tenant to headers for downstream API routes
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('X-Tenant-Subdomain', tenant);

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