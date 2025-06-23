import { AuthForm } from "@/components/auth/oss";
import { getAuthUrl, isGithubOAuthEnabled } from "@/lib/helper";
import { isGoogleOAuthEnabled } from "@/lib/helper";
import { SearchParamsProps } from "@/types";

const SignUp = ({ searchParams }: { searchParams: SearchParamsProps }) => {
  const invitationToken =
    typeof searchParams?.invitation_token === "string"
      ? searchParams.invitation_token
      : null;

  const GOOGLE_AUTH_URL = getAuthUrl("google");
  const GITHUB_AUTH_URL = getAuthUrl("github");

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
// "use client";
// import { AuthForm } from "@/components/auth/oss";
// import { getAuthUrl, isGithubOAuthEnabled, isGoogleOAuthEnabled } from "@/lib/helper";
// import { useEffect } from "react";
// import { useRouter } from "next/navigation";
// import { SearchParamsProps } from "@/types";

// const SignUp = ({ searchParams }: { searchParams: SearchParamsProps }) => {
//   const router = useRouter();
  
//   const invitationToken =
//     typeof searchParams?.invitation_token === "string"
//       ? searchParams.invitation_token
//       : null;

//   const GOOGLE_AUTH_URL = getAuthUrl("google");
//   const GITHUB_AUTH_URL = getAuthUrl("github");

//   // Flag to control the bypassing of the sign-up process
//   const bypassSignUp = true;

//   useEffect(() => {
//     if (bypassSignUp) {
//       // Simulate a signed-up user (for testing purposes)
//       const mockUser = {
//         name: "Test User",
//         email: "testuser@example.com",
//       };

//       // Store the mock user in localStorage (or context, if preferred)
//       localStorage.setItem("user", JSON.stringify(mockUser));

//       // Optionally, redirect to a protected page after "successful" sign-up
//       router.push("/dashboard"); // You can change this path to any page
//     }
//   }, [router]);

//   return (
//     <AuthForm
//       type="sign-up"
//       invitationToken={invitationToken}
//       googleAuthUrl={GOOGLE_AUTH_URL}
//       githubAuthUrl={GITHUB_AUTH_URL}
//       isGoogleOAuthEnabled={isGoogleOAuthEnabled}
//       isGithubOAuthEnabled={isGithubOAuthEnabled}
//     />
//   );
// };

// export default SignUp;

