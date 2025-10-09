'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card/card';
import { Alert, AlertDescription } from '@/components/ui/alert/alert';
import { Loader2, Shield, Building2, ExternalLink } from 'lucide-react';
import { useTenant } from '@/hooks/use-tenant';
import { initiateAzureLogin, handleAzureCallback, getAzureConfig } from '@/actions/auth/tenant-azure-auth';

interface TenantAzureLoginProps {
  onSuccess?: (user: any, tenant: any, membership: any) => void;
  onError?: (error: string) => void;
  className?: string;
}

const TenantAzureLogin: React.FC<TenantAzureLoginProps> = ({
  onSuccess,
  onError,
  className = ''
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isConfiguring, setIsConfiguring] = useState(false);
  const [azureConfig, setAzureConfig] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);

  const { tenant, membership, hasPermission } = useTenant();

  // Check if Azure AD is configured
  useEffect(() => {
    const checkAzureConfig = async () => {
      try {
        const config = await getAzureConfig();
        setAzureConfig(config);
      } catch (error) {
        console.log('Azure AD not configured for this tenant');
        setAzureConfig(null);
      }
    };

    checkAzureConfig();
  }, []);

  // Handle Azure AD login initiation
  const handleAzureLogin = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await initiateAzureLogin({});
      
      if (result.message === 'Redirecting to Azure AD') {
        // The redirect will happen automatically
        setIsInitializing(true);
      } else {
        setError(result.message || 'Failed to initiate Azure login');
        onError?.(result.message || 'Failed to initiate Azure login');
      }
    } catch (error) {
      console.error('Azure login error:', error);
      setError('An unexpected error occurred');
      onError?.('An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Azure AD callback (when redirected back)
  useEffect(() => {
    const handleCallback = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const state = urlParams.get('state');
      const error = urlParams.get('error');

      if (error) {
        setError(`Azure AD error: ${error}`);
        onError?.(`Azure AD error: ${error}`);
        return;
      }

      if (code) {
        setIsLoading(true);
        setError(null);

        try {
          const result = await handleAzureCallback({
            code,
            state: state || undefined
          });

          if (result.message === 'Authentication successful') {
            onSuccess?.(result.user, result.tenant, result.membership);
            // Clear URL parameters
            window.history.replaceState({}, document.title, window.location.pathname);
          } else {
            setError(result.message || 'Authentication failed');
            onError?.(result.message || 'Authentication failed');
          }
        } catch (error) {
          console.error('Azure callback error:', error);
          setError('Authentication failed');
          onError?.('Authentication failed');
        } finally {
          setIsLoading(false);
        }
      }
    };

    handleCallback();
  }, [onSuccess, onError]);

  // Show configuration button for admins
  const showConfigButton = hasPermission('can_manage_settings');

  if (isInitializing) {
    return (
      <div className={`flex flex-col items-center justify-center space-y-4 ${className}`}>
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <p className="text-gray-600">Redirecting to Azure AD...</p>
      </div>
    );
  }

  if (!azureConfig?.configured) {
    return (
      <Card className={className}>
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
            <Shield className="h-6 w-6 text-gray-600" />
          </div>
          <CardTitle className="text-2xl">Azure AD Not Configured</CardTitle>
          <CardDescription>
            Azure AD authentication is not set up for {tenant?.name || 'this organization'}.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {showConfigButton && (
            <Button
              onClick={() => setIsConfiguring(true)}
              className="w-full"
            >
              Configure Azure AD
            </Button>
          )}
          {!showConfigButton && (
            <p className="text-sm text-gray-500 text-center">
              Contact your administrator to set up Azure AD authentication.
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
          <Building2 className="h-6 w-6 text-blue-600" />
        </div>
        <CardTitle className="text-2xl">Sign in with Azure AD</CardTitle>
        <CardDescription>
          Use your organization's Azure AD account to sign in to {tenant?.name || 'this organization'}.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Button
          onClick={handleAzureLogin}
          disabled={isLoading}
          className="w-full"
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Connecting...
            </>
          ) : (
            <>
              <ExternalLink className="mr-2 h-4 w-4" />
              Sign in with Azure AD
            </>
          )}
        </Button>

        {showConfigButton && (
          <div className="text-center">
            <Button
              variant="outline"
              onClick={() => setIsConfiguring(true)}
              className="w-full"
            >
              Manage Azure AD Settings
            </Button>
          </div>
        )}

        <div className="text-center">
          <p className="text-xs text-gray-500">
            <Shield className="inline h-3 w-3 mr-1" />
            Your connection is secure and encrypted
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

export default TenantAzureLogin;
