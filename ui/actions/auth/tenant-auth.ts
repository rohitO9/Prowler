"use server";

import { AuthError } from "next-auth";
import { z } from "zod";
import { signIn, signOut } from "@/auth.config";
import { getApiBaseUrl } from "@/lib/helper";

/**
 * Tenant-Aware Authentication Actions
 * 
 * These actions provide secure, tenant-isolated authentication:
 * - Login with tenant validation
 * - Registration with tenant context
 * - Token refresh with tenant validation
 * - Logout with tenant cleanup
 */

const tenantLoginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
  tenant_subdomain: z.string().optional(),
});

const tenantRegisterSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(12, 'Password must be at least 12 characters'),
  confirmPassword: z.string(),
  tenant_subdomain: z.string().optional(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type TenantLoginData = z.infer<typeof tenantLoginSchema>;
type TenantRegisterData = z.infer<typeof tenantRegisterSchema>;

/**
 * Authenticate user with tenant validation
 */
export async function authenticateWithTenant(
  prevState: unknown,
  formData: TenantLoginData
) {
  try {
    console.log("Attempting tenant-aware authentication for:", formData.email);
    
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
    const validatedData = tenantLoginSchema.parse({
      ...formData,
      tenant_subdomain: tenantSubdomain
    });

    // Attempt authentication with tenant context
    const result = await signIn("credentials", {
      email: validatedData.email,
      password: validatedData.password,
      tenant_subdomain: tenantSubdomain,
      redirect: false,
    });

    if (result?.error) {
      return {
        message: "Authentication failed",
        errors: {
          credentials: "Invalid email or password"
        }
      };
    }

    return {
      message: "Success",
    };
  } catch (error) {
    console.error("Tenant authentication error:", error);
    
    if (error instanceof z.ZodError) {
      return {
        message: "Validation failed",
        errors: Object.fromEntries(
          error.errors.map((err) => [err.path[0], err.message])
        )
      };
    }
    
    if (error instanceof AuthError) {
      switch (error.type) {
        case "CredentialsSignin":
          return {
            message: "Invalid credentials",
            errors: {
              credentials: "Invalid email or password"
            }
          };
        case "CallbackRouteError":
          return {
            message: "Authentication error",
            errors: {
              general: error.cause?.err?.message || "Authentication failed"
            }
          };
        default:
          return {
            message: "Authentication error",
            errors: {
              general: error.message || "Authentication failed"
            }
          };
      }
    }
    
    return {
      message: "Unexpected error",
      errors: {
        general: "An unexpected error occurred. Please try again."
      }
    };
  }
}

/**
 * Register new user for specific tenant
 */
export async function registerWithTenant(
  prevState: unknown,
  formData: TenantRegisterData
) {
  try {
    console.log("Attempting tenant-aware registration for:", formData.email);
    
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
    const validatedData = tenantRegisterSchema.parse({
      ...formData,
      tenant_subdomain: tenantSubdomain
    });

    // Check if tenant allows registration
    const tenantInfo = await getTenantInfo(tenantSubdomain);
    if (!tenantInfo?.allow_registration) {
      return {
        message: "Registration not allowed",
        errors: {
          tenant: "Registration is not allowed for this organization"
        }
      };
    }

    // Register user with tenant context
    const response = await fetch(`${getApiBaseUrl()}/api/v1/tenant/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: validatedData.name,
        email: validatedData.email,
        password: validatedData.password,
        tenant_subdomain: tenantSubdomain
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        message: "Registration failed",
        errors: {
          general: errorData.error || "Registration failed"
        }
      };
    }

    // Auto-login after successful registration
    const loginResult = await signIn("credentials", {
      email: validatedData.email,
      password: validatedData.password,
      tenant_subdomain: tenantSubdomain,
      redirect: false,
    });

    if (loginResult?.error) {
      return {
        message: "Registration successful, but login failed",
        errors: {
          login: "Please try logging in manually"
        }
      };
    }

    return {
      message: "Registration successful",
    };
  } catch (error) {
    console.error("Tenant registration error:", error);
    
    if (error instanceof z.ZodError) {
      return {
        message: "Validation failed",
        errors: Object.fromEntries(
          error.errors.map((err) => [err.path[0], err.message])
        )
      };
    }
    
    return {
      message: "Registration failed",
      errors: {
        general: "An unexpected error occurred. Please try again."
      }
    };
  }
}

/**
 * Refresh access token with tenant validation
 */
export async function refreshTenantToken(refreshToken: string) {
  try {
    const tenantSubdomain = getCurrentTenantSubdomain();
    if (!tenantSubdomain) {
      throw new Error("No tenant context");
    }

    const response = await fetch(`${getApiBaseUrl()}/api/v1/tenant/refresh-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
        tenant_subdomain: tenantSubdomain
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
 * Validate user access to current tenant
 */
export async function validateTenantAccess(tenantSubdomain: string) {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/tenant/validate-access`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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
 * Get tenant information
 */
export async function getTenantInfo(tenantSubdomain?: string) {
  try {
    const subdomain = tenantSubdomain || getCurrentTenantSubdomain();
    if (!subdomain) {
      return null;
    }

    const response = await fetch(`${getApiBaseUrl()}/api/v1/tenant/public-info`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    console.log('🔍 [tenant-auth] API Response:', data);
    console.log('🔍 [tenant-auth] data.data:', data.data);
    console.log('🔍 [tenant-auth] data.data?.tenant:', data.data?.tenant);
    
    const result = data.data?.tenant || data.data;
    console.log('🔍 [tenant-auth] Final result:', result);
    
    // Handle API response structure: data.data.tenant
    return result;
  } catch (error) {
    console.error("Error fetching tenant info:", error);
    return null;
  }
}

/**
 * Get authenticated tenant information
 */
export async function getAuthenticatedTenantInfo(accessToken: string) {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/tenant/info`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error("Failed to fetch tenant info");
    }

    const data = await response.json();
    return {
      tenant: data.data?.attributes || data.data,
      membership: data.membership
    };
  } catch (error) {
    console.error("Error fetching authenticated tenant info:", error);
    throw error;
  }
}

/**
 * Logout from tenant
 */
export async function logoutFromTenant() {
  try {
    await signOut({ redirect: false });
    return { message: "Logged out successfully" };
  } catch (error) {
    console.error("Logout error:", error);
    return { message: "Logout failed" };
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
 * Check if current user belongs to current tenant
 */
export async function checkTenantMembership() {
  try {
    const tenantSubdomain = getCurrentTenantSubdomain();
    if (!tenantSubdomain) {
      return false;
    }

    return await validateTenantAccess(tenantSubdomain);
  } catch (error) {
    console.error("Error checking tenant membership:", error);
    return false;
  }
}

/**
 * Get tenant-specific API base URL
 */
export function getTenantApiBaseUrl(): string {
  const tenantSubdomain = getCurrentTenantSubdomain();
  if (!tenantSubdomain) {
    return getApiBaseUrl();
  }

  const baseUrl = getApiBaseUrl();
  // For tenant-specific API calls, we can add tenant context to headers
  // The actual API URL remains the same, but headers will contain tenant info
  return baseUrl;
}
