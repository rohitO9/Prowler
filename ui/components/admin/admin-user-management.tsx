"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog/dialog";
import { Select } from "@/components/ui/select/Select";
import { Label } from "@/components/ui/label/Label";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog/AlertDialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip/tooltip";
import {
  User,
  Settings,
  Plus,
  Key,
  Shield,
  Users,
  Crown,
  Eye,
  Edit,
  Trash2,
  Power,
  PowerOff,
  CheckCircle,
  XCircle,
} from "lucide-react";
// Using console.log instead of toast for now
const toast = {
  success: (message: string) => console.log("Success:", message),
  error: (message: string) => console.error("Error:", message)
};

interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  date_joined: string;
  roles: Role[];
  permissions: string[];
  azure_profile?: {
    job_title: string;
    department: string;
    office_location: string;
    last_synced_at: string;
    sync_status: string;
  };
  trial_info: {
    trial_start: string | null;
    trial_end: string | null;
    is_trial_active: boolean;
  };
}

interface Role {
  id: string;
  name: string;
  display_name: string;
  role_type: string;
  assignment_source: string;
  assigned_at: string;
  expires_at: string | null;
  is_expired: boolean;
}

interface Permission {
  name: string;
  display_name: string;
  category: string;
  action: string;
  has_permission: boolean;
}

interface AdminUserManagementProps {
  users: User[];
  roles: any[];
  onRefresh: () => void;
}

