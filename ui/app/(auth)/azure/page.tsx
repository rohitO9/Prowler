"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Card, CardBody, CardHeader, Divider, Badge } from "@nextui-org/react";
import { Icon } from "@iconify/react";
import { AzureStatus } from "@/components/auth/azure-status";
import { AzureSetupGuide } from "@/components/auth/azure-setup-guide";
import { useAzureAD } from "@/hooks/use-azure-ad";
import { useToast } from "@/components/ui";

export default function AzureConfig() {
  const router = useRouter();
  const { toast } = useToast();
  const { config, isLoading, error, isConfigured } = useAzureAD();
  const [showSetupGuide, setShowSetupGuide] = useState(false);

  const handleTestIntegration = () => {
    if (!isConfigured) {
      toast({
        variant: "destructive",
        title: "Not Configured",
        description: "Azure AD is not configured. Please check your backend environment variables.",
      });
      return;
    }
    router.push("/azure/test");
  };

  const handleGoToDashboard = () => {
    router.push("/azure/dashboard");
  };

  const handleBackToSignIn = () => {
    router.push("/sign-in");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Azure AD Configuration
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              Azure AD is configured via backend environment variables
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              variant="bordered"
              onClick={() => setShowSetupGuide(true)}
              startContent={<Icon icon="heroicons:question-mark-circle" width={16} />}
            >
              Setup Guide
            </Button>
            <Button
              color="primary"
              onClick={handleBackToSignIn}
              startContent={<Icon icon="heroicons:arrow-left" width={16} />}
            >
              Back to Sign In
            </Button>
          </div>
        </div>

        {/* Status Card */}
        <AzureStatus showActions={false} />

        {/* Configuration Info */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Icon icon="heroicons:information-circle" className="h-6 w-6 text-blue-600" />
              <div>
                <h3 className="text-lg font-semibold">Configuration Method</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Azure AD is configured using backend environment variables
                </p>
              </div>
            </div>
          </CardHeader>
          <Divider />
          <CardBody className="space-y-4">
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <Icon icon="heroicons:information-circle" className="h-5 w-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                    Backend Configuration
                  </p>
                  <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                    Azure AD settings are managed through environment variables in your backend. 
                    This ensures secure configuration management and single-tenant setup.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="text-sm font-medium">Required Environment Variables:</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge color="primary" variant="flat" size="sm">Required</Badge>
                    <span className="text-xs font-mono text-gray-600">AZURE_AD_CLIENT_ID</span>
                  </div>
                  <p className="text-xs text-gray-500">Your Azure AD application client ID</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge color="primary" variant="flat" size="sm">Required</Badge>
                    <span className="text-xs font-mono text-gray-600">AZURE_AD_CLIENT_SECRET</span>
                  </div>
                  <p className="text-xs text-gray-500">Your Azure AD application client secret</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge color="primary" variant="flat" size="sm">Required</Badge>
                    <span className="text-xs font-mono text-gray-600">AZURE_AD_TENANT_ID</span>
                  </div>
                  <p className="text-xs text-gray-500">Your Azure AD tenant ID</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge color="success" variant="flat" size="sm">Optional</Badge>
                    <span className="text-xs font-mono text-gray-600">AZURE_AD_REDIRECT_URI</span>
                  </div>
                  <p className="text-xs text-gray-500">OAuth redirect URI (defaults to localhost)</p>
                </div>
              </div>
            </div>

            {config && (
              <div className="space-y-3">
                <h4 className="text-sm font-medium">Current Configuration:</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-gray-500">Tenant ID</label>
                    <div className="mt-1 font-mono text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                      {config.tenant_id || "Not configured"}
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-500">Client ID</label>
                    <div className="mt-1 font-mono text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                      {config.client_id ? `${config.client_id.substring(0, 8)}...` : "Not configured"}
                    </div>
                  </div>
                  <div className="md:col-span-2">
                    <label className="text-xs font-medium text-gray-500">Redirect URI</label>
                    <div className="mt-1 font-mono text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                      {config.redirect_uri || "Not configured"}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardBody>
        </Card>

        {/* Action Buttons */}
        <div className="flex gap-3 justify-center">
          <Button
            color="primary"
            onClick={handleTestIntegration}
            disabled={!isConfigured}
            startContent={<Icon icon="heroicons:play" width={16} />}
          >
            Test Integration
          </Button>
          <Button
            variant="bordered"
            onClick={handleGoToDashboard}
            startContent={<Icon icon="heroicons:chart-bar" width={16} />}
          >
            View Dashboard
          </Button>
          <Button
            variant="bordered"
            onClick={() => setShowSetupGuide(true)}
            startContent={<Icon icon="heroicons:document-text" width={16} />}
          >
            Setup Guide
          </Button>
        </div>

        {/* Help Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Icon icon="heroicons:academic-cap" className="h-6 w-6 text-blue-600" />
              <div>
                <h3 className="text-lg font-semibold">Need Help?</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Resources for configuring Azure AD integration
                </p>
              </div>
            </div>
          </CardHeader>
          <Divider />
          <CardBody>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="text-center p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <Icon icon="heroicons:document-text" className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                <h4 className="font-medium mb-1">Setup Guide</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  Step-by-step instructions for configuring Azure AD
                </p>
                <Button
                  size="sm"
                  variant="bordered"
                  onClick={() => setShowSetupGuide(true)}
                >
                  View Guide
                </Button>
              </div>
              
              <div className="text-center p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <Icon icon="heroicons:cog" className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                <h4 className="font-medium mb-1">Backend Configuration</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  Configure environment variables in your backend
                </p>
                <Button
                  size="sm"
                  variant="bordered"
                  href="/docs/azure-ad-setup"
                  as="a"
                >
                  View Docs
                </Button>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {showSetupGuide && (
        <AzureSetupGuide onClose={() => setShowSetupGuide(false)} />
      )}
    </div>
  );
} 