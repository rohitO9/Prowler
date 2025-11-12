//disable eslint
/* eslint-disable */
'use client';

import React, { useState, useEffect, useCallback, useContext, createContext, ReactNode } from 'react';
import { useSession } from 'next-auth/react';

/**
 * Tenant Context for Multi-Tenant Application
 * 
 * This hook provides complete tenant management including:
 * - Tenant detection from subdomain
 * - Tenant validation and access control
 * - Tenant-specific API calls
 * - Tenant context throughout the application
 */

interface TenantInfo {
  id: string;
  name: string;
  subdomain: string;
  domain?: string;
  is_active: boolean;
  is_verified: boolean;
  contact_email: string;
  logo_url?: string;
  theme_color: string;
  secondary_color: string;
  subscription_status: 'trial' | 'active' | 'suspended' | 'cancelled';
  trial_ends_at?: string;
  allow_registration: boolean;
  require_email_verification: boolean;
}

interface TenantMembership {
  role: 'owner' | 'admin' | 'member' | 'viewer';
  permissions: {
    can_invite_users: boolean;
    can_manage_settings: boolean;
    can_view_analytics: boolean;
  };
  joined_at: string;
}

interface TenantContextType {
  tenant: TenantInfo | null;
  membership: TenantMembership | null;
  isLoading: boolean;
  error: string | null;
  getCurrentTenant: () => Promise<TenantInfo | null>;
  validateTenantAccess: (subdomain: string) => Promise<boolean>;
  refreshTenant: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  canAccessFeature: (feature: string) => boolean;
}

export const TenantContext = createContext<TenantContextType | null>(null);

export const useTenant = () => {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error('useTenant must be used within a TenantProvider');
  }
  return context;
};

