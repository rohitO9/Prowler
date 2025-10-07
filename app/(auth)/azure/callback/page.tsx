"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authenticateWithAzureAD } from "@/actions/auth/azure-ad";
import { useToast } from "@/components/ui";
import { Icon } from "@iconify/react";

export default function AzureCallback() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = searchParams?.get("code");
        const error = searchParams?.get("error");
        const errorDescription = searchParams?.get("error_description");
        if (!searchParams) return;

        // Handle OAuth errors
        if (error) {
          console.error("Azure AD OAuth error:", error, errorDescription);
          toast({
            variant: "destructive",
            title: "Authentication Failed",
            description: errorDescription || "An error occurred during authentication",
          });
          router.push("/sign-in");
          return;
        }

        // Check if we have an authorization code
        if (!code) {
          console.error("No authorization code received");
          toast({
            variant: "destructive",
            title: "Authentication Failed",
            description: "No authorization code received from Azure AD",
          });
          router.push("/sign-in");
          return;
        }

        // Exchange the authorization code for tokens
        const result = await authenticateWithAzureAD(code);

        if (result.success) {
          toast({
            title: "Welcome!",
            description: `Successfully signed in as ${result.user?.name}`,
          });
          
          // Redirect to the dashboard
          router.push("/");
        } else {
          toast({
            variant: "destructive",
            title: "Authentication Failed",
            description: result.error || "Failed to authenticate with Azure AD",
          });
          router.push("/sign-in");
        }
      } catch (error) {
        console.error("Azure AD callback error:", error);
        toast({
          variant: "destructive",
          title: "Authentication Error",
          description: "An unexpected error occurred during authentication",
        });
        router.push("/sign-in");
      } finally {
        setIsProcessing(false);
      }
    };

    handleCallback();
  }, [searchParams, router, toast]);

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="text-center">
        {isProcessing ? (
          <>
            <div className="mb-4 flex justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Completing Azure AD Sign In
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Please wait while we complete your authentication...
            </p>
          </>
        ) : (
          <>
            <div className="mb-4 flex justify-center">
              <Icon 
                icon="logos:microsoft-azure" 
                className="h-12 w-12 text-blue-600"
              />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Redirecting...
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              You will be redirected shortly.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
