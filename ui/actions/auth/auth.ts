"use server";

import { AuthError } from "next-auth";
import { z } from "zod";

import { signIn, signOut } from "@/auth.config";
import { apiBaseUrl } from "@/lib";
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
  
  // Log response details for debugging
  console.log(`Response status: ${response.status} ${response.statusText}`);
  console.log(`Content-Type: ${contentType}`);
  console.log(`Response URL: ${response.url}`);
  
  if (
    !contentType.includes("application/json") &&
    !contentType.includes("application/vnd.api+json")
  ) {
    const text = await response.text();
    console.error("Non-JSON response received:", text.substring(0, 500));
    throw new Error(
      `Non-JSON response from backend (${response.status}):\n${text.substring(0, 200)}`
    );
  }
  
  
  try {
    const json = await response.json();
    console.log("Parsed JSON response:", JSON.stringify(json, null, 2));
    return json;
  } catch (parseError) {
    console.error("Failed to parse JSON:", parseError);
    throw new Error("Invalid JSON response from backend");
  }
}

export async function authenticate(
  prevState: unknown,
  formData: z.infer<typeof formSchemaSignIn>
) {
  try {
    console.log("Attempting authentication for:", formData.email);
    await signIn("credentials", {
      ...formData,
      // Support enterprise: allow passing organization/tenant name from UI as "company"
      // NextAuth authorize will forward these to the backend token endpoint
      tenant_name: (formData as any).company,
      redirect: false,
    });
    return {
      message: "Success",
    };
  } catch (error) {
    console.error("Authentication error:", error);
    
    if (error instanceof AuthError) {
      switch (error.type) {
        case "CredentialsSignin":
          return {
            message: "Credentials error",
            errors: {
              ...defaultValues,
              credentials: "Incorrect email or password",
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
  formData: z.infer<typeof formSchemaSignUp>
) => {
  const url = new URL(`${apiBaseUrl}/users`);

  if (formData.invitationToken) {
    url.searchParams.append("invitation_token", formData.invitationToken);
  }

  const bodyData = {
    data: {
      type: "users",
      attributes: {
        name: formData.name,
        email: formData.email,
        password: formData.password,
        ...(formData.company && { company_name: formData.company }),
      },
    },
  };
  
  console.log("Creating new user with payload:", bodyData);
  console.log("API URL:", url.toString());

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
      return parsedResponse;
    }

    return parsedResponse;
  } catch (error) {
    console.error("Create user error:", error);
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

export const getToken = async (formData: z.infer<typeof formSchemaSignIn>) => {
  const url = new URL(`${apiBaseUrl}/tokens`);
  
  console.log("Getting token from:", url.toString());
  console.log("API Base URL:", apiBaseUrl);

  const bodyData = {
    data: {
      type: "tokens",
      attributes: {
        email: formData.email,
        password: formData.password,
        // enterprise: optionally send tenant_name to select organization context
        ...(formData as any)?.company ? { tenant_name: (formData as any).company } : {},
      },
    },
  };

  try {
    console.log("Token request payload:", bodyData);
    
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
      try {
        const parsed = await safeJsonParse(response);
        errorMsg = parsed?.errors?.[0]?.detail || errorMsg;
      } catch (parseErr: unknown) {
        console.error("Failed to parse error response:", parseErr);
        if (parseErr instanceof Error) {
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
      console.error("Missing tokens in response:", parsedResponse);
      throw new Error("Tokens missing in backend response.");
    }

    console.log("Successfully received tokens:", {
      accessTokenLength: accessToken.length,
      refreshTokenLength: refreshToken.length,
    });

    return {
      accessToken,
      refreshToken,
    };
  } catch (error) {
    console.error("getToken error:", error);
    throw new Error(error instanceof Error ? error.message : "Error in trying to get token");
  }
};

export const getUserByMe = async (accessToken: string) => {
  const url = new URL(`${apiBaseUrl}/users/me`);
  
  console.log("Getting user info from:", url.toString());
  console.log("Using access token length:", accessToken.length);

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

    const userData = {
      name: parsedResponse.data.attributes.name,
      email: parsedResponse.data.attributes.email,
      company: parsedResponse.data.attributes.company_name,
      dateJoined: parsedResponse.data.attributes.date_joined,
    };
    
    console.log("Successfully retrieved user data:", userData);
    return userData;
    
  } catch (error: any) {
    console.error("getUserByMe error:", error);
    throw new Error(error.message || "Network error or server unreachable");
  }
};

export async function logOut() {
  console.log("Logging out user");
  await signOut();
}