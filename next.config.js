/** @type {import('next').NextConfig} */

const isDevelopment = process.env.NODE_ENV === 'development';

const cspHeader = isDevelopment
  ? `
    default-src * data: blob:;
    script-src * 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval';
    style-src * 'unsafe-inline';
    img-src * data: blob:;
    font-src * data:;
    connect-src *;
    frame-src *;
    object-src *;
    media-src *;
    frame-ancestors *;
  `
  : `
    default-src 'self';
    img-src 'self' data: https: blob:;
    font-src 'self' data: https:;
    style-src 'self' 'unsafe-inline';
    script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' https://js.stripe.com;
    script-src-elem 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' https://js.stripe.com;
    connect-src 'self' https://api.iconify.design https://api.simplesvg.com https://api.unisvg.com https://js.stripe.com;
    frame-src 'self' https://js.stripe.com;
    frame-ancestors 'none';
  `;

module.exports = {
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  poweredByHeader: false,
  output: "standalone",
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: cspHeader.replace(/\n/g, ' ').trim(),
          },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
};
