'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Shield, Users, Zap, CheckCircle, LogIn } from 'lucide-react';

interface TenantRegistrationData {
  companyName: string;
  subdomain: string;
  adminEmail: string;
  adminFirstName: string;
  adminLastName: string;
  adminPassword: string;
  confirmPassword: string;
}

interface LoginData {
  email: string;
  password: string;
}

export default function LandingPage() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isTenantSubdomain, setIsTenantSubdomain] = useState(false);
  const [tenantName, setTenantName] = useState<string>('');
  const [formData, setFormData] = useState<TenantRegistrationData>({
    companyName: '',
    subdomain: '',
    adminEmail: '',
    adminFirstName: '',
    adminLastName: '',
    adminPassword: '',
    confirmPassword: ''
  });
  const [loginData, setLoginData] = useState<LoginData>({
    email: '',
    password: ''
  });

  // Detect if we're on a tenant subdomain
  useEffect(() => {
    const hostname = window.location.hostname;
    if (hostname.includes('.vulneralq.anantacloud.com') && hostname !== 'vulneralq.anantacloud.com') {
      // Extract subdomain from company2.localhost
      const subdomain = hostname.split('.')[0];
      setIsTenantSubdomain(true);
      setTenantName(subdomain);
      
      // Only redirect to sign-in if user is not authenticated
      if (status === 'unauthenticated') {
        window.location.href = '/sign-in';
      } else if (status === 'authenticated') {
        // If authenticated, redirect to overview or dashboard
        window.location.href = '/overview';
      }
      // If status is 'loading', wait for authentication check to complete
    }
  }, [status]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    
    if (isTenantSubdomain) {
      // Handle login form
      setLoginData(prev => ({
        ...prev,
        [name]: value
      }));
    } else {
      // Handle registration form
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
      
      // Auto-generate subdomain from company name
      if (name === 'companyName' && !formData.subdomain) {
        const subdomain = value
          .toLowerCase()
          .replace(/[^a-z0-9]/g, '')
          .substring(0, 20);
        setFormData(prev => ({
          ...prev,
          subdomain
        }));
      }
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!loginData.email.trim() || !loginData.password.trim()) {
      setError('Email and password are required');
      return;
    }

    setIsLoading(true);

    try {
      // Redirect to existing sign-in page with credentials
      const params = new URLSearchParams({
        email: loginData.email,
        password: loginData.password,
        company: tenantName
      });
      
      window.location.href = `/sign-in?${params.toString()}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  const validateForm = () => {
    if (!formData.companyName.trim()) {
      setError('Company name is required');
      return false;
    }
    if (!formData.subdomain.trim()) {
      setError('Subdomain is required');
      return false;
    }
    if (!/^[a-z0-9-]+$/.test(formData.subdomain)) {
      setError('Subdomain can only contain lowercase letters, numbers, and hyphens');
      return false;
    }
    if (!formData.adminEmail.trim()) {
      setError('Admin email is required');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.adminEmail)) {
      setError('Please enter a valid email address');
      return false;
    }
    if (!formData.adminFirstName.trim()) {
      setError('Admin first name is required');
      return false;
    }
    if (!formData.adminLastName.trim()) {
      setError('Admin last name is required');
      return false;
    }
    if (formData.adminPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      return false;
    }
    if (formData.adminPassword !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('/api/v1/tenant/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company_name: formData.companyName,
          subdomain: formData.subdomain,
          admin_email: formData.adminEmail,
          admin_first_name: formData.adminFirstName,
          admin_last_name: formData.adminLastName,
          admin_password: formData.adminPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Registration failed');
      }

      // Redirect to the new tenant's dashboard
      window.location.href = `https://${formData.subdomain}.vulneralq.anantacloud.com/dashboard`;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading for tenant subdomains (will redirect to sign-in)
  if (isTenantSubdomain) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-gray-600">Redirecting to sign-in...</p>
        </div>
      </div>
    );
  }

  // Show registration form for main domain
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-blue-600" />
              <span className="ml-2 text-2xl font-bold text-gray-900">SecureStack</span>
            </div>
            <div className="text-sm text-gray-500">
              Enterprise Cloud Security Platform
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Secure Your Cloud Infrastructure
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Enterprise-grade security compliance platform with Azure AD integration, 
            automated user provisioning, and comprehensive audit logging
          </p>
          <div className="flex justify-center space-x-8 text-sm text-gray-500">
            <div className="flex items-center">
              <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
              SOC 2 Compliant
            </div>
            <div className="flex items-center">
              <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
              Azure AD Ready
            </div>
            <div className="flex items-center">
              <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
              Multi-Tenant
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-12 items-start">
          {/* Features */}
          <div className="space-y-8">
            <div className="bg-white rounded-lg p-6 shadow-sm border">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <Shield className="h-8 w-8 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Multi-Tenant Security</h3>
                  <p className="text-gray-600">Complete tenant isolation with Azure AD SSO integration and role-based access control</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg p-6 shadow-sm border">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <Users className="h-8 w-8 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Automated User Management</h3>
                  <p className="text-gray-600">Seamless user provisioning and deprovisioning via SCIM 2.0 with Azure AD</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg p-6 shadow-sm border">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <Zap className="h-8 w-8 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Compliance Automation</h3>
                  <p className="text-gray-600">Automated security scanning, compliance reporting, and audit logging</p>
                </div>
              </div>
            </div>
          </div>

          {/* Registration Form */}
          <Card className="w-full max-w-md mx-auto shadow-lg">
            <CardHeader className="text-center">
              <CardTitle className="text-2xl">Create Your Organization</CardTitle>
              <CardDescription className="text-base">
                Set up your secure cloud compliance platform
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                <div className="space-y-2">
                  <Label htmlFor="companyName">Company Name</Label>
                  <Input
                    id="companyName"
                    name="companyName"
                    type="text"
                    value={formData.companyName}
                    onChange={handleInputChange}
                    placeholder="Acme Corporation"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="subdomain">Subdomain</Label>
                  <div className="flex items-center space-x-2">
                    <Input
                      id="subdomain"
                      name="subdomain"
                      type="text"
                      value={formData.subdomain}
                      onChange={handleInputChange}
                      placeholder="acme"
                      required
                      className="flex-1"
                    />
                    <span className="text-sm text-gray-500">.vulneralq.anantacloud.com</span>
                  </div>
                  <p className="text-xs text-gray-500">
                    Your dashboard will be at: {formData.subdomain || 'subdomain'}.vulneralq.anantacloud.com
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="adminFirstName">First Name</Label>
                    <Input
                      id="adminFirstName"
                      name="adminFirstName"
                      type="text"
                      value={formData.adminFirstName}
                      onChange={handleInputChange}
                      placeholder="John"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="adminLastName">Last Name</Label>
                    <Input
                      id="adminLastName"
                      name="adminLastName"
                      type="text"
                      value={formData.adminLastName}
                      onChange={handleInputChange}
                      placeholder="Doe"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="adminEmail">Admin Email</Label>
                  <Input
                    id="adminEmail"
                    name="adminEmail"
                    type="email"
                    value={formData.adminEmail}
                    onChange={handleInputChange}
                    placeholder="admin@acme.com"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="adminPassword">Password</Label>
                  <Input
                    id="adminPassword"
                    name="adminPassword"
                    type="password"
                    value={formData.adminPassword}
                    onChange={handleInputChange}
                    placeholder="••••••••"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm Password</Label>
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                    placeholder="••••••••"
                    required
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating Organization...
                    </>
                  ) : (
                    'Create Organization'
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white border-t">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-500">
            <p>&copy; 2024 SecureStack. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}