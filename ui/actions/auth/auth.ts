"use server";

import { AuthError } from "next-auth";
import { z } from "zod";

import { signIn, signOut } from "@/auth.config";
import { getApiBaseUrl, getServerApiBaseUrl } from "@/lib/helper";
import { authFormSchema } from "@/types";

const formSchemaSignIn = authFormSchema("sign-in");
const formSchemaSignUp = authFormSchema("sign-up");

const defaultValues: z.infer<typeof formSchemaSignIn> = {
  email: "",
  password: "",
};

// Enhanced helper to check JSON content type with better error handling
async function safeJsonParse(response: Response) {
  const contentType = response.headers.get("content-type") || "";
  
  if (
    !contentType.includes("application/json") &&
    !contentType.includes("application/vnd.api+json")
  ) {
    const text = await response.text();
    throw new Error(
      `Non-JSON response from backend (${response.status}):\n${text.substring(0, 200)}`
    );
  }
  
  try {
    return await response.json();
  } catch (parseError) {
    throw new Error("Invalid JSON response from backend");
  }
}

export async function authenticate(
  prevState: unknown,
  formData: z.infer<typeof formSchemaSignIn>
) {
  try {
    const result = await signIn("credentials", {
      ...formData,
      // Support enterprise: allow passing organization/tenant name from UI as "company"
      // NextAuth authorize will forward these to the backend token endpoint
      tenant_name: (formData as any).company,
      redirect: false,
    });
    
    if (result?.error) {
      throw new Error(result.error);
    }
    
    return {
      message: "Success",
    };
  } catch (error) {
    
    if (error instanceof AuthError) {
      switch (error.type) {
        case "CredentialsSignin":
          return {
            message: "User not found",
            errors: {
              ...defaultValues,
              credentials: "User not found or invalid credentials",
            },
          };
        case "CallbackRouteError":
          return {
            message: error.cause?.err?.message || "Callback route error",
          };
        default:
          return {
            message: "Unknown auth error",
            errors: {
              ...defaultValues,
              unknown: error.message || "Unknown authentication error",
            },
          };
      }
    }
    
    // Handle specific error messages from backend
    const errorMessage = (error as Error).message || "";
    if (errorMessage.includes("Invalid credentials") || errorMessage.includes("User not found")) {
      return {
        message: "User not found",
        errors: {
          ...defaultValues,
          credentials: "User not found or invalid credentials",
        },
      };
    }
    
    if (errorMessage.includes("Access denied") || errorMessage.includes("tenant")) {
      return {
        message: "Access denied",
        errors: {
          ...defaultValues,
          credentials: "Access denied to this tenant",
        },
      };
    }
    
    // Handle SSO-only user error
    if (errorMessage.includes("SSO_ONLY_USER") || errorMessage.includes("SSO") || errorMessage.includes("Azure AD")) {
      return {
        message: "SSO Login Required",
        errors: {
          ...defaultValues,
          credentials: errorMessage.replace("SSO_ONLY_USER: ", "") || "This account can only be accessed via Azure AD SSO. Please use the Azure AD login button.",
        },
      };
    }
    
    return {
      message: "Unexpected error",
      errors: {
        ...defaultValues,
        unknown: (error as Error).message || "Unexpected error occurred",
      },
    };
  }
}

export const createNewUser = async (
  formData: z.infer<typeof formSchemaSignUp>,
  host?: string
) => {
  // Ensure we're using the subdomain for API calls
  let apiBaseUrl = getApiBaseUrl();
  
  // Get subdomain from form data (passed from client-side)
  let subdomain = (formData as any).subdomain || '';
  
  // Fallback: Try client-side detection if not provided
  if (!subdomain && typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname.includes('localhost') && hostname !== 'localhost') {
      subdomain = hostname.split('.')[0];
      apiBaseUrl = `http://${hostname}:8080/api/v1`;
    }
  }
  
  // Fallback: Try server-side detection from host header
  if (!subdomain && host) {
    if (host.includes('localhost') && host !== 'localhost') {
      subdomain = host.split('.')[0];
      apiBaseUrl = `http://${host}:8080/api/v1`;
    }
  }
  
  const url = new URL(`${apiBaseUrl}/tenant/register`);

  if (formData.invitationToken) {
    url.searchParams.append("invitation_token", formData.invitationToken);
  }

  // Extract first and last name from full name
  // Name is required for sign-up, but TypeScript needs explicit check
  if (!formData.name) {
    return {
      errors: [
        {
          source: { pointer: "/data/attributes/name" },
          detail: "Name is required",
        },
      ],
    };
  }

  const nameParts = formData.name.split(' ');
  const first_name = nameParts[0] || '';
  const last_name = nameParts.slice(1).join(' ') || '';
  
  const bodyData = {
    data: {
      type: "tenant_register",
      attributes: {
        // Send subdomain explicitly from frontend
        subdomain: subdomain,
        email: formData.email,
        password: formData.password,
        first_name: first_name,
        last_name: last_name,
      },
    },
  };
  
  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/vnd.api+json",
        Accept: "application/vnd.api+json",
      },
      body: JSON.stringify(bodyData),
    });

    const parsedResponse = await safeJsonParse(response);
    if (!response.ok) {
      // Handle specific error scenarios
      if (response.status === 400) {
        const errorDetail = parsedResponse?.errors?.[0]?.detail || "";
        if (errorDetail.includes("already exists") || errorDetail.includes("duplicate")) {
          return {
            errors: [
              {
                source: { pointer: "/data/attributes/email" },
                detail: "User with this email already exists",
              },
            ],
          };
        }
      }
      
      if (response.status === 409) {
        return {
          errors: [
            {
              source: { pointer: "/data/attributes/email" },
              detail: "User with this email already exists",
            },
          ],
        };
      }
      
      return parsedResponse;
    }

    return parsedResponse;
  } catch (error) {
    return {
      errors: [
        {
          source: { pointer: "" },
          detail: error instanceof Error ? error.message : "Network error or server is unreachable",
        },
      ],
    };
  }
};

