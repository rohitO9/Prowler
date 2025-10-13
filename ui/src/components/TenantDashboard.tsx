'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { getSubdomain, isOnSubdomain } from '../utils/subdomain';
import ErrorBoundary from './ErrorBoundary';

interface TenantInfo {
  id: string;
  name: string;
  subdomain: string;
  contact_email: string;
  contact_phone?: string;
  address?: string;
  logo_url?: string;
  theme_color: string;
  secondary_color: string;
  is_active: boolean;
  is_verified: boolean;
  trial_ends_at?: string;
}

interface TenantDashboardProps {
  tenant?: TenantInfo;
}

const TenantDashboard: React.FC<TenantDashboardProps> = ({ tenant: propTenant }) => {
  console.log('🔍 [TenantDashboard] Component rendering with propTenant:', propTenant);
  const [tenant, setTenant] = useState<TenantInfo | null>(propTenant || null);
  const [loading, setLoading] = useState(!propTenant);
  const [error, setError] = useState<string | null>(null);
  const [hasFetched, setHasFetched] = useState(false);
  console.log('🔍 [TenantDashboard] State - tenant:', tenant, 'loading:', loading, 'error:', error);

  const fetchTenantInfo = useCallback(async () => {
    console.log('🔍 [TenantDashboard] fetchTenantInfo called');
    if (hasFetched) return; // Prevent multiple calls
    
    setLoading(true);
    setError(null);
    setHasFetched(true);
    
    try {
      // Try to get authentication headers first
      const { getAuthHeaders } = await import('@/lib/helper');
      let headers;
      let endpoint = '/api/v1/tenant/public-info'; // Default to public endpoint
      
      try {
        headers = await getAuthHeaders({ contentType: false });
        // If we have auth headers, use the authenticated endpoint
        endpoint = '/api/v1/tenant/info';
        console.log('🔍 [TenantDashboard] Using authenticated endpoint:', endpoint);
      } catch (authError) {
        // No authentication available, use public endpoint without headers
        headers = {
          'Accept': 'application/vnd.api+json'
        };
        console.log('🔍 [TenantDashboard] Using public endpoint:', endpoint);
      }
      
      console.log('🔍 [TenantDashboard] Fetching from:', endpoint, 'with headers:', headers);
      const response = await fetch(endpoint, {
        headers,
        cache: 'no-cache' // Prevent caching issues
      });
      
      console.log('🔍 [TenantDashboard] Response status:', response.status, 'ok:', response.ok);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('🔍 [TenantDashboard] API Response:', data);
      console.log('🔍 [TenantDashboard] data.data:', data.data);
      console.log('🔍 [TenantDashboard] data.data?.data:', data.data?.data);
      console.log('🔍 [TenantDashboard] data.data?.attributes:', data.data?.attributes);
      
      // Handle the nested data structure from the API
      const tenantData = data.data?.tenant || data.data?.data?.attributes || data.data?.attributes;
      console.log('🔍 [TenantDashboard] Parsed tenantData:', tenantData);
      
      if (tenantData) {
        console.log('🔍 [TenantDashboard] Setting tenant with:', tenantData);
        setTenant(tenantData);
      } else {
        console.error('❌ [TenantDashboard] Invalid tenant data structure');
        setError('Invalid tenant data structure');
      }
    } catch (err) {
      console.error('Error fetching tenant info:', err);
      setError(err instanceof Error ? err.message : 'Network error while loading tenant information');
    } finally {
      setLoading(false);
    }
  }, [hasFetched]);

  useEffect(() => {
    console.log('🔍 [TenantDashboard] useEffect running - propTenant:', propTenant, 'hasFetched:', hasFetched);
    if (!propTenant && !hasFetched) {
      console.log('🔍 [TenantDashboard] Calling fetchTenantInfo');
      fetchTenantInfo();
    }
  }, [propTenant, hasFetched, fetchTenantInfo]);

  const getTrialDaysRemaining = () => {
    if (!tenant?.trial_ends_at) return null;
    
    const trialEnd = new Date(tenant.trial_ends_at);
    const now = new Date();
    const diffTime = trialEnd.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    return diffDays > 0 ? diffDays : 0;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your organization...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-red-100 rounded-full">
              <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-red-800 mb-2">Unable to Load Organization</h3>
            <p className="text-sm text-red-700 mb-4">{error}</p>
            <button
              onClick={() => {
                setError(null);
                setHasFetched(false);
                setLoading(true);
                fetchTenantInfo();
              }}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium transition-colors duration-200"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900">No Tenant Found</h2>
          <p className="mt-2 text-gray-600">Unable to load tenant information.</p>
        </div>
      </div>
    );
  }

  const trialDaysRemaining = getTrialDaysRemaining();
  const currentSubdomain = getSubdomain();

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-white shadow-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center">
            {tenant.logo_url && (
              <div className="mb-8">
                <img
                  src={tenant.logo_url}
                  alt={`${tenant.name} logo`}
                  className="h-24 w-24 object-contain mx-auto rounded-lg shadow-lg"
                  onError={(e) => {
                    // Fallback to a default logo if external image fails to load
                    e.currentTarget.src = '/logo.svg';
                    e.currentTarget.onerror = null; // Prevent infinite loop
                  }}
                />
              </div>
            )}
            <h1 className="text-4xl font-bold text-gray-900 mb-4">{tenant.name}</h1>
            <p className="text-xl text-gray-600 mb-8">
              Welcome to your secure cloud infrastructure dashboard
            </p>
            <div className="flex justify-center space-x-4">
              <a 
                href="/sign-in"
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-lg font-medium shadow-lg transition-all duration-200 transform hover:scale-105 inline-block"
              >
                Sign In to Dashboard
              </a>
              <a 
                href="/sign-up"
                className="bg-white hover:bg-gray-50 text-indigo-600 border-2 border-indigo-600 px-8 py-3 rounded-lg font-medium shadow-lg transition-all duration-200 transform hover:scale-105 inline-block"
              >
                Create Account
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

      {/* Trial Banner */}
      {trialDaysRemaining !== null && trialDaysRemaining > 0 && (
        <div className="mb-6 bg-blue-50 border border-blue-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">Trial Period</h3>
              <div className="mt-2 text-sm text-blue-700">
                <p>
                  Your trial ends in {trialDaysRemaining} day{trialDaysRemaining !== 1 ? 's' : ''} on{' '}
                  {tenant.trial_ends_at && formatDate(tenant.trial_ends_at)}.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white overflow-hidden shadow-lg rounded-xl border border-gray-200 hover:shadow-xl transition-shadow duration-300">
            <div className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                    tenant.is_active ? 'bg-green-100' : 'bg-red-100'
                  }`}>
                    <div className={`w-6 h-6 rounded-full ${
                      tenant.is_active ? 'bg-green-500' : 'bg-red-500'
                    }`}></div>
                  </div>
                </div>
                <div className="ml-4 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Account Status</dt>
                    <dd className="text-lg font-semibold text-gray-900">
                      {tenant.is_active ? 'Active' : 'Inactive'}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow-lg rounded-xl border border-gray-200 hover:shadow-xl transition-shadow duration-300">
            <div className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                    tenant.is_verified ? 'bg-green-100' : 'bg-yellow-100'
                  }`}>
                    <svg className={`w-6 h-6 ${
                      tenant.is_verified ? 'text-green-500' : 'text-yellow-500'
                    }`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <div className="ml-4 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Verification</dt>
                    <dd className="text-lg font-semibold text-gray-900">
                      {tenant.is_verified ? 'Verified' : 'Pending'}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow-lg rounded-xl border border-gray-200 hover:shadow-xl transition-shadow duration-300">
            <div className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                    <svg className="w-6 h-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                    </svg>
                  </div>
                </div>
                <div className="ml-4 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Team Members</dt>
                    <dd className="text-lg font-semibold text-gray-900">0</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow-lg rounded-xl border border-gray-200 hover:shadow-xl transition-shadow duration-300">
            <div className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
                    <svg className="w-6 h-6 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                </div>
                <div className="ml-4 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Security Scans</dt>
                    <dd className="text-lg font-semibold text-gray-900">0</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-12">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-8">Platform Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="bg-white p-8 rounded-xl shadow-lg border border-gray-200 hover:shadow-xl transition-shadow duration-300">
              <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Security Scanning</h3>
              <p className="text-gray-600">Comprehensive security scans for your cloud infrastructure with detailed compliance reports.</p>
            </div>

            <div className="bg-white p-8 rounded-xl shadow-lg border border-gray-200 hover:shadow-xl transition-shadow duration-300">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Team Management</h3>
              <p className="text-gray-600">Invite team members, assign roles, and manage access to your security data.</p>
            </div>

            <div className="bg-white p-8 rounded-xl shadow-lg border border-gray-200 hover:shadow-xl transition-shadow duration-300">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Compliance Reports</h3>
              <p className="text-gray-600">Generate detailed compliance reports for various security frameworks.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Company Information */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Company Information</h3>
          <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-gray-500">Company Name</dt>
              <dd className="mt-1 text-sm text-gray-900">{tenant.name}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Subdomain</dt>
              <dd className="mt-1 text-sm text-gray-900">{tenant.subdomain}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Contact Email</dt>
              <dd className="mt-1 text-sm text-gray-900">{tenant.contact_email}</dd>
            </div>
            {tenant.contact_phone && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Contact Phone</dt>
                <dd className="mt-1 text-sm text-gray-900">{tenant.contact_phone}</dd>
              </div>
            )}
            {tenant.address && (
              <div className="sm:col-span-2">
                <dt className="text-sm font-medium text-gray-500">Address</dt>
                <dd className="mt-1 text-sm text-gray-900 whitespace-pre-line">{tenant.address}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      {/* Theme Preview */}
      <div className="mt-6 bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Theme Preview</h3>
          <div className="flex space-x-4">
            <div className="flex-1">
              <div className="text-sm font-medium text-gray-500 mb-2">Primary Color</div>
              <div 
                className="w-full h-12 rounded-md border"
                style={{ backgroundColor: tenant.theme_color }}
              ></div>
              <div className="mt-1 text-xs text-gray-500">{tenant.theme_color}</div>
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-gray-500 mb-2">Secondary Color</div>
              <div 
                className="w-full h-12 rounded-md border"
                style={{ backgroundColor: tenant.secondary_color }}
              ></div>
              <div className="mt-1 text-xs text-gray-500">{tenant.secondary_color}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </ErrorBoundary>
  );
};

export default TenantDashboard;
