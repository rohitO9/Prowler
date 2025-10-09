"use server";

import { AuthError } from "next-auth";
import { z } from "zod";
import { getApiBaseUrl } from "@/lib/helper";

/**
 * Tenant-Aware Azure AD Authentication Actions
 * 
 * These actions provide secure, tenant-isolated Azure AD authentication:
 * - Login initiation with tenant context
 * - Callback handling with tenant validation
 * - Token refresh with tenant validation
 * - Configuration management for tenant admins
 */

const azureInitSchema = z.object({
  domain_hint: z.string().optional(),
  login_hint: z.string().email().optional(),
});

const azureCallbackSchema = z.object({
  code: z.string().min(1, 'Authorization code is required'),
  state: z.string().optional(),
});

const azureConfigSchema = z.object({
  client_id: z.string().min(1, 'Client ID is required'),
  client_secret: z.string().min(1, 'Client Secret is required'),
  azure_tenant_id: z.string().optional(),
  scopes: z.array(z.string()).default(['openid', 'profile', 'email', 'User.Read']),
  allowed_domains: z.array(z.string()).default([]),
  auto_create_users: z.boolean().default(true),
  require_email_verification: z.boolean().default(false),
});

type AzureInitData = z.infer<typeof azureInitSchema>;
type AzureCallbackData = z.infer<typeof azureCallbackSchema>;
type AzureConfigData = z.infer<typeof azureConfigSchema>;

/**
 * Initialize Azure AD login for current tenant
 */
export async function initiateAzureLogin(
  prevState: unknown,
  formData: AzureInitData
) {
  try {
    console.log("Initiating Azure AD login for tenant");
    
    // Get tenant subdomain from current hostname
    const tenantSubdomain = getCurrentTenantSubdomain();
    if (!tenantSubdomain) {
      return {
        message: "Invalid tenant context",
        errors: {
          tenant: "Unable to determine organization"
        }
      };
    }

    // Validate form data
    const validatedData = azureInitSchema.parse(formData);

    // Call backend to get authorization URL
    const response = await fetch(`${getApiBaseUrl()}/tenant/azure/init`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': tenantSubdomain,
      },
      body: JSON.stringify(validatedData)
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        message: "Failed to initialize Azure login",
        errors: {
          general: errorData.error || "Failed to initialize Azure login"
        }
      };
    }

    const data = await response.json();
    
    // Redirect to Azure AD
    if (typeof window !== 'undefined') {
      window.location.href = data.authorization_url;
    }

    return {
      message: "Redirecting to Azure AD",
      authorization_url: data.authorization_url
    };
  } catch (error) {
    console.error("Azure login initiation error:", error);
    
    if (error instanceof z.ZodError) {
      return {
        message: "Validation failed",
        errors: Object.fromEntries(
          error.errors.map((err) => [err.path[0], err.message])
        )
      };
    }
    
    return {
      message: "Azure login initiation failed",
      errors: {
        general: "An unexpected error occurred. Please try again."
      }
    };
  }
}

/**
 * Handle Azure AD callback and complete authentication
 */
export async function handleAzureCallback(
  prevState: unknown,
  formData: AzureCallbackData
) {
  try {
    console.log("Handling Azure AD callback");
    
    // Get tenant subdomain from current hostname
    const tenantSubdomain = getCurrentTenantSubdomain();
    if (!tenantSubdomain) {
      return {
        message: "Invalid tenant context",
        errors: {
          tenant: "Unable to determine organization"
        }
      };
    }

    // Validate form data
    const validatedData = azureCallbackSchema.parse(formData);

    // Call backend to handle callback
    const response = await fetch(`${getApiBaseUrl()}/tenant/azure/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': tenantSubdomain,
      },
      body: JSON.stringify(validatedData)
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        message: "Authentication failed",
        errors: {
          general: errorData.error || "Authentication failed"
        }
      };
    }

    const data = await response.json();
    
    // Store tokens in localStorage (in production, use secure httpOnly cookies)
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('tenant_id', data.tenant.id);
      localStorage.setItem('user_id', data.user.id);
    }

    return {
      message: "Authentication successful",
      user: data.user,
      tenant: data.tenant,
      membership: data.membership
    };
  } catch (error) {
    console.error("Azure callback error:", error);
    
    if (error instanceof z.ZodError) {
      return {
        message: "Validation failed",
        errors: Object.fromEntries(
          error.errors.map((err) => [err.path[0], err.message])
        )
      };
    }
    
    return {
      message: "Authentication failed",
      errors: {
        general: "An unexpected error occurred. Please try again."
      }
    };
  }
}

/**
 * Refresh Azure AD access token
 */
export async function refreshAzureToken(refreshToken: string) {
  try {
    const tenantSubdomain = getCurrentTenantSubdomain();
    if (!tenantSubdomain) {
      throw new Error("No tenant context");
    }

    const response = await fetch(`${getApiBaseUrl()}/tenant/azure/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': tenantSubdomain,
      },
      body: JSON.stringify({
        refresh_token: refreshToken
      })
    });

    if (!response.ok) {
      throw new Error("Token refresh failed");
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Token refresh error:", error);
    throw error;
  }
}

