/**
 * API utility functions for handling subdomain-based API calls
 */

export const getApiBaseUrl = (): string => {
  if (typeof window === 'undefined') return '';
  
  const hostname = window.location.hostname;
  const port = '8080'; // Backend API port
  
  // Handle localhost development
  if (hostname.includes('localhost')) {
    return `http://localhost:${port}`;
  }
  
  // Handle production - assume API is on same domain but different port
  return `https://${hostname}:${port}`;
};

export const getApiUrl = (endpoint: string): string => {
  const baseUrl = getApiBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${baseUrl}/api/v1${cleanEndpoint}`;
};

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

export const isOnSubdomain = (): boolean => {
  return getSubdomain() !== null;
};
