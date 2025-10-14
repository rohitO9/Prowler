/**
 * Extract tenant subdomain from hostname
 */
export function getTenantFromHostname(hostname: string): string | null {
  // Remove port if present
  const host = hostname.split(':')[0].toLowerCase();
  
  // Split by dots
  const parts = host.split('.');
  
  // Handle different scenarios:
  // - localhost -> null
  // - company1.localhost -> company1
  // - company1.example.com -> company1
  // - www.example.com -> null
  
  if (parts.length < 2) {
    return null; // Just 'localhost' or similar
  }
  
  const subdomain = parts[0];
  
  // Ignore common subdomains
  const ignoredSubdomains = ['www', 'api', 'localhost', '127'];
  if (ignoredSubdomains.includes(subdomain)) {
    return null;
  }
  
  // Validate subdomain format
  const subdomainRegex = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/;
  if (!subdomainRegex.test(subdomain)) {
    return null;
  }
  
  return subdomain;
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
