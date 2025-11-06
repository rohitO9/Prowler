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
        toast({
          title: 'Users Synced',
          description: 'Users have been synced from Azure AD successfully.',
        });
      } else {
        const errorData = await response.json();
        setError(errorData.message || 'Failed to sync users');
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
        toast({
          title: 'Permissions Updated',
          description: 'User permissions have been updated successfully.',
        });
        // Reload users to get updated permissions
        loadUsers();
        // Update selected user if modal is open - reload and update after a short delay
        if (selectedUser?.id === userId) {
          setTimeout(async () => {
            await loadUsers();
            // The loadUsers will update the users array, we can update selected user from there
            // This will be handled by the users array update
          }, 500);
        }
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
  useEffect(() => {
    if (selectedUser && users.length > 0) {
      const updatedUser = users.find(u => u.id === selectedUser.id);
      if (updatedUser) {
        setSelectedUser(updatedUser);
      }
    }
  }, [users]);

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
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">
            {status === 'loading' ? 'Checking authentication...' : 'Loading Azure AD configuration...'}
          </p>
        </div>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Authentication Required</h2>
          <p className="text-gray-600 mb-4">Please sign in to access Azure AD configuration.</p>
          <Button onClick={() => router.push('/sign-in')}>
            Go to Sign In
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <KeyRound className="h-8 w-8 text-blue-600 mr-3" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Azure AD Configuration</h1>
              <p className="text-sm text-gray-500">
                {tenant?.name ? `${tenant.name} - Single Sign-On Setup` : 'Single Sign-On Setup'}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <Badge variant={ssoConfig?.is_active ? "default" : ssoConfig ? "secondary" : "destructive"}>
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
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('configuration')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'configuration'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Configuration
            </button>
            <button
              onClick={() => setActiveTab('scim-setup')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'scim-setup'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              SCIM Setup
            </button>
            <button
              onClick={() => setActiveTab('users')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'users'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              User Management
            </button>
            <button
              onClick={() => setActiveTab('setup-guide')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'setup-guide'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Setup Guide
            </button>
          </nav>
        </div>

        {/* Configuration Tab */}
        {activeTab === 'configuration' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Settings className="h-5 w-5 mr-2" />
                Azure AD SSO Configuration
              </CardTitle>
              <CardDescription>
                Configure your Azure AD application for single sign-on integration.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSSOSetup} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="azure_tenant_id">Azure Tenant ID</Label>
                    <Input
                      id="azure_tenant_id"
                      value={ssoFormData.azure_tenant_id}
                      onChange={(e) => setSSOFormData({ ...ssoFormData, azure_tenant_id: e.target.value })}
                      placeholder="Enter your Azure Tenant ID"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="client_id">Client ID</Label>
                    <Input
                      id="client_id"
                      value={ssoFormData.client_id}
                      onChange={(e) => setSSOFormData({ ...ssoFormData, client_id: e.target.value })}
                      placeholder="Enter your Azure AD Client ID"
                      required
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="client_secret">Client Secret</Label>
                  <Input
                    id="client_secret"
                    type="password"
                    value={ssoFormData.client_secret}
                    onChange={(e) => setSSOFormData({ ...ssoFormData, client_secret: e.target.value })}
                    placeholder="Enter your Azure AD Client Secret"
                    required
                  />
                </div>
                <Button type="submit" disabled={isSSOLoading} className="w-full">
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
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Users className="h-5 w-5 mr-2" />
                SCIM Provisioning
              </CardTitle>
              <CardDescription>
                Configure SCIM for automatic user provisioning from Azure AD.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {ssoConfig ? (
                <>
                  <div className="space-y-2">
                    <Label>SCIM Endpoint URL</Label>
                    <div className="flex items-center space-x-2">
                      <Input
                        value={ssoConfig.scim_url}
                        readOnly
                        className="bg-gray-50"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(ssoConfig.scim_url, 'SCIM URL')}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>SCIM Bearer Token</Label>
                    <div className="flex items-center space-x-2">
                      <Input
                        value={ssoConfig.scim_bearer_token}
                        readOnly
                        type="password"
                        className="bg-gray-50"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(ssoConfig.scim_bearer_token, 'SCIM Token')}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      Use these credentials to configure SCIM provisioning in your Azure AD application.
                    </AlertDescription>
                  </Alert>
                </>
              ) : (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
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
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center">
                  <Users className="h-5 w-5 mr-2" />
                  User Management
                </div>
                <Button onClick={handleSyncUsers} disabled={isSyncLoading}>
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
              </CardTitle>
              <CardDescription>
                Manage users synced from Azure AD and send invitations.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {users.length > 0 ? (
                <>
                  <div className="mb-4 flex items-center justify-between">
                    <p className="text-sm text-gray-600">
                      Showing <span className="font-medium text-gray-900">{users.length}</span> user{users.length !== 1 ? 's' : ''}
                    </p>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={loadUsers}
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Refresh
                    </Button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Department</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {users.map((user) => (
                        <tr 
                          key={user.id} 
                          className="hover:bg-gray-50 cursor-pointer transition-colors"
                          onClick={() => openUserDetails(user)}
                        >
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                                <Users className="h-5 w-5 text-blue-600" />
                              </div>
                              <div>
                                <div className="text-sm font-medium text-gray-900">
                                  {[user.first_name, user.last_name].filter(Boolean).join(' ') || user.email.split('@')[0]}
                                </div>
                                {(user.job_title || user.department) && (
                                  <div className="text-xs text-gray-500">
                                    {[user.department, user.job_title].filter(Boolean).join(' • ') || '-'}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">{user.email}</div>
                            {user.is_sso_user && (
                              <div className="text-xs text-blue-600">SSO User</div>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <Badge variant={user.role === 'admin' ? 'default' : 'secondary'}>
                              {user.role}
                            </Badge>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {user.department && user.department.trim() ? user.department : '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {getStatusBadge(user.is_active ? 'active' : 'inactive')}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center space-x-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => openUserDetails(user)}
                              >
                                <Eye className="h-4 w-4 mr-1" />
                                View
                              </Button>
                              {user.invite_status === 'not_invited' ? (
                                <Button
                                  size="sm"
                                  onClick={() => handleInviteUser(user.email, user.role)}
                                >
                                  <Mail className="h-4 w-4 mr-1" />
                                  Invite
                                </Button>
                              ) : user.invite_status === 'pending' ? (
                                <Badge variant="outline">Invited</Badge>
                              ) : user.invite_status === 'accepted' ? (
                                <Badge variant="default">Accepted</Badge>
                              ) : (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleInviteUser(user.email, user.role)}
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
                <div className="text-center py-8">
                  <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">No users found. Sync users from Azure AD to get started.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
        )}

        {/* Setup Guide Tab */}
        {activeTab === 'setup-guide' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Shield className="h-5 w-5 mr-2" />
                Azure AD Setup Guide
              </CardTitle>
              <CardDescription>
                Follow these steps to configure Azure AD integration.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Step 1: Create Azure AD Application</h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
                  <li>Go to Azure Portal → Azure Active Directory → App registrations</li>
                  <li>Click "New registration"</li>
                  <li>Enter application name: "Prowler SSO"</li>
                  <li>Select "Single tenant"</li>
                  <li>Set redirect URI: "https://{tenant?.subdomain}.localhost:3000/api/auth/callback/azure"</li>
                  <li>Click "Register"</li>
                </ol>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Step 2: Configure Authentication</h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
                  <li>Go to Authentication → Platform configurations</li>
                  <li>Add Web platform</li>
                  <li>Set redirect URI: "https://{tenant?.subdomain}.localhost:3000/api/auth/callback/azure"</li>
                  <li>Enable "ID tokens" and "Access tokens"</li>
                  <li>Save configuration</li>
                </ol>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Step 3: Create Client Secret</h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
                  <li>Go to Certificates & secrets</li>
                  <li>Click "New client secret"</li>
                  <li>Add description: "Prowler SSO Secret"</li>
                  <li>Set expiration (recommended: 24 months)</li>
                  <li>Click "Add" and copy the secret value</li>
                </ol>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Step 4: Configure SCIM (Optional)</h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
                  <li>Go to Enterprise applications → Your app → Provisioning</li>
                  <li>Set provisioning mode to "Automatic"</li>
                  <li>Set tenant URL: "{ssoConfig?.scim_url || 'SCIM URL will appear after SSO setup'}"</li>
                  <li>Set secret token: "{ssoConfig?.scim_bearer_token || 'SCIM Token will appear after SSO setup'}"</li>
                  <li>Test connection and save</li>
                </ol>
              </div>

              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
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
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>User Details</DialogTitle>
            <DialogDescription>
              View and manage user information
            </DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="space-y-4">
              {/* User Avatar and Basic Info */}
              <div className="flex items-start space-x-4 pb-4 border-b">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                  <Users className="h-8 w-8 text-blue-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {selectedUser.first_name} {selectedUser.last_name}
                  </h3>
                  <p className="text-sm text-gray-500">{selectedUser.email}</p>
                  {selectedUser.job_title && (
                    <p className="text-sm text-gray-600">{selectedUser.job_title}</p>
                  )}
                  <div className="flex items-center space-x-2 mt-2">
                    <Badge variant={selectedUser.role === 'admin' ? 'default' : 'secondary'}>
                      {selectedUser.role}
                    </Badge>
                    {selectedUser.is_sso_user && (
                      <Badge variant="outline" className="border-blue-500 text-blue-600">
                        SSO User
                      </Badge>
                    )}
                    {getStatusBadge(selectedUser.is_active ? 'active' : 'inactive')}
                  </div>
                </div>
              </div>

              {/* User Details Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-gray-500 uppercase">Department</Label>
                  <p className="text-sm font-medium text-gray-900 mt-1">
                    {selectedUser.department || 'Not specified'}
                  </p>
                </div>
                <div>
                  <Label className="text-xs text-gray-500 uppercase">Job Title</Label>
                  <p className="text-sm font-medium text-gray-900 mt-1">
                    {selectedUser.job_title || 'Not specified'}
                  </p>
                </div>
                <div>
                  <Label className="text-xs text-gray-500 uppercase">Invite Status</Label>
                  <div className="mt-1">
                    {getStatusBadge(selectedUser.invite_status)}
                  </div>
                </div>
                <div>
                  <Label className="text-xs text-gray-500 uppercase">User ID</Label>
                  <div className="flex items-center space-x-2 mt-1">
                    <p className="text-sm font-mono text-gray-600 truncate">{selectedUser.id}</p>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => copyToClipboard(selectedUser.id, 'User ID')}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Invite Information */}
              {selectedUser.invited_at && (
                <div className="pt-4 border-t">
                  <Label className="text-xs text-gray-500 uppercase">Invitation Details</Label>
                  <div className="mt-2 space-y-1">
                    <p className="text-sm text-gray-600">
                      Invited: {new Date(selectedUser.invited_at).toLocaleString()}
                    </p>
                    {selectedUser.accepted_invite_at && (
                      <p className="text-sm text-gray-600">
                        Accepted: {new Date(selectedUser.accepted_invite_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Permissions Management */}
              {selectedUser.permissions && (
                <div className="pt-4 border-t">
                  <Label className="text-xs text-gray-500 uppercase mb-3 block">Permissions</Label>
                  <div className="space-y-2">
                    {Object.entries(selectedUser.permissions).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between">
                        <Label className="text-sm font-normal text-gray-700 capitalize">
                          {key.replace(/_/g, ' ')}
                        </Label>
                        <Button
                          size="sm"
                          variant={value ? "default" : "outline"}
                          onClick={async () => {
                            if (selectedUser) {
                              const updatedPermissions = {
                                ...selectedUser.permissions,
                                [key]: !value
                              };
                              await handleUpdatePermissions(selectedUser.id, updatedPermissions);
                            }
                          }}
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
