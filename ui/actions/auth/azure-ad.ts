"use server";

import { signIn } from "@/auth.config";
import { getApiBaseUrl } from "@/lib/helper";

export interface AzureADConfig {
  client_id: string;
  tenant_id: string;
  redirect_uri: string;
  authority: string;
  scopes: string[];
}

export interface AzureADTokenResponse {
  access: string;
  refresh: string;
  user: {
    id: string;
    email: string;
    name: string;
    company?: string;
    dateJoined?: string;
  };
  tenant_id?: string;
  tenant_name?: string;
}

/**
 * Get Azure AD configuration from the backend (tenant-specific from DB)
 * Extracts tenant from current window location subdomain
 */
export const getAzureADConfig = async (): Promise<AzureADConfig | null> => {
  try {
    // Extract tenant subdomain from current window location
    let tenantSubdomain: string | null = null;
    if (typeof window !== "undefined") {
      const hostname = window.location.hostname;
      // Extract subdomain: company1.localhost -> company1
      if (hostname.includes('.')) {
        const parts = hostname.split('.');
        const firstPart = parts[0];
        // Skip localhost, IP addresses, www, api, admin
        if (firstPart && 
            firstPart !== 'localhost' && 
            firstPart !== 'www' && 
            firstPart !== '127' && 
            firstPart !== 'api' &&
            firstPart !== 'admin' &&
            !firstPart.match(/^\d+$/)) {
          tenantSubdomain = firstPart;
          
        }
      }
    }
    
    // Build API URL with tenant context
    let apiUrl = `${getApiBaseUrl()}/tokens/azure/config`;
    if (tenantSubdomain) {
      // Pass tenant subdomain as query parameter or header
      apiUrl += `?tenant_subdomain=${tenantSubdomain}`;
    }
    
    // Use the tenant-specific endpoint that gets config from database
    const response = await fetch(apiUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/vnd.api+json",
        Accept: "application/vnd.api+json",
        // Also pass subdomain as header for backend extraction
        ...(tenantSubdomain && { "X-Tenant-Subdomain": tenantSubdomain }),
      },
      cache: "no-store", // Always fetch fresh config
    });

    if (!response.ok) {
      // 404 means Azure AD not configured for this tenant - this is OK
      if (response.status === 404) {
        console.log("Azure AD not configured for this tenant");
        return null;
      }
      console.error("Failed to get Azure AD config:", response.status);
      return null;
    }

    const responseData = await response.json();
    
    // Extract the data from JSON API format
    const config = responseData.data || responseData;
    
    // Map backend response to expected format
    if (config) {
      return {
        client_id: config.client_id,
        tenant_id: config.azure_tenant_id || config.tenant_id,
        redirect_uri: config.redirect_uri,
        authority: config.authority || `https://login.microsoftonline.com/${config.azure_tenant_id || config.tenant_id}`,
        scopes: config.scopes || ["openid", "profile", "email", "User.Read"],
      };
    }
    
    return null;
  } catch (error) {
    console.error("Error getting Azure AD config:", error);
    return null;
  }
};

/**
 * Exchange authorization code for tokens
 */
export const exchangeAzureADCode = async (code: string, tenantName?: string): Promise<AzureADTokenResponse | null> => {
  try {
    const response = await fetch(`${getApiBaseUrl()}/tokens/azure`, {
      method: "POST",
      headers: {
        "Content-Type": "application/vnd.api+json",
        Accept: "application/vnd.api+json",
      },
      body: JSON.stringify({ code, tenant_name: tenantName }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Azure AD token exchange failed:", errorData);
      return null;
    }

    const responseData = await response.json();
    const tokenData = responseData.data || responseData;
    return tokenData;
  } catch (error) {
    console.error("Error exchanging Azure AD code:", error);
    return null;
  }
};

/**
 * Test Azure AD authentication without creating a user
 */
export const testAzureADAuth = async (code: string): Promise<any> => {
  try {
    const response = await fetch(`${getApiBaseUrl()}/tokens/azure/test`, {
      method: "POST",
      headers: {
        "Content-Type": "application/vnd.api+json",
        Accept: "application/vnd.api+json",
      },
      body: JSON.stringify({ code }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Azure AD test failed:", errorData);
      return null;
    }

    const responseData = await response.json();
    const testData = responseData.data || responseData;
    return testData;
  } catch (error) {
    console.error("Error testing Azure AD auth:", error);
    return null;
  }
};

/**
 * Check trial status for a user
 */
export const checkTrialStatus = async (email: string): Promise<any> => {
  try {
    const response = await fetch(`${getApiBaseUrl()}/tokens/azure/trial-status?email=${encodeURIComponent(email)}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/vnd.api+json",
        Accept: "application/vnd.api+json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Trial status check failed:", errorData);
      return null;
    }

    const responseData = await response.json();
    const trialData = responseData.data || responseData;
    return trialData;
  } catch (error) {
    console.error("Error checking trial status:", error);
    return null;
  }
};

/**
 * Authenticate with Azure AD using the authorization code
 */
export const authenticateWithAzureAD = async (code: string) => {
  try {
    const company = typeof window !== "undefined" ? localStorage.getItem("company") || undefined : undefined;
    // Exchange the authorization code for tokens
    const tokenResponse = await exchangeAzureADCode(code, company);
    
    if (!tokenResponse) {
      return {
        success: false,
        error: "Failed to exchange authorization code for tokens",
      };
    }

    // Sign in using the social OAuth provider with the tokens
    const result = await signIn("social-oauth", {
      accessToken: tokenResponse.access,
      refreshToken: tokenResponse.refresh,
      redirect: false,
    });

    if (result?.error) {
      return {
        success: false,
        error: result.error,
      };
    }

    return {
      success: true,
      user: tokenResponse.user,
      tokens: {
        access: tokenResponse.access,
        refresh: tokenResponse.refresh,
      },
    };
  } catch (error) {
    console.error("Azure AD authentication error:", error);
    return {
      success: false,
      error: "Authentication failed",
    };
  }
};

/**
 * Get Azure AD login URL
 */
export const getAzureADLoginUrl = async (): Promise<string | null> => {
  try {
    const config = await getAzureADConfig();
    
    if (!config) {
      return null;
    }

    const params = new URLSearchParams({
      client_id: config.client_id,
      response_type: "code",
      redirect_uri: config.redirect_uri,
      response_mode: "query",
      scope: config.scopes.join(" "),
      state: "optional-csrf",
      prompt: "select_account",
    });

    return `${config.authority}/oauth2/v2.0/authorize?${params.toString()}`;
  } catch (error) {
    console.error("Error generating Azure AD login URL:", error);
    return null;
  }
};
