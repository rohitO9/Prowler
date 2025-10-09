'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { signIn } from 'next-auth/react';
import { z } from 'zod';
import { Button } from '@/components/ui/button/button';
import { Input } from '@/components/ui/input/input';
import { Label } from '@/components/ui/label/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card/card';
import { Alert, AlertDescription } from '@/components/ui/alert/alert';
import { Loader2, Eye, EyeOff, Shield, Building2 } from 'lucide-react';
import { useTenant } from '@/hooks/use-tenant';
import { authenticate } from '@/actions/auth/auth';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormData = z.infer<typeof loginSchema>;

interface LoginPageProps {}

const LoginPage: React.FC<LoginPageProps> = () => {
  const [formData, setFormData] = useState<LoginFormData>({
    email: '',
    password: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tenant, setTenant] = useState<any>(null);
  const [isValidatingTenant, setIsValidatingTenant] = useState(true);

  const router = useRouter();
  const { data: session, status } = useSession();
  const { getCurrentTenant, validateTenantAccess } = useTenant();

  // Get current tenant from subdomain
  useEffect(() => {
    const loadTenant = async () => {
      try {
        const currentTenant = await getCurrentTenant();
        if (currentTenant) {
          setTenant(currentTenant);
          
          // If user is already authenticated, validate tenant access
          if (status === 'authenticated' && session?.user) {
            const isValid = await validateTenantAccess(currentTenant.subdomain);
            if (isValid) {
              router.push('/home');
              return;
            }
          }
        }
        setIsValidatingTenant(false);
      } catch (error) {
        console.error('Error loading tenant:', error);
        setError('Unable to load organization information');
        setIsValidatingTenant(false);
      }
    };

    loadTenant();
  }, [status, session, router, getCurrentTenant, validateTenantAccess]);

  // Redirect if already authenticated and has tenant access
  useEffect(() => {
    if (status === 'authenticated' && session?.user && tenant) {
      validateTenantAccess(tenant.subdomain).then((isValid) => {
        if (isValid) {
          router.push('/home');
        }
      });
    }
  }, [status, session, tenant, router, validateTenantAccess]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (error) setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // Validate form data
      const validatedData = loginSchema.parse(formData);
      
      // Attempt authentication with tenant context
      const result = await authenticate(validatedData);
      
      if (result.message === 'Success') {
        // Authentication successful, redirect to dashboard
        router.push('/home');
      } else {
        setError(result.message || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      if (error instanceof z.ZodError) {
        setError(error.errors[0].message);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading state while validating tenant
  if (isValidatingTenant) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-gray-600">Loading organization...</p>
        </div>
      </div>
    );
  }

  // Show error if no tenant found
  if (!tenant) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
              <Shield className="h-6 w-6 text-red-600" />
            </div>
            <CardTitle className="text-2xl">Organization Not Found</CardTitle>
            <CardDescription>
              The organization you're trying to access doesn't exist or is not active.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <AlertDescription>
                Please check the URL and try again, or contact your administrator.
              </AlertDescription>
            </Alert>
            <Button 
              onClick={() => window.location.href = '/'}
              className="w-full"
            >
              Go to Main Site
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        {/* Tenant Header */}
        <div className="text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-blue-100">
            {tenant.logo_url ? (
              <img 
                src={tenant.logo_url} 
                alt={tenant.name}
                className="h-12 w-12 rounded-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                  e.currentTarget.nextElementSibling?.classList.remove('hidden');
                }}
              />
            ) : null}
            <Building2 className={`h-8 w-8 text-blue-600 ${tenant.logo_url ? 'hidden' : ''}`} />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            Sign in to {tenant.name}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Enter your credentials to access your organization's dashboard
          </p>
        </div>

        {/* Login Form */}
        <Card>
          <CardHeader>
            <CardTitle>Sign In</CardTitle>
            <CardDescription>
              Enter your email and password to continue
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
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="Enter your email"
                  required
                  disabled={isLoading}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={handleInputChange}
                    placeholder="Enter your password"
                    required
                    disabled={isLoading}
                    className="w-full pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                    disabled={isLoading}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm text-gray-600">
                Don't have an account?{' '}
                <button
                  onClick={() => router.push('/sign-up')}
                  className="font-medium text-blue-600 hover:text-blue-500"
                  disabled={isLoading}
                >
                  Sign up here
                </button>
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Security Notice */}
        <div className="text-center">
          <p className="text-xs text-gray-500">
            <Shield className="inline h-3 w-3 mr-1" />
            Your connection is secure and encrypted
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
