// "use client"; // Ensures this is a Client Component

// import { useEffect } from "react";
// import { useRouter } from "next/navigation"; // Router for navigation
// import { AuthForm } from "@/components/auth/oss";
// import { getAuthUrl, isGithubOAuthEnabled, isGoogleOAuthEnabled } from "@/lib/helper";

// const SignIn = () => {
//   const router = useRouter();
//   const GOOGLE_AUTH_URL = getAuthUrl("google");
//   const GITHUB_AUTH_URL = getAuthUrl("github");

//   const bypassAuth = true;
  
// useEffect(() => {
//   if (!bypassAuth) return;
//   const callbackUrl = new URLSearchParams(window.location.search).get("callbackUrl") || "/";
//   localStorage.setItem("user", JSON.stringify({ name: "Test User", email: "testuser@example.com" }));
//   console.log("Redirecting to:", callbackUrl);  // Add a console log to confirm the URL is correct
//   router.push(callbackUrl); // Push to the URL
// }, [router]);


//   return (
//     <AuthForm
//       type="sign-in"
//       googleAuthUrl={GOOGLE_AUTH_URL}
//       githubAuthUrl={GITHUB_AUTH_URL}
//       isGoogleOAuthEnabled={isGoogleOAuthEnabled}
//       isGithubOAuthEnabled={isGithubOAuthEnabled}
//     />
//   );
// };

// export default SignIn;



import { AuthForm } from "@/components/auth/oss";
import {
  getAuthUrl,
  isGithubOAuthEnabled,
  isGoogleOAuthEnabled,
} from "@/lib/helper";

const SignIn = () => {
  const GOOGLE_AUTH_URL = getAuthUrl("google");
  const GITHUB_AUTH_URL = getAuthUrl("github");
  return (
    <AuthForm
      type="sign-in"
      googleAuthUrl={GOOGLE_AUTH_URL}
      githubAuthUrl={GITHUB_AUTH_URL}
      isGoogleOAuthEnabled={isGoogleOAuthEnabled}
      isGithubOAuthEnabled={isGithubOAuthEnabled}
    />
  );
};

export default SignIn;


