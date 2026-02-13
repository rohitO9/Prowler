import { DEV_APP_PORT, DEV_DOMAIN, isDevHost } from "@/lib/env";

/**
 * Utility functions for handling subdomain routing.
 *
 * Two-level subdomain rule: we only treat the host as a tenant subdomain when
 * there are at least two levels of subdomain (e.g. tenant1.valnarq.ananracloude.com).
 * Then the tenant is the leftmost segment (tenant1). Single-level subdomains
 * (e.g. valnarq.vaniva.shop) are treated as the app domain, not a tenant.
 */

/**
 * Extract tenant subdomain from a host string (hostname or host:port).
 * Returns the first segment only when the host has two-level subdomain:
 * - Production: 4+ parts (e.g. tenant1.valnarq.ananracloude.com → "tenant1")
 * - Dev (localhost): 2+ parts (e.g. company1.localhost → "company1")
 * Otherwise returns null (e.g. valnarq.vaniva.shop → null).
 */
export function getSubdomainFromHost(host: string): string | null {
  if (!host || typeof host !== "string") return null;
  const hostname = host.split(":")[0].trim();
  const parts = hostname.split(".");

  if (isDevHost(hostname)) {
    if (parts.length > 1 && parts[0] !== "www") return parts[0];
    return null;
  }

  if (parts.length >= 4 && parts[0] !== "www") return parts[0];
  return null;
}

export const getSubdomain = (): string | null => {
  if (typeof window === 'undefined') return null;
  return getSubdomainFromHost(window.location.hostname);
};

export const getMainDomain = (): string => {
  if (typeof window === "undefined") return "";

  const hostname = window.location.hostname;
  const port = window.location.port || DEV_APP_PORT;

  if (isDevHost(hostname)) {
    return `${DEV_DOMAIN}:${port}`;
  }

  const parts = hostname.split(".");
  if (parts.length > 2) {
    return parts.slice(-2).join(".");
  }
  return hostname;
};

export const redirectToSubdomain = (subdomain: string): void => {
  if (typeof window === 'undefined') return;
  
  const mainDomain = getMainDomain();
  const protocol = window.location.protocol;
  const port = window.location.port ? `:${window.location.port}` : '';
  
  const newUrl = `${protocol}//${subdomain}.${mainDomain}${port}`;
  window.location.href = newUrl;
};

export const isOnSubdomain = (): boolean => {
  return getSubdomain() !== null;
};

export const getTenantInfo = async (): Promise<any> => {
  try {
    // Try to get authentication headers first
    const { getAuthHeaders } = await import('@/lib/helper');
    let headers;
    let endpoint = '/api/v1/tenant/public-info'; // Default to public endpoint
    
    try {
      headers = await getAuthHeaders({ contentType: false });
      // If we have auth headers, use the authenticated endpoint
      endpoint = '/api/v1/tenant/info';
    } catch (authError) {
      // No authentication available, use public endpoint without headers
      headers = {
        'Accept': 'application/vnd.api+json'
      };
    }
    
    const response = await fetch(endpoint, {
      headers
    });
    if (response.ok) {
      return await response.json();
    }
    return null;
  } catch (error) {
    console.error('Failed to get tenant info:', error);
    return null;
  }
};
