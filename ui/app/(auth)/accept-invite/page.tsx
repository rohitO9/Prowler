'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { 
  Loader2, 
  Shield, 
  CheckCircle, 
  AlertCircle,
  ArrowRight,
  Users,
  Settings
} from 'lucide-react';
import { useToast } from '@/components/ui/toast/use-toast';

interface InviteData {
  user_id?: string;
  tenant_id: string;
  role?: string;
  tenant_name: string;
  tenant_subdomain?: string;
  user_email: string;
}

export default function AcceptInvitePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [isAccepting, setIsAccepting] = useState(false);
  const [inviteData, setInviteData] = useState<InviteData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    if (!searchParams) {
      setError('Invalid invitation link');
      setIsLoading(false);
      return;
    }
    
    const tokenParam = searchParams.get('token');
    if (tokenParam) {
      setToken(tokenParam);
      validateInviteToken(tokenParam);
    } else {
      setError('Invalid invitation link');
      setIsLoading(false);
    }
  }, [searchParams]);

  const validateInviteToken = async (inviteToken: string) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`/api/validate-invite?token=${inviteToken}`);
      
      // Try to parse response as JSON
      let data;
      try {
        const responseClone = response.clone(); // Clone to read text if needed
        try {
          data = await response.json();
        } catch (jsonError) {
          // If JSON parse fails, try to get text
          const text = await responseClone.text();
          console.error('Failed to parse as JSON:', jsonError);
          console.error('Response text:', text);
          throw new Error('Invalid response from server');
        }
      } catch (parseError) {
        console.error('Error parsing response:', parseError);
        throw parseError instanceof Error ? parseError : new Error('Failed to parse response');
      }
      
      if (!response.ok) {
        console.error('Error response:', data);
        throw new Error(data.error || data.message || 'Invalid invitation');
      }

      // Check if response is successful
      if (data.success === false || !data.success) {
        throw new Error(data.error || data.message || 'Invalid invitation');
      }

      // Map response data to InviteData interface
      setInviteData({
        tenant_id: data.tenant_id || data.invitation?.tenant?.id,
        tenant_name: data.tenant_name || data.invitation?.tenant?.name,
        tenant_subdomain: data.tenant_subdomain || data.invitation?.tenant?.subdomain,
        user_email: data.user_email || data.invitation?.email,
        role: data.invitation?.role || 'member'
      });
    } catch (err) {
      console.error('Error validating invite:', err);
      setError(err instanceof Error ? err.message : 'Failed to validate invitation');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAcceptInvite = async () => {
    if (!token) return;

    setIsAccepting(true);
    try {
      const response = await fetch('/api/accept-invite', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: token,
          user_data: {
            // Additional user data if needed
          }
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Failed to accept invitation' }));
        throw new Error(errorData.error || 'Failed to accept invitation');
      }
      
      const data = await response.json();

      // Priority: Redirect directly to Azure AD SSO login URL if available
      if (data.azure_login_url) {
        // Redirect directly to Azure AD OAuth login page (using tenant's SSO config from DB)
        console.log('Redirecting directly to Azure AD SSO login...');
        window.location.href = data.azure_login_url;
        return;
      }

      // Fallback: Redirect to tenant-specific sign-in page
      const tenantSubdomain = data.tenant?.subdomain || inviteData?.tenant_subdomain;
      
      if (!tenantSubdomain) {
        throw new Error('Tenant subdomain not found');
      }

      const protocol = window.location.protocol;
      const hostname = window.location.hostname;
      const port = window.location.port ? `:${window.location.port}` : '';

      const { isDevHost, DEV_DOMAIN } = await import('@/lib/env');
      if (isDevHost(hostname)) {
        const baseHost = hostname.replace(/^[^.]+\./, '') || DEV_DOMAIN;
        const ssoUrl = data.sso_redirect_url || `${protocol}//${tenantSubdomain}.${baseHost}${port}/sign-in?mode=sso&invite_accepted=true`;
        window.location.href = ssoUrl;
      } else {
        // Production: use subdomain format
        const baseHost = hostname.split('.').slice(1).join('.');
        const ssoUrl = data.sso_redirect_url || `${protocol}//${tenantSubdomain}.${baseHost}${port}/sign-in?mode=sso&invite_accepted=true`;
        window.location.href = ssoUrl;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to accept invitation');
    } finally {
      setIsAccepting(false);
    }
  };

  const getRoleDescription = (role: string) => {
    switch (role) {
      case 'owner':
        return 'Full access to all features and settings';
      case 'admin':
        return 'Manage users, run scans, configure integrations';
      case 'auditor':
        return 'Run scans, view reports, export data';
      case 'viewer':
        return 'View reports and data only (read-only)';
      default:
        return 'Standard user access';
    }
  };

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case 'owner':
        return 'default';
      case 'admin':
        return 'secondary';
      case 'auditor':
        return 'outline';
      case 'viewer':
        return 'outline';
      default:
        return 'outline';
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Validating invitation...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <CardTitle className="text-red-600">Invalid Invitation</CardTitle>
            <CardDescription>
              This invitation link is invalid or has expired.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-4">
                Please contact your administrator for a new invitation.
              </p>
              <Button
                variant="outline"
                onClick={() => router.push('/')}
              >
                Return to Home
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-blue-600" />
              <span className="ml-2 text-2xl font-bold text-gray-900">Prowler SaaS</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <Card className="w-full">
          <CardHeader className="text-center">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <CardTitle className="text-2xl">You're Invited!</CardTitle>
            <CardDescription className="text-lg">
              Welcome to {inviteData?.tenant_name}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="text-center space-y-2">
              <p className="text-gray-600">
                You've been invited to join <strong>{inviteData?.tenant_name}</strong> as a team member.
              </p>
              <p className="text-sm text-gray-500">
                Email: {inviteData?.user_email}
              </p>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Your Role:</span>
                <Badge variant={getRoleBadgeVariant(inviteData?.role || '')}>
                  {(() => {
                    const role = inviteData?.role || 'member';
                    return role.charAt(0).toUpperCase() + role.slice(1);
                  })()}
                </Badge>
              </div>
              <p className="text-sm text-gray-600">
                {getRoleDescription(inviteData?.role || '')}
              </p>
            </div>

            <div className="space-y-4">
              <h4 className="font-medium">What happens next?</h4>
              <div className="space-y-3">
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-xs font-medium text-blue-600">1</span>
                  </div>
                  <div>
                    <p className="text-sm font-medium">Accept Invitation</p>
                    <p className="text-xs text-gray-500">Click the button below to accept this invitation</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-xs font-medium text-blue-600">2</span>
                  </div>
                  <div>
                    <p className="text-sm font-medium">Azure AD Login</p>
                    <p className="text-xs text-gray-500">You'll be redirected to sign in with your organization's Azure AD</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-xs font-medium text-blue-600">3</span>
                  </div>
                  <div>
                    <p className="text-sm font-medium">Access Dashboard</p>
                    <p className="text-xs text-gray-500">Once signed in, you'll have access to your dashboard</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <Button
                onClick={handleAcceptInvite}
                disabled={isAccepting}
                className="w-full"
                size="lg"
              >
                {isAccepting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Accepting Invitation...
                  </>
                ) : (
                  <>
                    Accept Invitation
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
              
              <div className="text-center">
                <p className="text-xs text-gray-500">
                  By accepting this invitation, you agree to join {inviteData?.tenant_name} and 
                  will be able to access the platform using your organization's Azure AD credentials.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Features Preview */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center p-4 bg-white rounded-lg shadow-sm">
            <Users className="h-8 w-8 text-blue-600 mx-auto mb-2" />
            <h3 className="font-medium text-gray-900">Team Collaboration</h3>
            <p className="text-sm text-gray-500">Work with your team on security compliance</p>
          </div>
          <div className="text-center p-4 bg-white rounded-lg shadow-sm">
            <Shield className="h-8 w-8 text-blue-600 mx-auto mb-2" />
            <h3 className="font-medium text-gray-900">Security Scanning</h3>
            <p className="text-sm text-gray-500">Automated cloud security assessments</p>
          </div>
          <div className="text-center p-4 bg-white rounded-lg shadow-sm">
            <Settings className="h-8 w-8 text-blue-600 mx-auto mb-2" />
            <h3 className="font-medium text-gray-900">Compliance Reports</h3>
            <p className="text-sm text-gray-500">Generate detailed compliance reports</p>
          </div>
        </div>
      </div>
    </div>
  );
}
