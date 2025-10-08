"use client";
import { AuthForm } from "@/components/auth/oss";
import { getAuthUrl, isGithubOAuthEnabled, isGoogleOAuthEnabled } from "@/lib/helper";
import { SearchParamsProps } from "@/types";
import { useEffect } from "react";
import { getSubdomain } from "../../../src/utils/subdomain";

const SignUp = ({ searchParams }: { searchParams: SearchParamsProps }) => {
  const invitationToken =
    typeof searchParams?.invitation_token === "string"
      ? searchParams.invitation_token
      : null;

  const GOOGLE_AUTH_URL = getAuthUrl("google");
  const GITHUB_AUTH_URL = getAuthUrl("github");

  useEffect(() => {
    // Auto-detect organization from subdomain
    const subdomain = getSubdomain();
    if (subdomain && typeof window !== "undefined") {
      localStorage.setItem("company", subdomain);
    }
  }, []);

  return (
    <AuthForm
      type="sign-up"
      invitationToken={invitationToken}
      googleAuthUrl={GOOGLE_AUTH_URL}
      githubAuthUrl={GITHUB_AUTH_URL}
      isGoogleOAuthEnabled={isGoogleOAuthEnabled}
      isGithubOAuthEnabled={isGithubOAuthEnabled}
    />
  );
};

export default SignUp;
