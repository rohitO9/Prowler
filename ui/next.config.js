/** @type {import('next').NextConfig} */

const isDevelopment = process.env.NODE_ENV === 'development';

// Production CSP - more restrictive
const productionCspHeader = `
  default-src 'self';
  img-src 'self' data: https: blob:;
  font-src 'self' data: https:;
  style-src 'self' 'unsafe-inline';
  script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' https://js.stripe.com;
  script-src-elem 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' https://js.stripe.com;
  connect-src 'self' https://api.iconify.design https://api.simplesvg.com https://api.unisvg.com https://js.stripe.com https://api.stripe.com;
  frame-src 'self' https://js.stripe.com https://hooks.stripe.com;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
  object-src 'none';
  upgrade-insecure-requests;
`;

// Development CSP - very permissive
const developmentCspHeader = `
  default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;
  script-src * 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval';
  script-src-elem * 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval';
  style-src * 'unsafe-inline';
  img-src * data: blob:;
  font-src * data:;
  connect-src *;
  frame-src *;
  object-src *;
  media-src *;
  frame-ancestors *;
`;

module.exports = {
  eslint: { 
    ignoreDuringBuilds: true 
  },
  typescript: { 
    ignoreBuildErrors: true 
  },
  poweredByHeader: false,
  output: "standalone",
  
  async headers() {
    const cspValue = isDevelopment 
      ? developmentCspHeader 
      : productionCspHeader;

    // Clean up the CSP string: remove newlines, multiple spaces
    const cleanCsp = cspValue
      .replace(/\s{2,}/g, ' ')
      .replace(/\n/g, ' ')
      .trim();

    const headers = [
      {
        key: 'Content-Security-Policy',
        value: cleanCsp,
      },
    ];

    // Add additional security headers only in production
    if (!isDevelopment) {
      headers.push(
        { 
          key: 'X-Content-Type-Options', 
          value: 'nosniff' 
        },
        { 
          key: 'X-Frame-Options', 
          value: 'DENY' 
        },
        { 
          key: 'X-XSS-Protection', 
          value: '1; mode=block' 
        },
        { 
          key: 'Referrer-Policy', 
          value: 'strict-origin-when-cross-origin' 
        },
        {
          key: 'Permissions-Policy',
          value: 'camera=(), microphone=(), geolocation=()'
        }
      );
    }

    return [
      {
        // Match all routes
        source: '/:path*',
        headers: headers,
      },
    ];
  },
};