export const TenantProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [membership, setMembership] = useState<TenantMembership | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { data: session, status } = useSession();

  /**
   * Extract subdomain from current hostname
   */
  const getSubdomain = useCallback(() => {
    if (typeof window === 'undefined') return null;
    
    const hostname = window.location.hostname;
    console.log('🔍 [getSubdomain] Current hostname:', hostname);
    
    // Handle localhost development
    if (hostname.includes('.localhost')) {
      const subdomain = hostname.split('.')[0];
      console.log('🔍 [getSubdomain] Extracted subdomain:', subdomain);
      if (subdomain && subdomain !== 'www') {
        return subdomain;
      }
    }
    
    // Handle production domains
    const parts = hostname.split('.');
    if (parts.length > 2 && parts[0] !== 'www') {
      console.log('🔍 [getSubdomain] Production subdomain:', parts[0]);
      return parts[0];
    }
    
    console.log('🔍 [getSubdomain] No subdomain found');
    return null;
  }, []);

  /**
   * Get current tenant information
   */
  const getCurrentTenant = useCallback(async (): Promise<TenantInfo | null> => {
    try {
      const subdomain = getSubdomain();
      console.log('🔍 [getCurrentTenant] Subdomain:', subdomain);
      if (!subdomain) {
        console.log('🔍 [getCurrentTenant] No subdomain, returning null');
        return null;
      }

      const url = '/api/v1/tenant/public-info';
      console.log('🔍 [getCurrentTenant] Fetching from URL:', url);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      console.log('🔍 [getCurrentTenant] Response status:', response.status);
      console.log('🔍 [getCurrentTenant] Response ok:', response.ok);

      if (!response.ok) {
        throw new Error(`Failed to fetch tenant info: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('🔍 [useTenant] API Response:', data);
      console.log('🔍 [useTenant] data.data:', data.data);
      console.log('🔍 [useTenant] data.data?.tenant:', data.data?.tenant);
      
      const result = data.data?.tenant || data.data;
      console.log('🔍 [useTenant] Final result:', result);
      
      // Handle API response structure: data.data.tenant
      return result;
    } catch (error) {
      console.error('❌ [getCurrentTenant] Error fetching tenant info:', error);
      console.error('❌ [getCurrentTenant] Error details:', {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined,
        error: error
      });
      throw error;
    }
  }, [getSubdomain]);

  /**
   * Validate user access to tenant
   */
  const validateTenantAccess = useCallback(async (subdomain: string): Promise<boolean> => {
    try {
      if (!session?.accessToken) {
        return false;
      }

      const response = await fetch('/api/v1/tenant/validate-access', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tenant_subdomain: subdomain
        })
      });

      return response.ok;
    } catch (error) {
      console.error('Error validating tenant access:', error);
      return false;
    }
  }, [session]);

  /**
   * Get authenticated tenant information
   */
  const getAuthenticatedTenant = useCallback(async (): Promise<{
    tenant: TenantInfo;
    membership: TenantMembership;
  } | null> => {
    try {
      if (!session?.accessToken) {
        return null;
      }

      const response = await fetch('/api/v1/tenant/info', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${session.accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch authenticated tenant info: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        tenant: data.data?.attributes || data.data,
        membership: data.membership
      };
    } catch (error) {
      console.error('Error fetching authenticated tenant info:', error);
      throw error;
    }
  }, [session]);

  /**
   * Refresh tenant information
   */
  const refreshTenant = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const subdomain = getSubdomain();
      if (!subdomain) {
        setTenant(null);
        setMembership(null);
        return;
      }

      // If user is authenticated, get full tenant info with membership
      if (session?.user) {
        const authenticatedData = await getAuthenticatedTenant();
        if (authenticatedData) {
          setTenant(authenticatedData.tenant);
          setMembership(authenticatedData.membership);
          return;
        }
      }

      // Otherwise, get public tenant info
      const tenantInfo = await getCurrentTenant();
      console.log('🔍 [TenantProvider] Setting tenant:', tenantInfo);
      setTenant(tenantInfo);
      setMembership(null);
    } catch (error) {
      console.error('Error refreshing tenant:', error);
      setError(error instanceof Error ? error.message : 'Failed to load tenant information');
    } finally {
      setIsLoading(false);
    }
  }, [getSubdomain, session, getCurrentTenant, getAuthenticatedTenant]);

  /**
   * Check if user has specific permission
   */
  const hasPermission = useCallback((permission: string): boolean => {
    if (!membership) return false;
    return membership.permissions[permission as keyof typeof membership.permissions] || false;
  }, [membership]);

  /**
   * Check if tenant can access specific feature
   */
  const canAccessFeature = useCallback((feature: string): boolean => {
    if (!tenant) return false;
    
    // Basic subscription check
    if (tenant.subscription_status === 'active') return true;
    if (tenant.subscription_status === 'trial' && !tenant.trial_ends_at) return true;
    if (tenant.subscription_status === 'trial' && tenant.trial_ends_at) {
      const trialEnd = new Date(tenant.trial_ends_at);
      return trialEnd > new Date();
    }
    
    return false;
  }, [tenant]);

  // Load tenant information on mount and when session changes
  useEffect(() => {
    refreshTenant();
  }, [refreshTenant]);

  const contextValue: TenantContextType = {
    tenant,
    membership,
    isLoading,
    error,
    getCurrentTenant,
    validateTenantAccess,
    refreshTenant,
    hasPermission,
    canAccessFeature,
  };

  return (
    <TenantContext.Provider value={contextValue}>
      {children}
    </TenantContext.Provider>
  );
};

/**
 * Hook to get tenant information without context
 */
export const useTenantInfo = () => {
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const getSubdomain = useCallback(() => {
    if (typeof window === 'undefined') return null;
    
    const hostname = window.location.hostname;
    
    if (hostname.includes('.localhost')) {
      const subdomain = hostname.split('.')[0];
      if (subdomain && subdomain !== 'www') {
        return subdomain;
      }
    }
    
    const parts = hostname.split('.');
    if (parts.length > 2 && parts[0] !== 'www') {
      return parts[0];
    }
    
    return null;
  }, []);

  const loadTenant = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const subdomain = getSubdomain();
      if (!subdomain) {
        setTenant(null);
        return;
      }

      const response = await fetch('/api/v1/tenant/public-info');
      if (!response.ok) {
        throw new Error('Failed to fetch tenant information');
      }

      const data = await response.json();
      
      const result = data.data?.tenant || data.data;
      
      // Handle API response structure: data.data.tenant
      setTenant(result);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to load tenant');
    } finally {
      setIsLoading(false);
    }
  }, [getSubdomain]);

  useEffect(() => {
    loadTenant();
  }, [loadTenant]);

  return { tenant, isLoading, error, refreshTenant: loadTenant };
};

/**
 * Hook to check if current user belongs to current tenant
 */
export const useTenantMembership = () => {
  const { data: session } = useSession();
  const [isMember, setIsMember] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const checkMembership = useCallback(async () => {
    if (!session?.user) {
      setIsMember(false);
      setIsLoading(false);
      return;
    }

    try {
      const subdomain = window.location.hostname.split('.')[0];
      const response = await fetch('/api/v1/tenant/validate-access', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tenant_subdomain: subdomain })
      });

      setIsMember(response.ok);
    } catch (error) {
      console.error('Error checking membership:', error);
      setIsMember(false);
    } finally {
      setIsLoading(false);
    }
  }, [session]);

  useEffect(() => {
    checkMembership();
  }, [checkMembership]);

  return { isMember, isLoading };
};

