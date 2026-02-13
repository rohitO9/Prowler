'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
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
  Mail
} from 'lucide-react';
import { useToast } from '@/components/ui/toast/use-toast';
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
}

export default function AdminDashboard() {
  const router = useRouter();
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

  useEffect(() => {
    loadTenantData();
  }, []);

  const loadTenantData = async () => {
    try {
      setIsLoading(true);
      
      // Load tenant info
      const tenantResponse = await fetch('/api/v1/tenant/public-info');
      if (tenantResponse.ok) {
        const tenantData = await tenantResponse.json();
        setTenant(tenantData);
      }

      // Load SSO config
      const ssoResponse = await fetch('/api/v1/tenant/sso-config');
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
      }

      // Load users
      await loadUsers();
    } catch (err) {
      setError('Failed to load tenant data');
    } finally {
      setIsLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await fetch('/api/v1/tenant/users');
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users || []);
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
      const response = await fetch('/api/v1/tenant/setup-azure-sso', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(ssoFormData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'SSO setup failed');
      }

      setSSOConfig(data);
      toast({
        title: 'SSO Configured Successfully',
        description: 'Azure AD SSO has been set up for your organization.',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'SSO setup failed');
    } finally {
      setIsSSOLoading(false);
    }
  };

  const handleSyncUsers = async () => {
    setIsSyncLoading(true);
    try {
      const response = await fetch('/api/v1/tenant/sync-users', {
        method: 'POST',
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Sync failed');
      }

      await loadUsers();
      toast({
        title: 'Users Synced',
        description: `Successfully synced ${data.stats?.total || 0} users from Azure AD.`,
      });
    } catch (err) {
      toast({
        title: 'Sync Failed',
        description: err instanceof Error ? err.message : 'Failed to sync users',
        variant: 'destructive',
      });
    } finally {
      setIsSyncLoading(false);
    }
  };

  const handleInviteUser = async (userId: string) => {
    try {
      const response = await fetch(`/api/v1/tenant/users/${userId}/send-invite`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to send invite');
      }

      toast({
        title: 'Invitation Sent',
        description: 'User invitation has been sent successfully.',
      });
    } catch (err) {
      toast({
        title: 'Failed to Send Invite',
        description: err instanceof Error ? err.message : 'Failed to send invitation',
        variant: 'destructive',
      });
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: 'Copied to Clipboard',
      description: `${label} has been copied to your clipboard.`,
    });
  };

  const getStatusBadge = (user: User) => {
    if (!user.is_active) {
      return <Badge variant="destructive">Inactive</Badge>;
    }
    if (user.invite_status === 'accepted') {
      return <Badge variant="default">Active</Badge>;
    }
    if (user.invite_status === 'pending') {
      return <Badge variant="secondary">Pending Invite</Badge>;
    }
    return <Badge variant="outline">Not Invited</Badge>;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-blue-600" />
              <div className="ml-3">
                <h1 className="text-2xl font-bold text-gray-900">{tenant?.name}</h1>
                <p className="text-sm text-gray-500">{tenant?.subdomain}.{DEV_APP_HOST_DISPLAY}</p>
              </div>
            </div>
            <Button
              variant="outline"
              onClick={() => router.push('/api/auth/logout')}
            >
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="sso">SSO Setup</TabsTrigger>
            <TabsTrigger value="users">User Management</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Users</CardTitle>
                  <Users className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{users.length}</div>
                  <p className="text-xs text-muted-foreground">
                    {users.filter(u => u.is_active).length} active
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">SSO Status</CardTitle>
                  <Shield className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {ssoConfig?.is_active ? 'Active' : 'Not Configured'}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Azure AD integration
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Pending Invites</CardTitle>
                  <Mail className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {users.filter(u => u.invite_status === 'pending').length}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Awaiting acceptance
                  </p>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>
                  Manage your organization's security and users
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex space-x-4">
                  <Button
                    onClick={handleSyncUsers}
                    disabled={!ssoConfig?.is_active || isSyncLoading}
                  >
                    {isSyncLoading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="mr-2 h-4 w-4" />
                    )}
                    Sync Users from Azure AD
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => router.push('/dashboard/users')}
                  >
                    <UserPlus className="mr-2 h-4 w-4" />
                    Manage Users
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* SSO Setup Tab */}
          <TabsContent value="sso" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Azure AD SSO Configuration</CardTitle>
                <CardDescription>
                  Configure Azure Active Directory for single sign-on and user provisioning
                </CardDescription>
              </CardHeader>
              <CardContent>
                {ssoConfig?.is_active ? (
                  <div className="space-y-6">
                    <Alert>
                      <CheckCircle className="h-4 w-4" />
                      <AlertDescription>
                        Azure AD SSO is configured and active.
                      </AlertDescription>
                    </Alert>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-4">
                        <div>
                          <Label>SCIM Endpoint URL</Label>
                          <div className="flex items-center space-x-2">
                            <Input
                              value={ssoConfig.scim_url}
                              readOnly
                              className="bg-gray-50"
                            />
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => copyToClipboard(ssoConfig.scim_url, 'SCIM URL')}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>

                        <div>
                          <Label>SCIM Bearer Token</Label>
                          <div className="flex items-center space-x-2">
                            <Input
                              value={ssoConfig.scim_bearer_token}
                              readOnly
                              className="bg-gray-50"
                            />
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => copyToClipboard(ssoConfig.scim_bearer_token, 'Bearer Token')}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <h4 className="font-medium">Azure AD Configuration Steps:</h4>
                        <ol className="text-sm text-gray-600 space-y-2">
                          <li>1. Go to Azure AD Enterprise Applications</li>
                          <li>2. Create a new Enterprise Application</li>
                          <li>3. Configure SCIM provisioning</li>
                          <li>4. Use the SCIM URL and Bearer Token above</li>
                          <li>5. Test connection and start provisioning</li>
                        </ol>
                      </div>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleSSOSetup} className="space-y-4">
                    {error && (
                      <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{error}</AlertDescription>
                      </Alert>
                    )}

                    <div className="space-y-2">
                      <Label htmlFor="azure_tenant_id">Azure Tenant ID</Label>
                      <Input
                        id="azure_tenant_id"
                        name="azure_tenant_id"
                        type="text"
                        value={ssoFormData.azure_tenant_id}
                        onChange={(e) => setSSOFormData(prev => ({
                          ...prev,
                          azure_tenant_id: e.target.value
                        }))}
                        placeholder="12345678-1234-1234-1234-123456789012"
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="client_id">Client ID (Application ID)</Label>
                      <Input
                        id="client_id"
                        name="client_id"
                        type="text"
                        value={ssoFormData.client_id}
                        onChange={(e) => setSSOFormData(prev => ({
                          ...prev,
                          client_id: e.target.value
                        }))}
                        placeholder="12345678-1234-1234-1234-123456789012"
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="client_secret">Client Secret</Label>
                      <Input
                        id="client_secret"
                        name="client_secret"
                        type="password"
                        value={ssoFormData.client_secret}
                        onChange={(e) => setSSOFormData(prev => ({
                          ...prev,
                          client_secret: e.target.value
                        }))}
                        placeholder="••••••••••••••••••••••••••••••••"
                        required
                      />
                    </div>

                    <Button
                      type="submit"
                      className="w-full"
                      disabled={isSSOLoading}
                    >
                      {isSSOLoading ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Configuring SSO...
                        </>
                      ) : (
                        'Configure Azure AD SSO'
                      )}
                    </Button>
                  </form>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* User Management Tab */}
          <TabsContent value="users" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>User Management</CardTitle>
                <CardDescription>
                  Manage users synced from Azure AD and send invitations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {users.length === 0 ? (
                    <div className="text-center py-8">
                      <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No Users Found</h3>
                      <p className="text-gray-500 mb-4">
                        Configure Azure AD SSO and sync users to get started.
                      </p>
                      <Button
                        onClick={handleSyncUsers}
                        disabled={!ssoConfig?.is_active}
                      >
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Sync Users from Azure AD
                      </Button>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-3 px-4">Name</th>
                            <th className="text-left py-3 px-4">Email</th>
                            <th className="text-left py-3 px-4">Department</th>
                            <th className="text-left py-3 px-4">Role</th>
                            <th className="text-left py-3 px-4">Status</th>
                            <th className="text-left py-3 px-4">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {users.map((user) => (
                            <tr key={user.id} className="border-b">
                              <td className="py-3 px-4">
                                {user.first_name} {user.last_name}
                              </td>
                              <td className="py-3 px-4">{user.email}</td>
                              <td className="py-3 px-4">{user.department || '-'}</td>
                              <td className="py-3 px-4">
                                <Badge variant="outline">{user.role}</Badge>
                              </td>
                              <td className="py-3 px-4">
                                {getStatusBadge(user)}
                              </td>
                              <td className="py-3 px-4">
                                {user.invite_status === 'not_invited' && (
                                  <Button
                                    size="sm"
                                    onClick={() => handleInviteUser(user.id)}
                                  >
                                    <Mail className="mr-1 h-3 w-3" />
                                    Invite
                                  </Button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