export function AdminUserManagement({ users, roles, onRefresh }: AdminUserManagementProps) {
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [userPermissions, setUserPermissions] = useState<Record<string, Permission[]>>({});
  const [isPermissionModalOpen, setIsPermissionModalOpen] = useState(false);
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);
  const [isCreateRoleModalOpen, setIsCreateRoleModalOpen] = useState(false);
  const [selectedRoleId, setSelectedRoleId] = useState<string>("");

  const handleAssignRole = async (userId: string, roleId: string) => {
    try {
      const formData = new FormData();
      formData.append("userId", userId);
      formData.append("roleId", roleId);
      formData.append("assignmentSource", "direct");

      const response = await fetch("/api/admin/assign-role", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (result.error) {
        toast.error(result.error);
      } else {
        toast.success("Role assigned successfully");
        onRefresh();
      }
    } catch (error) {
      toast.error("Failed to assign role");
    }
  };

  const handleRemoveRole = async (userId: string, roleId: string) => {
    try {
      const formData = new FormData();
      formData.append("userId", userId);
      formData.append("roleId", roleId);

      const response = await fetch("/api/admin/remove-role", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (result.error) {
        toast.error(result.error);
      } else {
        toast.success("Role removed successfully");
        onRefresh();
      }
    } catch (error) {
      toast.error("Failed to remove role");
    }
  };

  const handleToggleUserActive = async (userId: string) => {
    try {
      const formData = new FormData();
      formData.append("userId", userId);

      const response = await fetch("/api/admin/toggle-user-active", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (result.error) {
        toast.error(result.error);
      } else {
        toast.success(result.message);
        onRefresh();
      }
    } catch (error) {
      toast.error("Failed to update user status");
    }
  };

  const handleViewPermissions = async (user: User) => {
    setSelectedUser(user);
    setIsPermissionModalOpen(true);

    try {
      const response = await fetch(`/api/admin/user-permissions/${user.id}`);
      const data = await response.json();
      setUserPermissions(data.permissions_by_category || {});
    } catch (error) {
      toast.error("Failed to fetch user permissions");
    }
  };

  const getRoleIcon = (roleType: string) => {
    switch (roleType) {
      case "system":
        return <Crown className="h-4 w-4" />;
      case "azure_sync":
        return <Shield className="h-4 w-4" />;
      default:
        return <User className="h-4 w-4" />;
    }
  };

  const getRoleColor = (roleType: string) => {
    switch (roleType) {
      case "system":
        return "bg-red-100 text-red-800 border-red-200";
      case "azure_sync":
        return "bg-blue-100 text-blue-800 border-blue-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Users className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">User Management</h2>
            <p className="text-gray-600">Manage users, roles, and permissions</p>
          </div>
        </div>
        <div className="flex space-x-2">
          <Button
            onClick={() => setIsCreateRoleModalOpen(true)}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Role
          </Button>
          <Button onClick={onRefresh} variant="outline">
            Refresh
          </Button>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Users ({users.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b">
                <th className="text-left p-2">User</th>
                <th className="text-left p-2">Status</th>
                <th className="text-left p-2">Roles</th>
                <th className="text-left p-2">Azure Profile</th>
                <th className="text-left p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b hover:bg-gray-50">
                  <td className="p-2">
                    <div>
                      <div className="font-semibold">{user.name}</div>
                      <div className="text-sm text-gray-600">{user.email}</div>
                    </div>
                  </td>
                  <td className="p-2">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        user.is_active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"
                      }`}>
                        {user.is_active ? "Active" : "Inactive"}
                      </span>
                      {user.trial_info.is_trial_active && (
                        <span className="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800 border">
                          Trial
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-2">
                    <div className="flex flex-wrap gap-1">
                      {user.roles.map((role) => (
                        <span
                          key={role.id}
                          className={`px-2 py-1 rounded-full text-xs border flex items-center space-x-1 ${getRoleColor(role.role_type)}`}
                          title={`Type: ${role.role_type}, Source: ${role.assignment_source}, Assigned: ${new Date(role.assigned_at).toLocaleDateString()}`}
                        >
                          {getRoleIcon(role.role_type)}
                          <span>{role.display_name}</span>
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="p-2">
                    {user.azure_profile ? (
                      <div>
                        <div className="font-medium">{user.azure_profile.job_title}</div>
                        <div className="text-sm text-gray-600">{user.azure_profile.department}</div>
                      </div>
                    ) : (
                      <span className="text-gray-400">No Azure profile</span>
                    )}
                  </td>
                  <td className="p-2">
                    <div className="flex items-center space-x-1">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleViewPermissions(user)}
                        title="Manage Permissions"
                      >
                        <Key className="h-4 w-4" />
                      </Button>

                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setSelectedUser(user);
                          setIsRoleModalOpen(true);
                        }}
                        title="Assign Role"
                      >
                        <Plus className="h-4 w-4" />
                      </Button>

                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          if (confirm(`Are you sure you want to ${user.is_active ? "deactivate" : "activate"} ${user.name}?`)) {
                            handleToggleUserActive(user.id);
                          }
                        }}
                        title={user.is_active ? "Deactivate User" : "Activate User"}
                      >
                        {user.is_active ? (
                          <PowerOff className="h-4 w-4" />
                        ) : (
                          <Power className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Permission Management Modal */}
      {isPermissionModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Manage Permissions for {selectedUser?.name}</h2>
              <button
                onClick={() => setIsPermissionModalOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            <div className="space-y-4">
              <div className="border-b pb-2">
                <button
                  className={`px-4 py-2 rounded-t ${true ? 'bg-blue-100 text-blue-800 border-b-2 border-blue-800' : 'text-gray-600'}`}
                >
                  Current Permissions
                </button>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {Object.entries(userPermissions).map(([category, permissions]) => (
                  <div key={category} className="mb-4 p-4 border rounded">
                    <h4 className="font-semibold text-lg mb-2">
                      {category.replace("_", " ").toUpperCase()}
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {permissions.map((permission) => (
                        <span
                          key={permission.name}
                          className={`px-2 py-1 rounded text-xs ${
                            permission.has_permission
                              ? "bg-green-100 text-green-800"
                              : "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {permission.display_name}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Role Assignment Modal */}
      {isRoleModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Assign Role to {selectedUser?.name}</h2>
              <button
                onClick={() => setIsRoleModalOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Select Role</label>
                <select
                  value={selectedRoleId}
                  onChange={(e) => setSelectedRoleId(e.target.value)}
                  className="w-full p-2 border rounded"
                >
                  <option value="">Choose a role</option>
                  {roles.map((role) => (
                    <option key={role.id} value={role.id}>
                      {role.display_name} ({role.role_type})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end space-x-2">
                <Button
                  onClick={() => setIsRoleModalOpen(false)}
                  variant="outline"
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => {
                    if (selectedUser && selectedRoleId) {
                      handleAssignRole(selectedUser.id, selectedRoleId);
                      setIsRoleModalOpen(false);
                      setSelectedRoleId("");
                    }
                  }}
                  disabled={!selectedRoleId}
                >
                  Assign Role
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Role Modal */}
      <CreateRoleModal
        isOpen={isCreateRoleModalOpen}
        onClose={() => setIsCreateRoleModalOpen(false)}
        onSuccess={() => {
          setIsCreateRoleModalOpen(false);
          onRefresh();
        }}
      />
    </div>
  );
}

// Create Role Modal Component
function CreateRoleModal({ isOpen, onClose, onSuccess }: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [formData, setFormData] = useState({
    name: "",
    display_name: "",
    description: "",
    role_type: "custom",
    priority: 50,
    permissions: [] as string[],
  });

  const permissionCategories = [
    {
      name: "User Management",
      permissions: [
        { name: "users.create", display: "Create Users" },
        { name: "users.read", display: "View Users" },
        { name: "users.update", display: "Update Users" },
        { name: "users.delete", display: "Delete Users" },
      ],
    },
    {
      name: "Role Management",
      permissions: [
        { name: "roles.manage", display: "Manage Roles" },
      ],
    },
    {
      name: "Provider Management",
      permissions: [
        { name: "providers.create", display: "Create Providers" },
        { name: "providers.read", display: "View Providers" },
        { name: "providers.update", display: "Update Providers" },
        { name: "providers.delete", display: "Delete Providers" },
      ],
    },
    {
      name: "Scan Management",
      permissions: [
        { name: "scans.create", display: "Create Scans" },
        { name: "scans.read", display: "View Scans" },
        { name: "scans.execute", display: "Execute Scans" },
      ],
    },
    {
      name: "Audit Access",
      permissions: [
        { name: "audit.access", display: "Access Audit Logs" },
      ],
    },
  ];

  const handlePermissionToggle = (permissionName: string) => {
    setFormData(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permissionName)
        ? prev.permissions.filter(p => p !== permissionName)
        : [...prev.permissions, permissionName]
    }));
  };

  const handleSubmit = async () => {
    try {
      const form = new FormData();
      form.append("name", formData.name);
      form.append("display_name", formData.display_name);
      form.append("description", formData.description);
      form.append("role_type", formData.role_type);
      form.append("priority", formData.priority.toString());
      form.append("permissions", JSON.stringify(formData.permissions));

      const response = await fetch("/api/admin/create-role", {
        method: "POST",
        body: form,
      });

      const result = await response.json();

      if (result.error) {
        toast.error(result.error);
      } else {
        toast.success("Role created successfully");
        onSuccess();
      }
    } catch (error) {
      toast.error("Failed to create role");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Create New Role</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            ✕
          </button>
        </div>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Role Name</label>
              <input
                type="text"
                placeholder="e.g., security_analyst"
                value={formData.name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Display Name</label>
              <input
                type="text"
                placeholder="e.g., Security Analyst"
                value={formData.display_name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData(prev => ({ ...prev, display_name: e.target.value }))}
                className="w-full p-2 border rounded"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Description</label>
            <textarea
              placeholder="Role description"
              value={formData.description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full p-2 border rounded"
              rows={3}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Role Type</label>
              <select
                value={formData.role_type}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFormData(prev => ({ ...prev, role_type: e.target.value }))}
                className="w-full p-2 border rounded"
              >
                <option value="custom">Custom</option>
                <option value="azure_sync">Azure AD Synced</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Priority</label>
              <input
                type="number"
                min="0"
                max="100"
                value={formData.priority}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData(prev => ({ ...prev, priority: parseInt(e.target.value) }))}
                className="w-full p-2 border rounded"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Permissions</label>
            <div className="max-h-60 overflow-y-auto border rounded-md p-4 space-y-4">
              {permissionCategories.map((category) => (
                <div key={category.name}>
                  <h4 className="font-semibold text-sm mb-2">{category.name}</h4>
                  <div className="space-y-2">
                    {category.permissions.map((permission) => (
                      <div key={permission.name} className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id={permission.name}
                          checked={formData.permissions.includes(permission.name)}
                          onChange={() => handlePermissionToggle(permission.name)}
                          className="rounded"
                        />
                        <label htmlFor={permission.name} className="text-sm">
                          {permission.display}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="flex justify-end mt-6">
          <Button onClick={handleSubmit} disabled={!formData.name || !formData.display_name}>
            Create Role
          </Button>
        </div>
      </div>
    </div>
  );
}