// Replace the getToken function in your actions/auth/auth.ts file with this:

export const getToken = async (formData: z.infer<typeof formSchemaSignIn>, host?: string) => {
  // Use server-side API URL if host is provided, otherwise use client-side
  let apiUrl = host ? getServerApiBaseUrl(host) : getApiBaseUrl();
  
  // If we're on client-side and have a subdomain, use it
  if (typeof window !== 'undefined' && !host) {
    const hostname = window.location.hostname;
    if (hostname.includes('localhost') && hostname !== 'localhost') {
      // We're on a subdomain like company1.localhost
      apiUrl = `http://${hostname}:8080/api/v1`;
    }
  }
  
  const url = new URL(`${apiUrl}/tokens`);
  
  // Auto-detect tenant from current subdomain and send it explicitly
  let subdomain = '';
  
  // Check if we have host parameter (server-side)
  if (host) {
    if (host.includes('localhost') && host !== 'localhost') {
      // Extract subdomain from company1.localhost:3000
      subdomain = host.split('.')[0];
    }
  } else if (typeof window !== 'undefined') {
    // Client-side detection
    const hostname = window.location.hostname;
    if (hostname.includes('localhost') && hostname !== 'localhost') {
      // Extract subdomain from company1.localhost
      subdomain = hostname.split('.')[0];
    }
  }
  
  // Getting token from backend
  const bodyData = {
    data: {
      type: "tokens",
      attributes: {
        email: formData.email,
        password: formData.password,
        // Send subdomain explicitly for tenant context
        ...(subdomain ? { tenant_name: subdomain } : {}),
      },
    },
  };

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/vnd.api+json",
        Accept: "application/vnd.api+json",
      },
      body: JSON.stringify(bodyData),
    });

    if (!response.ok) {
      let errorMsg = `Token request failed (${response.status} ${response.statusText})`;
      let errorCode = '';
      try {
        const parsed = await safeJsonParse(response);
        errorMsg = parsed?.error || parsed?.errors?.[0]?.detail || errorMsg;
        errorCode = parsed?.code || '';
        
        // Check for SSO-only user error
        if (response.status === 403 && (errorCode === 'SSO_ONLY_USER' || errorMsg.includes('SSO') || errorMsg.includes('Azure AD'))) {
          throw new Error(`SSO_ONLY_USER: ${errorMsg}`);
        }
      } catch (parseErr: unknown) {
        if (parseErr instanceof Error) {
          // If it's already our SSO-only error, rethrow it
          if (parseErr.message.includes('SSO_ONLY_USER')) {
            throw parseErr;
          }
          errorMsg = `${errorMsg} - Parse error: ${parseErr.message}`;
        } else {
          errorMsg = `${errorMsg} - Parse error: ${String(parseErr)}`;
        }
      }
      throw new Error(errorMsg);
    }

    const parsedResponse = await safeJsonParse(response);
    
    // FIX: Access tokens directly from data object, not data.attributes
    const accessToken = parsedResponse?.data?.access;
    const refreshToken = parsedResponse?.data?.refresh;

    if (!accessToken || !refreshToken) {
      throw new Error("Tokens missing in backend response.");
    }

    return {
      accessToken,
      refreshToken,
    };
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : "Error in trying to get token");
  }
};

export const getUserByMe = async (accessToken: string, host?: string) => {
  // Use server-side API URL if host is provided, otherwise use client-side
  const apiUrl = host ? getServerApiBaseUrl(host) : getApiBaseUrl();
  const url = new URL(`${apiUrl}/users/me`);

  try {
    const response = await fetch(url.toString(), {
      method: "GET",
      headers: {
        Accept: "application/vnd.api+json",
        Authorization: `Bearer ${accessToken}`,
      },
    });

    const parsedResponse = await safeJsonParse(response);

    if (!response.ok) {
      let errorMsg = `Get user failed (${response.status} ${response.statusText})`;

      switch (response.status) {
        case 401:
          errorMsg = "Invalid or expired token";
          break;
        case 403:
          errorMsg = parsedResponse.errors?.[0]?.detail || "Forbidden";
          break;
        case 404:
          errorMsg = "User not found";
          break;
        default:
          errorMsg = parsedResponse.errors?.[0]?.detail || errorMsg;
      }
      throw new Error(errorMsg);
    }

    // Safety check for response structure (handle double-nested data)
    const attributes = parsedResponse?.data?.data?.attributes || parsedResponse?.data?.attributes;
    if (!attributes) {
      throw new Error("Invalid response structure from server");
    }
    
    return {
      name: attributes.name,
      email: attributes.email,
      company: attributes.company_name,
      dateJoined: attributes.date_joined,
    };
    
  } catch (error: any) {
    throw new Error(error.message || "Network error or server unreachable");
  }
};

export async function logOut() {
  try {
    // Clear NextAuth session
    await signOut({ 
      redirect: false // We'll handle redirect manually
    });
    
    // Clear any cached data
    if (typeof window !== 'undefined') {
      // Clear localStorage
      localStorage.removeItem('company');
      localStorage.removeItem('tenant');
      localStorage.removeItem('user');
      
      // Clear sessionStorage
      sessionStorage.clear();
      
      // Clear any other cached data
      localStorage.removeItem('auth-token');
      localStorage.removeItem('refresh-token');
    }
    
    return {
      success: true,
      message: "Logged out successfully"
    };
    
  } catch (error) {
    return {
      success: false,
      message: "Logout failed"
    };
  }
}