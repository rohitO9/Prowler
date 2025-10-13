"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  apiBaseUrl,
  getApiBaseUrl,
  getAuthHeaders,
  getErrorMessage,
  parseStringify,
} from "@/lib";

// Admin User Management Actions

export const getAdminUsers = async ({
  page = 1,
  query = "",
  sort = "",
  filters = {},
  pageSize = 10,
}) => {
  const headers = await getAuthHeaders({ contentType: false });

  if (isNaN(Number(page)) || page < 1) redirect("/users");

  const url = new URL(`${getApiBaseUrl()}/admin/users/`);

  if (page) url.searchParams.append("page", page.toString());
  if (pageSize) url.searchParams.append("page_size", pageSize.toString());
  if (query) url.searchParams.append("search", query);
  if (sort) url.searchParams.append("sort", sort);

  // Handle multiple filters
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      url.searchParams.append(key, String(value));
    }
  });

  try {
    const response = await fetch(url.toString(), {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    revalidatePath("/users");
    return data;
  } catch (error) {
    console.error("Error fetching admin users:", error);
    return { users: [], total_count: 0 };
  }
};

export const getUserPermissions = async (userId: string) => {
  const headers = await getAuthHeaders({ contentType: false });
  const url = new URL(`${getApiBaseUrl()}/admin/users/${userId}/permissions/`);

  try {
    const response = await fetch(url.toString(), {
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching user permissions:", error);
    return { permissions_by_category: {}, user: null };
  }
};

export const assignRoleToUser = async (formData: FormData) => {
  const headers = await getAuthHeaders({ contentType: true });

  const userId = formData.get("userId") as string;
  const roleId = formData.get("roleId") as string;
  const assignmentSource = formData.get("assignmentSource") as string || "direct";

  if (!userId || !roleId) {
    return { error: "userId and roleId are required" };
  }

  const url = new URL(`${getApiBaseUrl()}/admin/users/${userId}/assign_role/`);

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
      body: JSON.stringify({
        role_id: roleId,
        assignment_source: assignmentSource,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return { error: data.error || "Failed to assign role" };
    }

    revalidatePath("/users");
    return data;
  } catch (error) {
    console.error("Error assigning role:", error);
    return { error: getErrorMessage(error) };
  }
};

export const removeRoleFromUser = async (formData: FormData) => {
  const headers = await getAuthHeaders({ contentType: true });

  const userId = formData.get("userId") as string;
  const roleId = formData.get("roleId") as string;

  if (!userId || !roleId) {
    return { error: "userId and roleId are required" };
  }

  const url = new URL(`${getApiBaseUrl()}/admin/users/${userId}/remove_role/`);

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
      body: JSON.stringify({
        role_id: roleId,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return { error: data.error || "Failed to remove role" };
    }

    revalidatePath("/users");
    return data;
  } catch (error) {
    console.error("Error removing role:", error);
    return { error: getErrorMessage(error) };
  }
};

export const toggleUserActive = async (formData: FormData) => {
  const headers = await getAuthHeaders({ contentType: true });

  const userId = formData.get("userId") as string;

  if (!userId) {
    return { error: "userId is required" };
  }

  const url = new URL(`${getApiBaseUrl()}/admin/users/${userId}/toggle_active/`);

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
    });

    const data = await response.json();

    if (!response.ok) {
      return { error: data.error || "Failed to toggle user status" };
    }

    revalidatePath("/users");
    return data;
  } catch (error) {
    console.error("Error toggling user status:", error);
    return { error: getErrorMessage(error) };
  }
};

export const updateUserPermissions = async (formData: FormData) => {
  const headers = await getAuthHeaders({ contentType: true });

  const userId = formData.get("userId") as string;
  const permissions = JSON.parse(formData.get("permissions") as string || "[]");

  if (!userId) {
    return { error: "userId is required" };
  }

  const url = new URL(`${getApiBaseUrl()}/admin/users/${userId}/update_permissions/`);

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
      body: JSON.stringify({
        permissions: permissions,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return { error: data.error || "Failed to update permissions" };
    }

    revalidatePath("/users");
    return data;
  } catch (error) {
    console.error("Error updating user permissions:", error);
    return { error: getErrorMessage(error) };
  }
};

// Admin Role Management Actions

export const getAdminRoles = async () => {
  const headers = await getAuthHeaders({ contentType: false });
  const url = new URL(`${getApiBaseUrl()}/admin/roles/`);

  try {
    const response = await fetch(url.toString(), {
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching admin roles:", error);
    return { roles: [], total_count: 0 };
  }
};

export const createRole = async (formData: FormData) => {
  const headers = await getAuthHeaders({ contentType: true });

  const name = formData.get("name") as string;
  const displayName = formData.get("display_name") as string;
  const description = formData.get("description") as string;
  const roleType = formData.get("role_type") as string || "custom";
  const priority = parseInt(formData.get("priority") as string || "50");
  const permissions = JSON.parse(formData.get("permissions") as string || "[]");

  if (!name || !displayName) {
    return { error: "name and display_name are required" };
  }

  const url = new URL(`${getApiBaseUrl()}/admin/roles/`);

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
      body: JSON.stringify({
        name,
        display_name: displayName,
        description,
        role_type: roleType,
        priority,
        permissions,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return { error: data.error || "Failed to create role" };
    }

    revalidatePath("/roles");
    return data;
  } catch (error) {
    console.error("Error creating role:", error);
    return { error: getErrorMessage(error) };
  }
};

export const addPermissionToRole = async (formData: FormData) => {
  const headers = await getAuthHeaders({ contentType: true });

  const roleId = formData.get("roleId") as string;
  const permissionName = formData.get("permissionName") as string;

  if (!roleId || !permissionName) {
    return { error: "roleId and permissionName are required" };
  }

  const url = new URL(`${getApiBaseUrl()}/admin/roles/${roleId}/add_permission/`);

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
      body: JSON.stringify({
        permission_name: permissionName,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return { error: data.error || "Failed to add permission" };
    }

    revalidatePath("/roles");
    return data;
  } catch (error) {
    console.error("Error adding permission to role:", error);
    return { error: getErrorMessage(error) };
  }
};

export const removePermissionFromRole = async (formData: FormData) => {
  const headers = await getAuthHeaders({ contentType: true });

  const roleId = formData.get("roleId") as string;
  const permissionName = formData.get("permissionName") as string;

  if (!roleId || !permissionName) {
    return { error: "roleId and permissionName are required" };
  }

  const url = new URL(`${getApiBaseUrl()}/admin/roles/${roleId}/remove_permission/`);

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
      body: JSON.stringify({
        permission_name: permissionName,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return { error: data.error || "Failed to remove permission" };
    }

    revalidatePath("/roles");
    return data;
  } catch (error) {
    console.error("Error removing permission from role:", error);
    return { error: getErrorMessage(error) };
  }
};
