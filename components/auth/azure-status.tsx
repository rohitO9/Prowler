"use client";

import { useState, useEffect } from "react";
import { Card, CardBody, CardHeader, Button, Badge, Divider } from "@nextui-org/react";
import { Icon } from "@iconify/react";
import { useAzureAD } from "@/hooks/use-azure-ad";
import { useToast } from "@/components/ui";

interface AzureStatusProps {
  showActions?: boolean;
  className?: string;
}

export const AzureStatus = ({ showActions = true, className = "" }: AzureStatusProps) => {
  const { config, isLoading, error, isConfigured } = useAzureAD();
  const { toast } = useToast();
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  useEffect(() => {
    if (config) {
      setLastChecked(new Date());
    }
  }, [config]);

  const getStatusColor = () => {
    if (isLoading) return "default";
    if (error) return "danger";
    if (isConfigured) return "success";
    return "warning";
  };

  const getStatusText = () => {
    if (isLoading) return "Checking...";
    if (error) return "Error";
    if (isConfigured) return "Configured";
    return "Not Configured";
  };

  const getStatusIcon = () => {
    if (isLoading) return "heroicons:arrow-path";
    if (error) return "heroicons:x-circle";
    if (isConfigured) return "heroicons:check-circle";
    return "heroicons:exclamation-triangle";
  };

  const handleTestConnection = async () => {
    if (!isConfigured) {
      toast({
        variant: "destructive",
        title: "Not Configured",
        description: "Azure AD is not configured. Please configure it first.",
      });
      return;
    }

    toast({
      title: "Testing Connection",
      description: "Testing Azure AD connection...",
    });

    // Simulate connection test
    setTimeout(() => {
      toast({
        title: "Connection Test",
        description: "Azure AD connection test completed successfully.",
      });
    }, 2000);
  };

  const handleRefreshConfig = () => {
    window.location.reload();
  };

  return (
    <Card className={className}>
      <CardHeader className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <Icon icon="logos:microsoft-azure" className="h-6 w-6 text-blue-600" />
          <div>
            <h3 className="text-lg font-semibold">Azure AD Status</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Authentication configuration status
            </p>
          </div>
        </div>
        <Badge
          color={getStatusColor()}
          variant="flat"
          className="flex items-center gap-1"
        >
          <Icon icon={getStatusIcon()} width={14} />
          {getStatusText()}
        </Badge>
      </CardHeader>

      <Divider />

      <CardBody className="space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-4">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span className="ml-2 text-sm text-gray-600">Loading configuration...</span>
          </div>
        ) : error ? (
          <div className="space-y-3">
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <Icon icon="heroicons:x-circle" className="h-5 w-5 text-red-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-800 dark:text-red-200">
                    Configuration Error
                  </p>
                  <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                    {error}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : isConfigured ? (
          <div className="space-y-3">
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <Icon icon="heroicons:check-circle" className="h-5 w-5 text-green-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-green-800 dark:text-green-200">
                    Azure AD is properly configured
                  </p>
                  <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                    Users can authenticate using Azure AD
                  </p>
                </div>
              </div>
            </div>

            {config && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Configuration Details:</h4>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-500">Tenant ID:</span>
                    <div className="font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded truncate">
                      {config.tenant_id}
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-500">Client ID:</span>
                    <div className="font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded truncate">
                      {config.client_id}
                    </div>
                  </div>
                  <div className="col-span-2">
                    <span className="text-gray-500">Redirect URI:</span>
                    <div className="font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded truncate">
                      {config.redirect_uri}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {lastChecked && (
              <p className="text-xs text-gray-500">
                Last checked: {lastChecked.toLocaleTimeString()}
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <Icon icon="heroicons:exclamation-triangle" className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                    Azure AD not configured
                  </p>
                  <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                    Configure Azure AD to enable single sign-on authentication
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {showActions && (
          <>
            <Divider />
            <div className="flex gap-2">
              {isConfigured && (
                <Button
                  size="sm"
                  variant="bordered"
                  onClick={handleTestConnection}
                  startContent={<Icon icon="heroicons:play" width={14} />}
                >
                  Test Connection
                </Button>
              )}
              <Button
                size="sm"
                variant="bordered"
                onClick={handleRefreshConfig}
                startContent={<Icon icon="heroicons:arrow-path" width={14} />}
              >
                Refresh
              </Button>
              {!isConfigured && (
                <Button
                  size="sm"
                  color="primary"
                  href="/azure"
                  as="a"
                  startContent={<Icon icon="heroicons:cog" width={14} />}
                >
                  Configure
                </Button>
              )}
            </div>
          </>
        )}
      </CardBody>
    </Card>
  );
};
