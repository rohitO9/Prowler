"use client";
import { AuthForm } from "@/components/auth/oss";
import {
  getAuthUrl,
  isGithubOAuthEnabled,
  isGoogleOAuthEnabled,
  isAzureOAuthEnabled,
} from "@/lib/helper";
import { useEffect, useState } from "react";
import { getSubdomain } from "@/src/utils/subdomain";
import { useSearchParams } from "next/navigation";
import { useToast } from "@/components/ui";

const SignIn = () => {
  const GOOGLE_AUTH_URL = getAuthUrl("google");
  const GITHUB_AUTH_URL = getAuthUrl("github");
  // Azure AD URL is fetched dynamically from database via getAzureADLoginUrl() in AzureADLogin component
  const searchParams = useSearchParams();
  const [tenantMismatchError, setTenantMismatchError] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    // Auto-detect organization from subdomain
    const subdomain = getSubdomain();
    if (subdomain && typeof window !== "undefined") {
      localStorage.setItem("company", subdomain);
    }
    
    // Check for SSO mode - auto-trigger Azure AD login for invited users
    const mode = searchParams?.get('mode');
    const inviteAccepted = searchParams?.get('invite_accepted');
    
    if (mode === 'sso') {
      // Auto-redirect to Azure AD SSO for invited users (using dynamic config from DB)
      if (inviteAccepted === 'true') {
        toast({
          title: "✅ Invitation Accepted",
          description: "Redirecting to Azure AD login...",
          variant: "default",
        });
      }
      // Get Azure AD login URL from database and redirect
      import("@/actions/auth/azure-ad").then(({ getAzureADLoginUrl }) => {
        getAzureADLoginUrl().then((azureUrl) => {
          if (azureUrl) {
            window.location.href = azureUrl;
          } else {
            toast({
              title: "⚠️ Azure AD Not Configured",
              description: "Azure AD SSO is not configured for this tenant. Please contact your administrator.",
              variant: "destructive",
            });
          }
        });
      });
      return;
    }
    
    // Check for various error scenarios and show appropriate toasts
    const error = searchParams?.get('error');
    const message = searchParams?.get('message');
    
    if (error === 'tenant_mismatch') {
      setTenantMismatchError(true);
      toast({
        title: "🚫 Access Denied",
        description: "You don't have access to this tenant. Please sign in to your correct tenant.",
        variant: "destructive",
      });
    } else if (error === 'user_not_found') {
      toast({
        title: "👤 User Not Found",
        description: "No account found with this email address. Please check your email or sign up.",
        variant: "destructive",
      });
    } else if (error === 'invalid_credentials') {
      toast({
        title: "🔒 Invalid Credentials",
        description: "Incorrect email or password. Please try again.",
        variant: "destructive",
      });
    } else if (error === 'account_locked') {
      toast({
        title: "🔐 Account Locked",
        description: "Your account has been locked due to multiple failed login attempts. Please contact support.",
        variant: "destructive",
      });
    } else if (error === 'cross_tenant_access') {
      toast({
        title: "🚫 Cross-Tenant Access Denied",
        description: "You don't have access to this organization. You've been redirected to your correct organization.",
        variant: "destructive",
      });
    } else if (message === 'registration_success') {
      toast({
        title: "✅ Registration Successful",
        description: "Your account has been created successfully. Please sign in to continue.",
        variant: "default",
      });
    } else if (message === 'logout_success') {
      toast({
        title: "👋 Logged Out",
        description: "You have been successfully logged out.",
        variant: "default",
      });
    } else if (message === 'session_expired') {
      toast({
        title: "⏰ Session Expired",
        description: "Your session has expired. Please sign in again to continue.",
        variant: "destructive",
      });
    } else if (message === 'invite_accepted') {
      toast({
        title: "✅ Invitation Accepted",
        description: "Please sign in with Azure AD SSO to access your account.",
        variant: "default",
      });
    } else if (error === 'sso_only_user') {
      toast({
        title: "🔐 SSO Login Required",
        description: "This account can only be accessed via Azure AD SSO. Please use the Azure AD login button.",
        variant: "destructive",
      });
    }
  }, [searchParams, toast]);

  return (
    <div>
      {tenantMismatchError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 mx-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Access Denied
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>You don't have access to this tenant. Please sign in to your correct tenant or contact your administrator.</p>
              </div>
            </div>
          </div>
        </div>
      )}
      <AuthForm
        type="sign-in"
        googleAuthUrl={GOOGLE_AUTH_URL}
        githubAuthUrl={GITHUB_AUTH_URL}
        isGoogleOAuthEnabled={isGoogleOAuthEnabled}
        isGithubOAuthEnabled={isGithubOAuthEnabled}
        // Azure AD URL is fetched dynamically from database, no hardcoded value
      />
    </div>
  );
};

export default SignIn;