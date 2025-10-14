"use client";
import { AuthForm } from "@/components/auth/oss";
import { getAuthUrl, isGithubOAuthEnabled, isGoogleOAuthEnabled } from "@/lib/helper";
import { SearchParamsProps } from "@/types";
import { useEffect } from "react";
import { getSubdomain } from "@/src/utils/subdomain";
import { useToast } from "@/components/ui";
import { useSearchParams } from "next/navigation";

const SignUp = ({ searchParams }: { searchParams: SearchParamsProps }) => {
  const invitationToken =
    typeof searchParams?.invitation_token === "string"
      ? searchParams.invitation_token
      : null;

  const GOOGLE_AUTH_URL = getAuthUrl("google");
  const GITHUB_AUTH_URL = getAuthUrl("github");
  const { toast } = useToast();
  const urlSearchParams = useSearchParams();

  useEffect(() => {
    // Auto-detect organization from subdomain
    const subdomain = getSubdomain();
    if (subdomain && typeof window !== "undefined") {
      localStorage.setItem("company", subdomain);
    }
    
    // Check for various sign-up scenarios and show appropriate toasts
    const error = urlSearchParams?.get('error');
    const message = urlSearchParams?.get('message');
    
    if (error === 'email_already_exists') {
      toast({
        title: "📧 Email Already Exists",
        description: "An account with this email already exists. Please sign in instead.",
        variant: "destructive",
      });
    } else if (error === 'tenant_not_found') {
      toast({
        title: "🏢 Tenant Not Found",
        description: "The organization you're trying to join doesn't exist. Please check the URL.",
        variant: "destructive",
      });
    } else if (error === 'invalid_invitation') {
      toast({
        title: "❌ Invalid Invitation",
        description: "This invitation link is invalid or has expired. Please request a new one.",
        variant: "destructive",
      });
    } else if (error === 'registration_failed') {
      toast({
        title: "❌ Registration Failed",
        description: "Unable to create your account. Please try again or contact support.",
        variant: "destructive",
      });
    } else if (message === 'invitation_accepted') {
      toast({
        title: "🎉 Invitation Accepted",
        description: "Welcome to the team! Your account has been created successfully.",
        variant: "default",
      });
    }
  }, [urlSearchParams, toast]);

  return (
    <AuthForm
      type="sign-up"
      invitationToken={invitationToken}
      isCloudEnv={false}
      googleAuthUrl={GOOGLE_AUTH_URL}
      githubAuthUrl={GITHUB_AUTH_URL}
      isGoogleOAuthEnabled={isGoogleOAuthEnabled}
      isGithubOAuthEnabled={isGithubOAuthEnabled}
    />
  );
};

export default SignUp;