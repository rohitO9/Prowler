'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession, getSession } from 'next-auth/react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Loader2, 
  Shield, 
  Users, 
  Settings, 
  CheckCircle, 
  AlertCircle,
  Copy,
  RefreshCw,
  UserPlus,
  Mail,
  KeyRound,
  ExternalLink,
  Info,
  Eye,
  X,
  Trash2
} from 'lucide-react';
import { useToast } from '@/components/ui/toast/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog/dialog';
import { DEV_APP_HOST_DISPLAY } from '@/lib/env';

interface TenantInfo {
  id: string;
  name: string;
  subdomain: string;
  is_active: boolean;
}

interface SSOConfig {
  id: string;
  azure_tenant_id: string;
  client_id: string;
  scim_url: string;
  scim_bearer_token: string;
  is_active: boolean;
}

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  department: string;
  job_title: string;
  role: string;
  is_active: boolean;
  is_sso_user: boolean;
  invite_status: string;
  invited_at?: string;
  accepted_invite_at?: string;
  permissions?: {
    can_run_scans?: boolean;
    can_export_reports?: boolean;
    can_invite_users?: boolean;
    can_manage_users?: boolean;
    can_manage_settings?: boolean;
    can_view_analytics?: boolean;
    can_manage_billing?: boolean;
    can_manage_providers?: boolean;
    can_manage_integrations?: boolean;
    can_manage_scans?: boolean;
    unlimited_visibility?: boolean;
  };
}

