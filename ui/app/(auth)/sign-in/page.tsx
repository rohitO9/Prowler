import { AuthForm } from "@/components/auth/oss";
import {
  getAuthUrl,
  isGithubOAuthEnabled,
  isGoogleOAuthEnabled,
  isAzureOAuthEnabled,
} from "@/lib/helper";

const SignIn = () => {
  const GOOGLE_AUTH_URL = getAuthUrl("google");
  const GITHUB_AUTH_URL = getAuthUrl("github");
  const AZURE_AUTH_URL = getAuthUrl("azure");
  return (
    <AuthForm
      type="sign-in"
      googleAuthUrl={GOOGLE_AUTH_URL}
      githubAuthUrl={GITHUB_AUTH_URL}
      isGoogleOAuthEnabled={isGoogleOAuthEnabled}
      isGithubOAuthEnabled={isGithubOAuthEnabled}
      azureAuthUrl={AZURE_AUTH_URL}
      // isAzureOAuthEnabled={isAzureOAuthEnabled}
    />
  );
};

export default SignIn;
