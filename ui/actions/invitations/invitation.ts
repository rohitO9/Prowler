"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  getApiBaseUrl,
  getAuthHeaders,
  getErrorMessage,
  parseStringify,
} from "@/lib";

export const getInvitations = async ({
  page = 1,
  query = "",
  sort = "",
  filters = {},
  pageSize = 10,
}) => {
  const headers = await getAuthHeaders({ contentType: false });

  if (isNaN(Number(page)) || page < 1) redirect("/invitations");

  const url = new URL(`${getApiBaseUrl()}/tenants/invitations`);

  if (page) url.searchParams.append("page[number]", page.toString());
  if (pageSize) url.searchParams.append("page[size]", pageSize.toString());
  if (query) url.searchParams.append("filter[search]", query);
  if (sort) url.searchParams.append("sort", sort);

  // Handle multiple filters
  Object.entries(filters).forEach(([key, value]) => {
    if (key !== "filter[search]") {
      url.searchParams.append(key, String(value));
    }
  });

  try {
    console.log('Fetching invitations from:', url.toString());
    
    const invitations = await fetch(url.toString(), {
      headers,
    });

    if (!invitations.ok) {
      console.error(`HTTP Error: ${invitations.status} ${invitations.statusText}`);
      const errorText = await invitations.text();
      console.error('Error response body:', errorText);
      
      // Return a consistent error structure instead of undefined
      return {
        data: [],
        meta: {
          total: 0,
          page: Number(page),
          pageSize: Number(pageSize)
        },
        error: {
          status: invitations.status,
          message: invitations.statusText,
          details: errorText
        }
      };
    }

    // Check if response is JSON
    const contentType = invitations.headers.get('content-type');
    if (!contentType?.includes('application/json')) {
      console.error('Invalid content type:', contentType);
      const text = await invitations.text();
      console.error('Non-JSON response:', text.substring(0, 500));
      
      return {
        data: [],
        meta: {
          total: 0,
          page: Number(page),
          pageSize: Number(pageSize)
        },
        error: {
          message: 'Invalid response format - expected JSON',
          details: `Content-Type: ${contentType}`
        }
      };
    }

    const data = await invitations.json();
    const parsedData = parseStringify(data);
    
    // Validate the response structure
    if (!parsedData || typeof parsedData !== 'object') {
      console.error('Invalid response data structure:', parsedData);
      return {
        data: [],
        meta: {
          total: 0,
          page: Number(page),
          pageSize: Number(pageSize)
        },
        error: {
          message: 'Invalid response data structure',
          details: 'Response is not a valid object'
        }
      };
    }

    // Ensure consistent data structure
    const normalizedData = {
      data: Array.isArray(parsedData.data) ? parsedData.data : 
            parsedData.data ? [parsedData.data] : [],
      meta: parsedData.meta || {
        total: 0,
        page: Number(page),
        pageSize: Number(pageSize)
      },
      ...parsedData
    };

    console.log('Successfully fetched invitations:', normalizedData.data.length, 'items');
    revalidatePath("/invitations");
    return normalizedData;

  } catch (error) {
    console.error("Error fetching invitations:", error);
    
    // Return a consistent error structure instead of undefined
    return {
      data: [],
      meta: {
        total: 0,
        page: Number(page),
        pageSize: Number(pageSize)
      },
      error: {
        message: getErrorMessage(error),
        details: error instanceof Error ? error.stack : String(error)
      }
    };
  }
};

export const sendInvite = async (formData: FormData) => {
  const headers = await getAuthHeaders({ contentType: true });

  const email = formData.get("email");
  const role = formData.get("role");
  const url = new URL(`${getApiBaseUrl()}/tenants/invitations`);

  const body = JSON.stringify({
    data: {
      type: "invitations",
      attributes: {
        email,
      },
      relationships: {
        roles: {
          data: role
            ? [
                {
                  id: role,
                  type: "roles",
                },
              ]
            : [],
        },
      },
    },
  });

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
      body,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
      return {
        error: {
          status: response.status,
          message: errorData.message || response.statusText,
          details: errorData
        }
      };
    }

    const data = await response.json();
    return parseStringify(data);
    
  } catch (error) {
    return {
      error: {
        message: getErrorMessage(error),
        details: error instanceof Error ? error.stack : String(error)
      }
    };
  }
};

export const updateInvite = async (formData: FormData) => {
  const headers = await getAuthHeaders({ contentType: true });

  const invitationId = formData.get("invitationId");
  const invitationEmail = formData.get("invitationEmail");
  const roleId = formData.get("role");
  const expiresAt =
    formData.get("expires_at") ||
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();

  const url = new URL(`${getApiBaseUrl()}/tenants/invitations/${invitationId}`);

  const body: any = {
    data: {
      type: "invitations",
      id: invitationId,
      attributes: {},
      relationships: {},
    },
  };

  // Only add attributes that exist in the formData
  if (invitationEmail) {
    body.data.attributes.email = invitationEmail;
  }
  if (expiresAt) {
    body.data.attributes.expires_at = expiresAt;
  }
  if (roleId) {
    body.data.relationships.roles = {
      data: [
        {
          id: roleId,
          type: "roles",
        },
      ],
    };
  }

  try {
    const response = await fetch(url.toString(), {
      method: "PATCH",
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Unknown error' }));
      return { 
        error: {
          status: response.status,
          message: error.message || response.statusText,
          details: error
        }
      };
    }

    const data = await response.json();
    revalidatePath("/invitations");
    return parseStringify(data);
    
  } catch (error) {
    return {
      error: {
        message: getErrorMessage(error),
        details: error instanceof Error ? error.stack : String(error)
      }
    };
  }
};

export const getInvitationInfoById = async (invitationId: string) => {
  const headers = await getAuthHeaders({ contentType: false });
  const url = new URL(`${getApiBaseUrl()}/tenants/invitations/${invitationId}`);

  try {
    const response = await fetch(url.toString(), {
      method: "GET",
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
      return {
        error: {
          status: response.status,
          message: errorData.message || response.statusText,
          details: errorData
        }
      };
    }

    const data = await response.json();
    return parseStringify(data);
    
  } catch (error) {
    return {
      error: {
        message: getErrorMessage(error),
        details: error instanceof Error ? error.stack : String(error)
      }
    };
  }
};

export const revokeInvite = async (formData: FormData) => {
  const headers = await getAuthHeaders({ contentType: false });
  const invitationId = formData.get("invitationId");

  if (!invitationId) {
    return { 
      error: {
        message: "Invitation ID is required",
        details: "No invitation ID provided in form data"
      }
    };
  }

  const url = new URL(`${getApiBaseUrl()}/tenants/invitations/${invitationId}`);

  try {
    const response = await fetch(url.toString(), {
      method: "DELETE",
      headers,
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        throw new Error(
          errorData?.message || "Failed to revoke the invitation",
        );
      } catch {
        throw new Error("Failed to revoke the invitation");
      }
    }

    let data = null;
    if (response.status !== 204) {
      data = await response.json();
    }

    revalidatePath("/invitations");
    return data || { success: true };
    
  } catch (error) {
    console.error("Error revoking invitation:", error);
    return { 
      error: {
        message: getErrorMessage(error),
        details: error instanceof Error ? error.stack : String(error)
      }
    };
  }
};