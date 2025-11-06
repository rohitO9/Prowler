'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function AzureCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    handleAzureCallback();
  }, []);

  const handleAzureCallback = async () => {
    try {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      if (error) {
        throw new Error(errorDescription || error);
      }

      if (!code) {
        throw new Error('No authorization code received');
      }

      // Exchange code for tokens
      const response = await fetch('/api/v1/tenant/azure/callback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code,
          state,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Authentication failed');
      }

      // Store tokens and user info
      if (data.access_token) {
        localStorage.setItem('azure_access_token', data.access_token);
      }
      if (data.refresh_token) {
        localStorage.setItem('azure_refresh_token', data.refresh_token);
      }
      if (data.user) {
        localStorage.setItem('azure_user', JSON.stringify(data.user));
      }

      setStatus('success');
      
      // Redirect to dashboard after a short delay
      setTimeout(() => {
        router.push('/dashboard');
      }, 2000);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
      setStatus('error');
    }
  };

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Completing Azure AD authentication...</p>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="w-full max-w-md">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error || 'Authentication failed. Please try again.'}
            </AlertDescription>
          </Alert>
          <div className="mt-4 text-center">
            <button
              onClick={() => router.push('/sign-in')}
              className="text-blue-600 hover:text-blue-800"
            >
              Return to Sign In
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <div className="text-center">
        <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Authentication Successful!</h2>
        <p className="text-gray-600 mb-4">Redirecting to your dashboard...</p>
        <Loader2 className="h-6 w-6 animate-spin mx-auto" />
      </div>
    </div>
  );
}
