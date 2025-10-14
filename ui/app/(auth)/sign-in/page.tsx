'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getTenantFromHostname } from '@/lib/tenant';
import { authenticate } from '@/actions/auth/auth';

export default function SignInPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [tenant, setTenant] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    // Extract tenant from URL
    const currentTenant = getTenantFromHostname(window.location.hostname);
    
    if (!currentTenant) {
      // No tenant in URL - redirect to main page or tenant selection
      router.push('/');
      return;
    }
    
    setTenant(currentTenant);
    
    // Check for error in URL params
    const errorParam = searchParams.get('error');
    if (errorParam === 'wrong_tenant') {
      setError('You do not have access to this organization');
    }
  }, [router, searchParams]);
  
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    
    if (!tenant) {
      setError('No organization detected. Please use your organization\'s subdomain.');
      setLoading(false);
      return;
    }
    
    const formData = new FormData(e.currentTarget);
    formData.append('tenant_subdomain', tenant);
    
    try {
      const result = await authenticate(formData);
      
      if (result?.error) {
        // ✅ Show tenant-specific error messages
        switch (result.error) {
          case 'wrong_tenant':
            setError(
              'You do not have access to this organization. ' +
              'Please use your organization\'s subdomain to sign in.'
            );
            break;
          case 'invalid_credentials':
            setError('Invalid email or password');
            break;
          case 'tenant_not_found':
            setError(`Organization "${tenant}" not found`);
            break;
          default:
            setError(result.message || 'Authentication failed');
        }
      } else {
        // Success - redirect to dashboard
        router.push('/dashboard');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };
  
  if (!tenant) {
    return <div>Loading...</div>;
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-3xl font-bold text-center">
            Sign in to {tenant}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Organization: <strong>{tenant}</strong>
          </p>
        </div>
        
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="you@example.com"
            />
          </div>
          
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
        
        <div className="text-center text-sm">
          <a href="/register" className="text-blue-600 hover:text-blue-500">
            Don't have an account? Register
          </a>
        </div>
      </div>
    </div>
  );
}