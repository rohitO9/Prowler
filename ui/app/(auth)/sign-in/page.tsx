"use client";
import { AuthForm } from "@/components/auth/oss";
import {
  getAuthUrl,
  isGithubOAuthEnabled,
  isGoogleOAuthEnabled,
  isAzureOAuthEnabled,
} from "@/lib/helper";
import { useEffect } from "react";
import { getSubdomain } from "../../../src/utils/subdomain";

const SignIn = () => {
  const GOOGLE_AUTH_URL = getAuthUrl("google");
  const GITHUB_AUTH_URL = getAuthUrl("github");
  const AZURE_AUTH_URL = getAuthUrl("azure");

  useEffect(() => {
    // Auto-detect organization from subdomain
    const subdomain = getSubdomain();
    if (subdomain && typeof window !== "undefined") {
      localStorage.setItem("company", subdomain);
    }
  }, []);

  return (
    <AuthForm
      type="sign-in"
      googleAuthUrl={GOOGLE_AUTH_URL}
      githubAuthUrl={GITHUB_AUTH_URL}
      isGoogleOAuthEnabled={isGoogleOAuthEnabled}
      isGithubOAuthEnabled={isGithubOAuthEnabled}
      azureAuthUrl={AZURE_AUTH_URL}
    />
  );
};

export default SignIn;