export function AzureADConfigClient() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [isSSOLoading, setIsSSOLoading] = useState(false);
  const [isSyncLoading, setIsSyncLoading] = useState(false);
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [ssoConfig, setSSOConfig] = useState<SSOConfig | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ssoFormData, setSSOFormData] = useState({
    azure_tenant_id: '',
    client_id: '',
    client_secret: ''
  });
  const [activeTab, setActiveTab] = useState('configuration');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);

  // Check authentication status
  useEffect(() => {
    if (status === 'loading') {
      return; // Still loading
    }
    
    if (status === 'unauthenticated') {
      toast({
        title: 'Authentication Required',
        description: 'Please sign in to access Azure AD configuration.',
        variant: 'destructive',
      });
      router.push('/sign-in');
      return;
    }
    
    if (status === 'authenticated') {
      loadTenantData();
    }
  }, [status, router, toast]);

  const loadTenantData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Get the session to get the access token
      const session = await getSession();
      if (!session?.accessToken) {
        console.log('No access token available');
        setIsLoading(false);
        return;
      }

      const authHeaders = {
        'Authorization': `Bearer ${session.accessToken}`,
      };
      
      // Load tenant info
      const tenantResponse = await fetch('/api/v1/tenant/public-info', {
        headers: authHeaders,
      });
      if (tenantResponse.ok) {
        const tenantData = await tenantResponse.json();
        setTenant(tenantData);
      } else if (tenantResponse.status === 400) {
        // Handle case when tenant info is not available
        console.log('Tenant info not available yet');
      } else {
        console.error('Failed to load tenant info:', tenantResponse.status);
      }

      // Load SSO config
      const ssoResponse = await fetch('/api/sso-config', {
        headers: authHeaders,
      });
      if (ssoResponse.ok) {
        const ssoData = await ssoResponse.json();
        setSSOConfig(ssoData);
        if (ssoData) {
          setSSOFormData({
            azure_tenant_id: ssoData.azure_tenant_id || '',
            client_id: ssoData.client_id || '',
            client_secret: ''
          });
        }
      } else if (ssoResponse.status === 404) {
        // SSO not configured yet - this is normal
        console.log('SSO not configured yet');
        setSSOConfig(null);
      } else {
        const errorData = await ssoResponse.json().catch(() => ({}));
        console.error('Failed to load SSO config:', ssoResponse.status, errorData);
        setSSOConfig(null);
      }

      // Load users
      await loadUsers();
    } catch (err) {
      console.error('Error loading tenant data:', err);
      setError('Failed to load tenant data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      // Get the session to get the access token
      const session = await getSession();
      if (!session?.accessToken) {
        console.log('No access token available for users');
        return;
      }

      const response = await fetch('/api/v1/tenant/users', {
        headers: {
          'Authorization': `Bearer ${session.accessToken}`,
        },
      });
      if (response.ok) {
        const responseData = await response.json();
        
        // Handle response wrapped in 'data' object
        const data = responseData.data || responseData;
        const usersArray = data.users || [];
        
        setUsers(usersArray);
      } else if (response.status === 400) {
        // No users available yet - this is normal when SSO is not configured
        console.log('No users available yet');
        setUsers([]);
      } else {
        console.error('Failed to load users:', response.status);
      }
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  };

  const handleSSOSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSSOLoading(true);
    setError(null);

    try {
      // Get the session to get the access token
      const session = await getSession();
      if (!session?.accessToken) {
        toast({
          title: 'Authentication Required',
          description: 'Please sign in to configure Azure AD SSO.',
          variant: 'destructive',
        });
        return;
      }

      const response = await fetch('/api/sso-config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.accessToken}`,
        },
        body: JSON.stringify(ssoFormData),
      });

      if (response.ok) {
        const data = await response.json();
        
        // If response includes full SSO config, use it; otherwise reload
        if (data.is_active !== undefined) {
          setSSOConfig(data);
          setSSOFormData({
            azure_tenant_id: data.azure_tenant_id || '',
            client_id: data.client_id || '',
            client_secret: '' // Never store secret in form after save
          });
        } else {
          // Reload the SSO config to get the full config with is_active
          await loadTenantData();
        }
        
        toast({
          title: '✅ SSO Configuration Saved',
          description: 'Azure AD SSO has been configured successfully and is now active.',
        });
      } else {
        const errorData = await response.json();
        setError(errorData.message || 'Failed to configure SSO');
      }
    } catch (err) {
      console.error('Error configuring SSO:', err);
      setError('Failed to configure SSO. Please try again.');
    } finally {
      setIsSSOLoading(false);
    }
  };

  const handleSyncUsers = async () => {
    setIsSyncLoading(true);
    setError(null);

    try {
      // Get the session to get the access token
      const session = await getSession();
      if (!session?.accessToken) {
        toast({
          title: 'Authentication Required',
          description: 'Please sign in to sync users.',
          variant: 'destructive',
        });
        return;
      }

      const response = await fetch('/api/v1/tenant/sync-users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.accessToken}`,
        },
      });

      if (response.ok) {
        const syncData = await response.json();
        console.log('🔍 [handleSyncUsers] Sync response:', syncData);
        await loadUsers();
        
        // Build detailed message from stats
        const stats = syncData.stats || {};
        const messageParts = [];
        
        if (stats.created > 0) {
          messageParts.push(`${stats.created} new user(s) created`);
        }
        if (stats.skipped_existing > 0) {
          messageParts.push(`${stats.skipped_existing} existing user(s) skipped`);
        }
        if (stats.memberships_created > 0) {
          messageParts.push(`${stats.memberships_created} membership(s) created`);
        }
        
        let description = messageParts.length > 0 
          ? messageParts.join(', ') 
          : 'User sync completed.';
        
        // Add warning about existing users
        if (stats.skipped_existing > 0 && stats.existing_users && stats.existing_users.length > 0) {
          description += ` ${stats.existing_users.length} user(s) already exist in other tenant(s) and were not added.`;
        }
        
        toast({
          title: 'Users Synced',
          description: description,
          variant: stats.skipped_existing > 0 ? 'default' : 'default',
        });
      } else {
        const errorData = await response.json();
        setError(errorData.message || 'Failed to sync users');
        toast({
          title: 'Sync Failed',
          description: errorData.message || 'Failed to sync users',
          variant: 'destructive',
        });
      }
    } catch (err) {
      console.error('Error syncing users:', err);
      setError('Failed to sync users. Please try again.');
    } finally {
      setIsSyncLoading(false);
    }
  };

  const handleInviteUser = async (email: string, role: string) => {
    try {
      // Get the session to get the access token
      const session = await getSession();
      if (!session?.accessToken) {
        toast({
          title: 'Authentication Required',
          description: 'Please sign in to invite users.',
          variant: 'destructive',
        });
        return;
      }

      const response = await fetch('/api/v1/tenant/invite-user', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.accessToken}`,
        },
        body: JSON.stringify({ email, role }),
      });

      const responseData = await response.json();
      if (response.ok) {
        // Check if invite is already pending
        if (responseData.invite_status === 'pending') {
          toast({
            title: 'Already Invited',
            description: responseData.message || `User ${email} has already been invited.`,
          });
        } else {
          toast({
            title: 'Invitation Sent',
            description: responseData.message || `Invitation sent to ${email}`,
          });
        }
        // Reload users to update invite status
        loadUsers();
      } else {
        // Check if user is already invited
        if (responseData.invite_status === 'pending' || responseData.invite_status === 'accepted') {
          toast({
            title: 'Already Invited',
            description: responseData.error || responseData.message || `User ${email} has already been invited.`,
          });
        } else {
          toast({
            title: 'Failed to Send Invitation',
            description: responseData.error || responseData.message || 'Please try again.',
            variant: 'destructive',
          });
        }
        // Reload users to update invite status
        loadUsers();
      }
    } catch (err) {
      console.error('Error sending invitation:', err);
      toast({
        title: 'Failed to Send Invitation',
        description: 'Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteUser = async (userId: string, email: string) => {
    if (!confirm(`Are you sure you want to remove ${email} from this tenant? This action cannot be undone.`)) {
      return;
    }

    try {
      const session = await getSession();
      if (!session?.accessToken) {
        toast({
          title: 'Authentication Required',
          description: 'Please sign in to delete users.',
          variant: 'destructive',
        });
        return;
      }

      const response = await fetch(`/api/v1/tenant/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.accessToken}`,
        },
      });

      if (response.ok) {
        toast({
          title: 'User Removed',
          description: `${email} has been removed from the tenant.`,
        });
        // Reload users
        loadUsers();
        // Close modal if open
        if (selectedUser?.id === userId) {
          closeUserDetails();
        }
      } else {
        const errorData = await response.json();
        toast({
          title: 'Failed to Remove User',
          description: errorData.error || 'Please try again.',
          variant: 'destructive',
        });
      }
    } catch (err) {
      console.error('Error deleting user:', err);
      toast({
        title: 'Failed to Remove User',
        description: 'Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleUpdatePermissions = async (userId: string, permissions: Record<string, boolean>) => {
    try {
      const session = await getSession();
      if (!session?.accessToken) {
        toast({
          title: 'Authentication Required',
          description: 'Please sign in to update permissions.',
          variant: 'destructive',
        });
        return;
      }

      const response = await fetch(`/api/v1/tenant/users/${userId}/permissions`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.accessToken}`,
        },
        body: JSON.stringify({ permissions }),
      });

      if (response.ok) {
        const responseData = await response.json();
        const updatedPermissions = responseData.permissions || permissions;
        
        toast({
          title: 'Permissions Updated',
          description: 'User permissions have been updated successfully.',
        });
        
        // Update selectedUser state immediately with response data for real-time UI update
        if (selectedUser?.id === userId) {
          setSelectedUser(prev => {
            if (prev && prev.id === userId) {
              return {
                ...prev,
                permissions: updatedPermissions
              };
            }
            return prev;
          });
        }
        
        // Update users array to reflect the change in the table
        setUsers(prevUsers => 
          prevUsers.map(user => 
            user.id === userId 
              ? { ...user, permissions: updatedPermissions }
              : user
          )
        );
        
        // Reload users from backend to ensure consistency
        await loadUsers();
      } else {
        const errorData = await response.json();
        toast({
          title: 'Failed to Update Permissions',
          description: errorData.error || 'Please try again.',
          variant: 'destructive',
        });
      }
    } catch (err) {
      console.error('Error updating permissions:', err);
      toast({
        title: 'Failed to Update Permissions',
        description: 'Please try again.',
        variant: 'destructive',
      });
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: 'Copied to Clipboard',
      description: `${label} copied successfully.`,
    });
  };

  const openUserDetails = (user: User) => {
    setSelectedUser(user);
    setIsUserModalOpen(true);
  };

  const closeUserDetails = () => {
    setIsUserModalOpen(false);
    setSelectedUser(null);
  };

  // Update selected user when users array changes
  // Preserve permissions if they were just updated (to avoid overwriting real-time updates)
  useEffect(() => {
    if (selectedUser && users.length > 0) {
      const updatedUser = users.find(u => u.id === selectedUser.id);
      if (updatedUser) {
        // Preserve permissions from selectedUser if they exist (might be more recent)
        setSelectedUser(prev => {
          if (prev && prev.id === updatedUser.id && prev.permissions) {
            // Merge permissions - prefer selectedUser permissions if they exist
            return {
              ...updatedUser,
              permissions: prev.permissions || updatedUser.permissions
            };
          }
          return updatedUser;
        });
      }
    }
  }, [users, selectedUser?.id]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="default">Active</Badge>;
      case 'inactive':
        return <Badge variant="secondary">Inactive</Badge>;
      case 'pending':
        return <Badge variant="outline">Pending</Badge>;
      default:
        return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  if (status === 'loading' || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-indigo-600 dark:text-indigo-400" />
          <p className="text-gray-600 dark:text-gray-400">
            {status === 'loading' ? 'Checking authentication...' : 'Loading Azure AD configuration...'}
          </p>
        </div>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <AlertCircle className="h-8 w-8 text-red-500 dark:text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Authentication Required</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">Please sign in to access Azure AD configuration.</p>
          <Button onClick={() => router.push('/sign-in')} className="bg-indigo-600 hover:bg-indigo-700 text-white">
            Go to Sign In
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      {/* Page Header */}
      <div className="mb-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 shadow-lg">
              <KeyRound className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Azure AD Configuration</h1>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {tenant?.name ? `${tenant.name} - Single Sign-On Setup` : 'Single Sign-On Setup'}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <Badge 
              variant={ssoConfig?.is_active ? "default" : ssoConfig ? "secondary" : "destructive"}
              className="px-4 py-1.5 text-sm font-semibold"
            >
              {ssoConfig?.is_active ? 'SSO Active' : ssoConfig ? 'SSO Configured (Inactive)' : 'SSO Not Configured'}
            </Badge>
          </div>
        </div>
      </div>

      {error && (
        <Alert className="mb-6" variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-6">
        {/* Tab Navigation */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('configuration')}
              className={`py-3 px-1 border-b-2 font-semibold text-sm transition-colors ${
                activeTab === 'configuration'
                  ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              Configuration
            </button>
            <button
              onClick={() => setActiveTab('scim-setup')}
              className={`py-3 px-1 border-b-2 font-semibold text-sm transition-colors ${
                activeTab === 'scim-setup'
                  ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              SCIM Setup
            </button>
            <button
              onClick={() => setActiveTab('users')}
              className={`py-3 px-1 border-b-2 font-semibold text-sm transition-colors ${
                activeTab === 'users'
                  ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              User Management
            </button>
            <button
              onClick={() => setActiveTab('setup-guide')}
              className={`py-3 px-1 border-b-2 font-semibold text-sm transition-colors ${
                activeTab === 'setup-guide'
                  ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              Setup Guide
            </button>
          </nav>
        </div>

        {/* Configuration Tab */}
        {activeTab === 'configuration' && (
        <div className="space-y-6">
          <Card className="shadow-xl border-0 bg-white dark:bg-gray-800">
            <CardHeader className="pb-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900">
                  <Settings className="h-5 w-5 text-indigo-600 dark:text-indigo-300" />
                </div>
                <div>
                  <CardTitle className="text-xl font-bold text-gray-900 dark:text-white">
                    Azure AD SSO Configuration
                  </CardTitle>
                  <CardDescription className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Configure your Azure AD application for single sign-on integration.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <form onSubmit={handleSSOSetup} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="azure_tenant_id" className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Azure Tenant ID
                    </Label>
                    <Input
                      id="azure_tenant_id"
                      value={ssoFormData.azure_tenant_id}
                      onChange={(e) => setSSOFormData({ ...ssoFormData, azure_tenant_id: e.target.value })}
                      placeholder="Enter your Azure Tenant ID"
                      required
                      className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="client_id" className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Client ID
                    </Label>
                    <Input
                      id="client_id"
                      value={ssoFormData.client_id}
                      onChange={(e) => setSSOFormData({ ...ssoFormData, client_id: e.target.value })}
                      placeholder="Enter your Azure AD Client ID"
                      required
                      className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="client_secret" className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Client Secret
                  </Label>
                  <Input
                    id="client_secret"
                    type="password"
                    value={ssoFormData.client_secret}
                    onChange={(e) => setSSOFormData({ ...ssoFormData, client_secret: e.target.value })}
                    placeholder="Enter your Azure AD Client Secret"
                    required
                    className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500"
                  />
                </div>
                <Button 
                  type="submit" 
                  disabled={isSSOLoading} 
                  className="w-full bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white shadow-lg"
                >
                  {isSSOLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Configuring SSO...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Configure SSO
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
        )}

        {/* SCIM Setup Tab */}
        {activeTab === 'scim-setup' && (
        <div className="space-y-6">
          <Card className="shadow-xl border-0 bg-white dark:bg-gray-800">
            <CardHeader className="pb-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900">
                  <Users className="h-5 w-5 text-indigo-600 dark:text-indigo-300" />
                </div>
                <div>
                  <CardTitle className="text-xl font-bold text-gray-900 dark:text-white">
                    SCIM Provisioning
                  </CardTitle>
                  <CardDescription className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Configure SCIM for automatic user provisioning from Azure AD.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              {ssoConfig ? (
                <>
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      SCIM Endpoint URL
                    </Label>
                    <div className="flex items-center gap-2">
                      <Input
                        value={ssoConfig.scim_url}
                        readOnly
                        className="bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white font-mono text-sm"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(ssoConfig.scim_url, 'SCIM URL')}
                        className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      SCIM Bearer Token
                    </Label>
                    <div className="flex items-center gap-2">
                      <Input
                        value={ssoConfig.scim_bearer_token}
                        readOnly
                        type="password"
                        className="bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white font-mono text-sm"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(ssoConfig.scim_bearer_token, 'SCIM Token')}
                        className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  <Alert className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
                    <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    <AlertDescription className="text-blue-800 dark:text-blue-200">
                      Use these credentials to configure SCIM provisioning in your Azure AD application.
                    </AlertDescription>
                  </Alert>
                </>
              ) : (
                <Alert variant="destructive" className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
                  <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                  <AlertDescription className="text-red-800 dark:text-red-200">
                    Please configure SSO first to enable SCIM provisioning.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </div>
        )}

        {/* User Management Tab */}
        {activeTab === 'users' && (
        <div className="space-y-6">
          <Card className="shadow-xl border-0 bg-white dark:bg-gray-800">
            <CardHeader className="pb-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900">
                    <Users className="h-5 w-5 text-indigo-600 dark:text-indigo-300" />
                  </div>
                  <div>
                    <CardTitle className="text-xl font-bold text-gray-900 dark:text-white">
                      User Management
                    </CardTitle>
                    <CardDescription className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Manage users synced from Azure AD and send invitations.
                    </CardDescription>
                  </div>
                </div>
                <Button 
                  onClick={handleSyncUsers} 
                  disabled={isSyncLoading}
                  className="bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white shadow-lg"
                >
                  {isSyncLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Sync Users
                    </>
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              {users.length > 0 ? (
                <>
                  <div className="mb-6 flex items-center justify-between">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Showing <span className="font-semibold text-gray-900 dark:text-white">{users.length}</span> user{users.length !== 1 ? 's' : ''}
                    </p>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={loadUsers}
                      className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Refresh
                    </Button>
                  </div>
                  <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-700">
                      <tr>
                        <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Name</th>
                        <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Email</th>
                        <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Role</th>
                        <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Department</th>
                        <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Status</th>
                        <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                      {users.map((user) => (
                        <tr 
                          key={user.id} 
                          className="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
                          onClick={() => openUserDetails(user)}
                        >
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-blue-600 rounded-full flex items-center justify-center mr-3 shadow-md">
                                <Users className="h-5 w-5 text-white" />
                              </div>
                              <div>
                                <div className="text-sm font-semibold text-gray-900 dark:text-white">
                                  {[user.first_name, user.last_name].filter(Boolean).join(' ') || user.email.split('@')[0]}
                                </div>
                                {(user.job_title || user.department) && (
                                  <div className="text-xs text-gray-500 dark:text-gray-400">
                                    {[user.department, user.job_title].filter(Boolean).join(' • ') || '-'}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900 dark:text-white">{user.email}</div>
                            {user.is_sso_user && (
                              <div className="text-xs text-indigo-600 dark:text-indigo-400 font-medium">SSO User</div>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <Badge variant={user.role === 'admin' ? 'default' : 'secondary'}>
                              {user.role}
                            </Badge>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                            {user.department && user.department.trim() ? user.department : '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {getStatusBadge(user.is_active ? 'active' : 'inactive')}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => openUserDetails(user)}
                                className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                              >
                                <Eye className="h-4 w-4 mr-1" />
                                View
                              </Button>
                              {user.invite_status === 'not_invited' ? (
                                <Button
                                  size="sm"
                                  onClick={() => handleInviteUser(user.email, user.role)}
                                  className="bg-indigo-600 hover:bg-indigo-700 text-white"
                                >
                                  <Mail className="h-4 w-4 mr-1" />
                                  Invite
                                </Button>
                              ) : user.invite_status === 'pending' ? (
                                <Badge variant="outline" className="border-yellow-300 dark:border-yellow-600 text-yellow-700 dark:text-yellow-400">Invited</Badge>
                              ) : user.invite_status === 'accepted' ? (
                                <Badge variant="default" className="bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300">Accepted</Badge>
                              ) : (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleInviteUser(user.email, user.role)}
                                  className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                                >
                                  <Mail className="h-4 w-4 mr-1" />
                                  Re-invite
                                </Button>
                              )}
                              <Button
                                size="sm"
                                variant="destructive"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteUser(user.id, user.email);
                                }}
                              >
                                <Trash2 className="h-4 w-4 mr-1" />
                                Delete
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  </div>
                </>
              ) : (
                <div className="text-center py-12 bg-gray-50 dark:bg-gray-700/50 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600">
                  <Users className="h-12 w-12 text-gray-400 dark:text-gray-500 mx-auto mb-4" />
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">No users found</p>
                  <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">Sync users from Azure AD to get started</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
        )}

        {/* Setup Guide Tab */}
        {activeTab === 'setup-guide' && (
        <div className="space-y-6">
          <Card className="shadow-xl border-0 bg-white dark:bg-gray-800">
            <CardHeader className="pb-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900">
                  <Shield className="h-5 w-5 text-indigo-600 dark:text-indigo-300" />
                </div>
                <div>
                  <CardTitle className="text-xl font-bold text-gray-900 dark:text-white">
                    Azure AD Setup Guide
                  </CardTitle>
                  <CardDescription className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Follow these steps to configure Azure AD integration.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-8">
              <div className="space-y-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  <span className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold">1</span>
                  Create Azure AD Application
                </h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700 dark:text-gray-300 ml-10">
                  <li>Go to Azure Portal → Azure Active Directory → App registrations</li>
                  <li>Click "New registration"</li>
                  <li>Enter application name: "Prowler SSO"</li>
                  <li>Select "Single tenant"</li>
                  <li>Set redirect URI: &quot;https://{tenant?.subdomain}.{DEV_APP_HOST_DISPLAY}/api/auth/callback/azure&quot;</li>
                  <li>Click "Register"</li>
                </ol>
              </div>

              <div className="space-y-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  <span className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold">2</span>
                  Configure Authentication
                </h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700 dark:text-gray-300 ml-10">
                  <li>Go to Authentication → Platform configurations</li>
                  <li>Add Web platform</li>
                  <li>Set redirect URI: &quot;https://{tenant?.subdomain}.{DEV_APP_HOST_DISPLAY}/api/auth/callback/azure&quot;</li>
                  <li>Enable "ID tokens" and "Access tokens"</li>
                  <li>Save configuration</li>
                </ol>
              </div>

              <div className="space-y-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  <span className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold">3</span>
                  Create Client Secret
                </h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700 dark:text-gray-300 ml-10">
                  <li>Go to Certificates & secrets</li>
                  <li>Click "New client secret"</li>
                  <li>Add description: "Prowler SSO Secret"</li>
                  <li>Set expiration (recommended: 24 months)</li>
                  <li>Click "Add" and copy the secret value</li>
                </ol>
              </div>

              <div className="space-y-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  <span className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold">4</span>
                  Configure SCIM (Optional)
                </h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700 dark:text-gray-300 ml-10">
                  <li>Go to Enterprise applications → Your app → Provisioning</li>
                  <li>Set provisioning mode to "Automatic"</li>
                  <li>Set tenant URL: "{ssoConfig?.scim_url || 'SCIM URL will appear after SSO setup'}"</li>
                  <li>Set secret token: "{ssoConfig?.scim_bearer_token || 'SCIM Token will appear after SSO setup'}"</li>
                  <li>Test connection and save</li>
                </ol>
              </div>

              <Alert className="bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800">
                <Info className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                <AlertDescription className="text-indigo-800 dark:text-indigo-200">
                  After completing these steps, return to the Configuration tab and enter your Azure Tenant ID, Client ID, and Client Secret to activate the integration.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </div>
        )}
      </div>

      {/* User Details Modal */}
      <Dialog open={isUserModalOpen} onOpenChange={setIsUserModalOpen}>
        <DialogContent className="max-w-2xl bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-gray-900 dark:text-white">User Details</DialogTitle>
            <DialogDescription className="text-sm text-gray-600 dark:text-gray-400">
              View and manage user information
            </DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="space-y-6">
              {/* User Avatar and Basic Info */}
              <div className="flex items-start gap-4 pb-6 border-b border-gray-200 dark:border-gray-700">
                <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-blue-600 rounded-full flex items-center justify-center shadow-lg">
                  <Users className="h-8 w-8 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                    {selectedUser.first_name} {selectedUser.last_name}
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{selectedUser.email}</p>
                  {selectedUser.job_title && (
                    <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">{selectedUser.job_title}</p>
                  )}
                  <div className="flex items-center gap-2 mt-3">
                    <Badge variant={selectedUser.role === 'admin' ? 'default' : 'secondary'}>
                      {selectedUser.role}
                    </Badge>
                    {selectedUser.is_sso_user && (
                      <Badge variant="outline" className="border-indigo-500 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400">
                        SSO User
                      </Badge>
                    )}
                    {getStatusBadge(selectedUser.is_active ? 'active' : 'inactive')}
                  </div>
                </div>
              </div>

              {/* User Details Grid */}
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Department</Label>
                  <p className="text-sm font-medium text-gray-900 dark:text-white mt-2">
                    {selectedUser.department || 'Not specified'}
                  </p>
                </div>
                <div>
                  <Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Job Title</Label>
                  <p className="text-sm font-medium text-gray-900 dark:text-white mt-2">
                    {selectedUser.job_title || 'Not specified'}
                  </p>
                </div>
                <div>
                  <Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Invite Status</Label>
                  <div className="mt-2">
                    {getStatusBadge(selectedUser.invite_status)}
                  </div>
                </div>
                <div>
                  <Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">User ID</Label>
                  <div className="flex items-center gap-2 mt-2">
                    <p className="text-sm font-mono text-gray-700 dark:text-gray-300 truncate">{selectedUser.id}</p>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => copyToClipboard(selectedUser.id, 'User ID')}
                      className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Invite Information */}
              {selectedUser.invited_at && (
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Invitation Details</Label>
                  <div className="mt-3 space-y-2">
                    <p className="text-sm text-gray-700 dark:text-gray-300">
                      <span className="font-medium">Invited:</span> {new Date(selectedUser.invited_at).toLocaleString()}
                    </p>
                    {selectedUser.accepted_invite_at && (
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        <span className="font-medium">Accepted:</span> {new Date(selectedUser.accepted_invite_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Permissions Management */}
              {selectedUser.permissions && (
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-4 block">Permissions</Label>
                  <div className="space-y-3">
                    {Object.entries(selectedUser.permissions).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                        <Label className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                          {key.replace(/_/g, ' ')}
                        </Label>
                        <Button
                          size="sm"
                          variant={value ? "default" : "outline"}
                          onClick={async () => {
                            if (selectedUser) {
                              // Optimistically update UI immediately
                              const newValue = !value;
                              const updatedPermissions = {
                                ...selectedUser.permissions,
                                [key]: newValue
                              };
                              
                              // Update selectedUser state immediately for instant UI feedback
                              setSelectedUser({
                                ...selectedUser,
                                permissions: updatedPermissions
                              });
                              
                              // Then sync with backend
                              await handleUpdatePermissions(selectedUser.id, updatedPermissions);
                            }
                          }}
                          className={value ? "bg-indigo-600 hover:bg-indigo-700 text-white" : "border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300"}
                        >
                          {value ? 'Enabled' : 'Disabled'}
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter className="flex justify-between">
            <Button
              variant="destructive"
              onClick={() => {
                if (selectedUser) {
                  handleDeleteUser(selectedUser.id, selectedUser.email);
                }
              }}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Remove User
            </Button>
            <div className="flex space-x-2">
              <Button variant="outline" onClick={closeUserDetails}>
                Close
              </Button>
              {selectedUser?.invite_status === 'not_invited' && (
                <Button onClick={() => {
                  if (selectedUser) {
                    handleInviteUser(selectedUser.email, selectedUser.role);
                  }
                }}>
                  <Mail className="h-4 w-4 mr-2" />
                  Send Invite
                </Button>
              )}
              {selectedUser?.invite_status === 'pending' && (
                <Button
                  variant="outline"
                  onClick={() => {
                    if (selectedUser) {
                      handleInviteUser(selectedUser.email, selectedUser.role);
                    }
                  }}
                >
                  <Mail className="h-4 w-4 mr-2" />
                  Resend Invite
                </Button>
              )}
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
