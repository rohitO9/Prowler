/**
 * Extract tenant subdomain from hostname using two-level subdomain logic.
 *
 * Production (e.g. vulneralq.anantacloud.com = 3 parts → NO tenant):
 *   - 3 parts or fewer = app domain, return null
 *   - 4+ parts = tenant subdomain (e.g. tenant1.vulneralq.anantacloud.com → "tenant1")
 *
 * Localhost / dev:
 *   - localhost → null
 *   - company1.localhost → "company1"
 */
export function getTenantFromHostname(hostname: string): string | null {
  if (!hostname) return null;

  // Remove port if present
  const host = hostname.split(':')[0].toLowerCase().trim();
  if (!host) return null;

  // Split by dots
  const parts = host.split('.');

  // --- Localhost / 127.0.0.1 / dev ---
  const isLocal = host === 'localhost' || host === '127.0.0.1'
    || host.endsWith('.localhost') || host.endsWith('.127.0.0.1');

  if (isLocal) {
    // company1.localhost → "company1"
    if (parts.length >= 2 && parts[0] !== 'www') {
      return parts[0];
    }
    return null;
  }

  // --- Production ---
  // Ignore common non-tenant subdomains
  const ignoredSubdomains = ['www', 'api'];

  // Two-level subdomain: only extract tenant when host has 4+ parts
  // e.g. tenant1.vulneralq.anantacloud.com (4 parts) → "tenant1"
  // e.g. vulneralq.anantacloud.com (3 parts) → null  (this is the app domain)
  if (parts.length >= 4) {
    const subdomain = parts[0];
    if (ignoredSubdomains.includes(subdomain)) return null;

    // Validate subdomain format
    const subdomainRegex = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/;
    if (!subdomainRegex.test(subdomain)) return null;

    return subdomain;
  }

  return null;
}

/**
 * Get tenant from Next.js request
 */
export function getTenantFromRequest(request: Request): string | null {
  const hostname = request.headers.get('host') || '';
  return getTenantFromHostname(hostname);
}

/**
 * Build tenant URL
 */
export function getTenantUrl(subdomain: string, path: string = '/'): string {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
  const url = new URL(baseUrl);
  
  // Set subdomain
  url.hostname = `${subdomain}.${url.hostname}`;
  url.pathname = path;
  
  return url.toString();
}

/**
 * Validate tenant exists
 */
export async function validateTenant(subdomain: string): Promise<boolean> {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
    const response = await fetch(`${apiUrl}/api/v1/tenant/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/vnd.api+json',
      },
      body: JSON.stringify({
        data: {
          type: 'tenant-validation',
          attributes: {
            subdomain,
          },
        },
      }),
    });
    
    return response.ok;
  } catch (error) {
    console.error('Error validating tenant:', error);
    return false;
  }
}