/**
 * Get Azure AD configuration for current tenant
 */
export async function getAzureConfig() {
  try {
    const tenantSubdomain = getCurrentTenantSubdomain();
    if (!tenantSubdomain) {
      throw new Error("No tenant context");
    }

    const response = await fetch(`${getApiBaseUrl()}/tenant/azure/config`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': tenantSubdomain,
        'Authorization': `Bearer ${getStoredAccessToken()}`,
      }
    });

    if (!response.ok) {
      throw new Error("Failed to fetch Azure configuration");
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Get Azure config error:", error);
    throw error;
  }
}

/**
 * Update Azure AD configuration for current tenant
 */
export async function updateAzureConfig(
  prevState: unknown,
  formData: AzureConfigData
) {
  try {
    console.log("Updating Azure AD configuration");
    
    const tenantSubdomain = getCurrentTenantSubdomain();
    if (!tenantSubdomain) {
      return {
        message: "Invalid tenant context",
        errors: {
          tenant: "Unable to determine organization"
        }
      };
    }

    // Validate form data
    const validatedData = azureConfigSchema.parse(formData);

    const response = await fetch(`${getApiBaseUrl()}/tenant/azure/config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': tenantSubdomain,
        'Authorization': `Bearer ${getStoredAccessToken()}`,
      },
      body: JSON.stringify(validatedData)
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        message: "Configuration update failed",
        errors: {
          general: errorData.error || "Configuration update failed"
        }
      };
    }

    const data = await response.json();
    return {
      message: "Azure AD configuration updated successfully",
      config: data.config
    };
  } catch (error) {
    console.error("Update Azure config error:", error);
    
    if (error instanceof z.ZodError) {
      return {
        message: "Validation failed",
        errors: Object.fromEntries(
          error.errors.map((err) => [err.path[0], err.message])
        )
      };
    }
    
    return {
      message: "Configuration update failed",
      errors: {
        general: "An unexpected error occurred. Please try again."
      }
    };
  }
}

/**
 * Delete Azure AD configuration for current tenant
 */
export async function deleteAzureConfig() {
  try {
    const tenantSubdomain = getCurrentTenantSubdomain();
    if (!tenantSubdomain) {
      throw new Error("No tenant context");
    }

    const response = await fetch(`${getApiBaseUrl()}/tenant/azure/config`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': tenantSubdomain,
        'Authorization': `Bearer ${getStoredAccessToken()}`,
      }
    });

    if (!response.ok) {
      throw new Error("Failed to delete Azure configuration");
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Delete Azure config error:", error);
    throw error;
  }
}

/**
 * Get Azure AD login URL for current tenant
 */
export async function getAzureLoginUrl() {
  try {
    const tenantSubdomain = getCurrentTenantSubdomain();
    if (!tenantSubdomain) {
      throw new Error("No tenant context");
    }

    const response = await fetch(`${getApiBaseUrl()}/tenant/azure/login-url`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': tenantSubdomain,
        'Authorization': `Bearer ${getStoredAccessToken()}`,
      }
    });

    if (!response.ok) {
      throw new Error("Failed to get Azure login URL");
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Get Azure login URL error:", error);
    throw error;
  }
}

/**
 * Validate user access to current tenant
 */
export async function validateTenantAccess(tenantSubdomain: string) {
  try {
    const response = await fetch(`${getApiBaseUrl()}/tenant/validate-access`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': tenantSubdomain,
        'Authorization': `Bearer ${getStoredAccessToken()}`,
      },
      body: JSON.stringify({
        tenant_subdomain: tenantSubdomain
      })
    });

    return response.ok;
  } catch (error) {
    console.error("Tenant access validation error:", error);
    return false;
  }
}

/**
 * Get current tenant subdomain from hostname
 */
function getCurrentTenantSubdomain(): string | null {
  if (typeof window === 'undefined') return null;
  
  const hostname = window.location.hostname;
  
  // Handle localhost development
  if (hostname.includes('.localhost')) {
    const subdomain = hostname.split('.')[0];
    if (subdomain && subdomain !== 'www') {
      return subdomain;
    }
  }
  
  // Handle production domains
  const parts = hostname.split('.');
  if (parts.length > 2 && parts[0] !== 'www') {
    return parts[0];
  }
  
  return null;
}

/**
 * Get stored access token
 */
function getStoredAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

/**
 * Check if user is authenticated with valid tenant access
 */
export async function checkAzureAuthStatus() {
  try {
    const accessToken = getStoredAccessToken();
    if (!accessToken) {
      return { authenticated: false, reason: 'No access token' };
    }

    const tenantSubdomain = getCurrentTenantSubdomain();
    if (!tenantSubdomain) {
      return { authenticated: false, reason: 'No tenant context' };
    }

    const isValid = await validateTenantAccess(tenantSubdomain);
    return { authenticated: isValid, reason: isValid ? 'Valid' : 'Invalid tenant access' };
  } catch (error) {
    console.error("Auth status check error:", error);
    return { authenticated: false, reason: 'Check failed' };
  }
}
