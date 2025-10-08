import NextAuth from "next-auth";
import { NextRequest, NextResponse } from "next/server";
import { authConfig } from "./auth.config";

const authMiddleware = NextAuth(authConfig).auth;

export default function middleware(request: NextRequest) {
  const hostname = request.headers.get('host') || '';
  const pathname = request.nextUrl.pathname;
  
  // Handle subdomain routing
  if (hostname.includes('.localhost') && !hostname.startsWith('www.')) {
    const subdomain = hostname.split('.')[0];
    
    // For subdomains, let the LandingPage component handle the routing
    // Don't rewrite here, let the component decide based on auth status
    if (pathname === '/') {
      // Let the page component handle the logic
      return NextResponse.next();
    }
    
    // If accessing main site paths on subdomain, redirect to root
    if (pathname.startsWith('/register') || pathname.startsWith('/verify-tenant')) {
      return NextResponse.redirect(new URL('/', request.url));
    }
  }
  
  // Handle main site routing
  if (!hostname.includes('.localhost') || hostname.startsWith('www.')) {
    // If accessing tenant dashboard on main site, redirect to home
    if (pathname.startsWith('/tenant-dashboard')) {
      return NextResponse.redirect(new URL('/', request.url));
    }
  }
  
  // Apply NextAuth middleware (it will handle public routes based on auth config)
  return authMiddleware(request);
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
