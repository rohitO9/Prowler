'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { isOnSubdomain, getSubdomain } from '../utils/subdomain';
import TenantRegistration from './TenantRegistration';
import TenantDashboard from './TenantDashboard';

const LandingPage: React.FC = () => {
  console.log('🔍 [LandingPage] Component rendering');
  const [showRegistration, setShowRegistration] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const router = useRouter();
  const { data: session, status } = useSession();
  console.log('🔍 [LandingPage] Session status:', status);

  // Ensure we're on the client side to avoid hydration issues
  useEffect(() => {
    console.log('🔍 [LandingPage] useEffect running, setting isClient to true');
    setIsClient(true);
  }, []);

  // Prevent hydration mismatches by ensuring consistent rendering
  if (typeof window === 'undefined') {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  // Handle redirect for authenticated users on subdomains
  useEffect(() => {
    if (isClient && isOnSubdomain() && status === 'authenticated' && session?.user) {
      router.push('/home');
    }
  }, [isClient, status, session, router]);

  // Show loading while checking authentication or during client-side hydration
  if (!isClient || status === 'loading') {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  // If we're on a subdomain, handle authentication and routing
  if (isOnSubdomain()) {
    // If user is authenticated, show redirecting message (redirect handled by useEffect)
    if (status === 'authenticated' && session?.user) {
      return <div className="min-h-screen flex items-center justify-center">Redirecting to dashboard...</div>;
    }
    
    // If not authenticated, show tenant dashboard (public view)
    return (
      <div>
        <TenantDashboard />
      </div>
    );
  }

  // Main landing page for non-subdomain access
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">Prowler</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowLogin(true)}
                className="text-gray-500 hover:text-gray-700 px-3 py-2 rounded-md text-sm font-medium"
              >
                Log In
              </button>
              <button
                onClick={() => setShowRegistration(true)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                Get Started
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center">
          <h1 className="text-4xl font-extrabold text-gray-900 sm:text-5xl md:text-6xl">
            <span className="block">Multi-Tenant Security</span>
            <span className="block text-indigo-600">for Every Company</span>
          </h1>
          <p className="mt-3 max-w-md mx-auto text-base text-gray-500 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
            Secure your cloud infrastructure with Prowler's comprehensive security scanning. 
            Each company gets their own secure environment with custom branding and settings.
          </p>
          <div className="mt-5 max-w-md mx-auto sm:flex sm:justify-center md:mt-8">
            <div className="rounded-md shadow">
              <button
                onClick={() => setShowRegistration(true)}
                className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 md:py-4 md:text-lg md:px-10"
              >
                Create Your Company Account
              </button>
            </div>
            <div className="mt-3 rounded-md shadow sm:mt-0 sm:ml-3">
              <button
                onClick={() => setShowLogin(true)}
                className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-indigo-600 bg-white hover:bg-gray-50 md:py-4 md:text-lg md:px-10"
              >
                Log In
              </button>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="mt-20">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <div className="pt-6">
              <div className="flow-root bg-white rounded-lg px-6 pb-8">
                <div className="-mt-6">
                  <div>
                    <span className="inline-flex items-center justify-center p-3 bg-indigo-500 rounded-md shadow-lg">
                      <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                      </svg>
                    </span>
                  </div>
                  <h3 className="mt-8 text-lg font-medium text-gray-900 tracking-tight">Secure by Default</h3>
                  <p className="mt-5 text-base text-gray-500">
                    Each company gets their own isolated environment with enterprise-grade security.
                  </p>
                </div>
              </div>
            </div>

            <div className="pt-6">
              <div className="flow-root bg-white rounded-lg px-6 pb-8">
                <div className="-mt-6">
                  <div>
                    <span className="inline-flex items-center justify-center p-3 bg-indigo-500 rounded-md shadow-lg">
                      <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zM21 5a2 2 0 00-2-2h-4a2 2 0 00-2 2v12a4 4 0 004 4h4a2 2 0 002-2V5z" />
                      </svg>
                    </span>
                  </div>
                  <h3 className="mt-8 text-lg font-medium text-gray-900 tracking-tight">Custom Branding</h3>
                  <p className="mt-5 text-base text-gray-500">
                    Customize your company's look with logos, colors, and themes that match your brand.
                  </p>
                </div>
              </div>
            </div>

            <div className="pt-6">
              <div className="flow-root bg-white rounded-lg px-6 pb-8">
                <div className="-mt-6">
                  <div>
                    <span className="inline-flex items-center justify-center p-3 bg-indigo-500 rounded-md shadow-lg">
                      <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                      </svg>
                    </span>
                  </div>
                  <h3 className="mt-8 text-lg font-medium text-gray-900 tracking-tight">Team Management</h3>
                  <p className="mt-5 text-base text-gray-500">
                    Invite team members, manage roles, and control access to your security data.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* How it works */}
        <div className="mt-20">
          <div className="text-center">
            <h2 className="text-3xl font-extrabold text-gray-900">How It Works</h2>
            <p className="mt-4 text-lg text-gray-500">
              Get your company set up in minutes with our simple registration process
            </p>
          </div>
          <div className="mt-12">
            <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
              <div className="text-center">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white text-xl font-bold mx-auto">
                  1
                </div>
                <h3 className="mt-6 text-lg font-medium text-gray-900">Register Your Company</h3>
                <p className="mt-2 text-base text-gray-500">
                  Provide your company details and choose a unique subdomain for your organization.
                </p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white text-xl font-bold mx-auto">
                  2
                </div>
                <h3 className="mt-6 text-lg font-medium text-gray-900">Verify Your Email</h3>
                <p className="mt-2 text-base text-gray-500">
                  Check your email for verification instructions and temporary login credentials.
                </p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white text-xl font-bold mx-auto">
                  3
                </div>
                <h3 className="mt-6 text-lg font-medium text-gray-900">Access Your Dashboard</h3>
                <p className="mt-2 text-base text-gray-500">
                  Log in to your company's dashboard and start securing your infrastructure.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Registration Modal */}
      {showRegistration && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex justify-end">
                <button
                  onClick={() => setShowRegistration(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <TenantRegistration 
                onRegistrationComplete={(subdomain) => {
                  setShowRegistration(false);
                  // Redirect to the subdomain
                  window.location.href = `https://${subdomain}.vulneralq.anantacloud.com`;
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex justify-end">
                <button
                  onClick={() => setShowLogin(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="text-center">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Log In</h3>
                <p className="text-sm text-gray-500 mb-4">
                  Access your company dashboard by visiting your subdomain URL:
                </p>
                <div className="bg-gray-50 p-3 rounded-md">
                  <code className="text-sm">yourcompany.vulneralq.anantacloud.com</code>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Don't have a company account? <button 
                    onClick={() => {
                      setShowLogin(false);
                      setShowRegistration(true);
                    }}
                    className="text-indigo-600 hover:text-indigo-500"
                  >
                    Create one here
                  </button>
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LandingPage;
