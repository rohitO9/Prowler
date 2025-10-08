/**
 * Utility functions for handling subdomain routing
 */

export const getSubdomain = (): string | null => {
  if (typeof window === 'undefined') return null;
  
  const hostname = window.location.hostname;
  
  // Handle localhost development
  if (hostname.includes('localhost')) {
    const parts = hostname.split('.');
    if (parts.length > 1 && parts[0] !== 'www') {
      return parts[0];
    }
    return null;
  }
  
  // Handle production domains
  const parts = hostname.split('.');
  if (parts.length > 2 && parts[0] !== 'www') {
    return parts[0];
  }
  
  return null;
};

export const getMainDomain = (): string => {
  if (typeof window === 'undefined') return '';
  
  const hostname = window.location.hostname;
  const port = window.location.port || '3000';
  
  // Handle localhost development
  if (hostname.includes('localhost')) {
    return `localhost:${port}`;
  }
  
  // Handle production domains
  const parts = hostname.split('.');
  if (parts.length > 2) {
    return parts.slice(-2).join('.');
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
