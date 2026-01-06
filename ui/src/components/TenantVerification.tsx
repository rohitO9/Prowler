'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

const TenantVerification: React.FC = () => {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  const token = searchParams?.get('token');
  const email = searchParams?.get('email');

  useEffect(() => {
    if (token && email) {
      verifyTenant();
    } else {
      setError('Invalid verification link. Please check your email for the correct link.');
    }
  }, [token, email]);

  const verifyTenant = async () => {
    if (!token || !email) return;
    
    setIsVerifying(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8080/api/v1/tenant/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/vnd.api+json',
        },
        body: JSON.stringify({
          data: {
            type: 'tenants',
            attributes: {
              email: email,
              verification_token: token,
            },
          },
        }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setSuccess('Your account has been verified successfully! You can now log in to your tenant dashboard.');
      } else {
        setError(data.errors?.[0]?.detail || 'Failed to verify account');
      }
    } catch (err) {
      setError('Network error while verifying account');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleLogin = () => {
    // Extract subdomain from the current URL or redirect to login
    const hostname = window.location.hostname;
    if (hostname.includes('.vulneralq.anantacloud.com')) {
      const subdomain = hostname.split('.')[0];
      router.push(`/login?subdomain=${subdomain}`);
    } else {
      router.push('/login');
    }
  };

  if (isVerifying) {
    return (
      <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
        <div className="text-center">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100">
            <svg className="animate-spin h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <h2 className="mt-4 text-lg font-medium text-gray-900">Verifying Your Account</h2>
          <p className="mt-2 text-sm text-gray-600">Please wait while we verify your account...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
        <div className="text-center">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
            <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="mt-4 text-lg font-medium text-gray-900">Verification Failed</h2>
          <p className="mt-2 text-sm text-gray-600">{error}</p>
          <div className="mt-6">
            <button
              onClick={() => router.push('/')}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Return to Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
        <div className="text-center">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
            <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="mt-4 text-lg font-medium text-gray-900">Account Verified!</h2>
          <p className="mt-2 text-sm text-gray-600">{success}</p>
          <div className="mt-6 space-y-3">
            <button
              onClick={handleLogin}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Log In to Dashboard
            </button>
            <button
              onClick={() => router.push('/')}
              className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Return to Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default TenantVerification;
