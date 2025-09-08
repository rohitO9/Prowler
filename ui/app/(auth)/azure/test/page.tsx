"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Card, CardBody, CardHeader, Input, Divider } from "@nextui-org/react";
import { Icon } from "@iconify/react";
import { testAzureADAuth, checkTrialStatus } from "@/actions/auth/azure-ad";
import { useToast } from "@/components/ui";

export default function AzureTestPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [authCode, setAuthCode] = useState("");
  const [email, setEmail] = useState("");
  const [isTesting, setIsTesting] = useState(false);
  const [testResults, setTestResults] = useState<any>(null);

  const handleTestAuth = async () => {
    if (!authCode.trim()) {
      toast({
        variant: "destructive",
        title: "Missing Code",
        description: "Please enter an authorization code to test",
      });
      return;
    }

    setIsTesting(true);
    try {
      const result = await testAzureADAuth(authCode);
      setTestResults(result);
      
      if (result) {
        toast({
          title: "Test Successful",
          description: "Azure AD authentication test completed successfully",
        });
      } else {
        toast({
          variant: "destructive",
          title: "Test Failed",
          description: "Azure AD authentication test failed",
        });
      }
    } catch (error) {
      console.error("Test error:", error);
      toast({
        variant: "destructive",
        title: "Test Error",
        description: "An error occurred during testing",
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleCheckTrialStatus = async () => {
    if (!email.trim()) {
      toast({
        variant: "destructive",
        title: "Missing Email",
        description: "Please enter an email address to check trial status",
      });
      return;
    }

    setIsTesting(true);
    try {
      const result = await checkTrialStatus(email);
      setTestResults({ trialStatus: result });
      
      toast({
        title: "Trial Status Checked",
        description: "Trial status has been retrieved successfully",
      });
    } catch (error) {
      console.error("Trial status error:", error);
      toast({
        variant: "destructive",
        title: "Check Failed",
        description: "Failed to check trial status",
      });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <Icon icon="logos:microsoft-azure" className="h-8 w-8 text-blue-600" />
            <h1 className="text-2xl font-bold">Azure AD Integration Test</h1>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            Test Azure AD authentication and configuration
          </p>
        </CardHeader>
        
        <Divider />
        
        <CardBody className="space-y-6">
          {/* Authorization Code Test */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Test Authentication</h3>
            <div className="space-y-3">
              <Input
                label="Authorization Code"
                placeholder="Enter authorization code from Azure AD"
                value={authCode}
                onChange={(e) => setAuthCode(e.target.value)}
                description="Paste the authorization code received from Azure AD OAuth flow"
              />
              <Button
                color="primary"
                onClick={handleTestAuth}
                isLoading={isTesting}
                disabled={!authCode.trim()}
                startContent={<Icon icon="heroicons:play" width={16} />}
              >
                Test Authentication
              </Button>
            </div>
          </div>

          <Divider />

          {/* Trial Status Check */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Check Trial Status</h3>
            <div className="space-y-3">
              <Input
                label="Email Address"
                placeholder="Enter email to check trial status"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                description="Check if a user has trial access"
              />
              <Button
                color="secondary"
                onClick={handleCheckTrialStatus}
                isLoading={isTesting}
                disabled={!email.trim()}
                startContent={<Icon icon="heroicons:information-circle" width={16} />}
              >
                Check Trial Status
              </Button>
            </div>
          </div>

          {/* Test Results */}
          {testResults && (
            <>
              <Divider />
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Test Results</h3>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <pre className="text-sm overflow-x-auto">
                    {JSON.stringify(testResults, null, 2)}
                  </pre>
                </div>
              </div>
            </>
          )}

          {/* Navigation */}
          <Divider />
          <div className="flex gap-3">
            <Button
              variant="bordered"
              onClick={() => router.push("/azure")}
              startContent={<Icon icon="heroicons:arrow-left" width={16} />}
            >
              Back to Configuration
            </Button>
            <Button
              variant="bordered"
              onClick={() => router.push("/sign-in")}
              startContent={<Icon icon="heroicons:home" width={16} />}
            >
              Back to Sign In
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
