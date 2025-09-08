"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Card, CardBody, CardHeader, Divider, Link, Badge } from "@nextui-org/react";
import { Icon } from "@iconify/react";
import { AzureStatus } from "@/components/auth/azure-status";
import { AzureSetupGuide } from "@/components/auth/azure-setup-guide";
import { useAzureAD } from "@/hooks/use-azure-ad";

export default function AzureDashboard() {
  const router = useRouter();
  const { config, isLoading, isConfigured } = useAzureAD();
  const [showSetupGuide, setShowSetupGuide] = useState(false);

  const quickActions = [
    {
      title: "Configure Azure AD",
      description: "Set up Azure AD authentication",
      icon: "heroicons:cog",
      color: "primary",
      href: "/azure",
      disabled: false,
    },
    {
      title: "Test Integration",
      description: "Test Azure AD authentication flow",
      icon: "heroicons:play",
      color: "secondary",
      href: "/azure/test",
      disabled: !isConfigured,
    },
    {
      title: "View Documentation",
      description: "Read setup and usage guides",
      icon: "heroicons:document-text",
      color: "default",
      href: "/docs/azure-ad-setup",
      disabled: false,
    },
    {
      title: "Manage Users",
      description: "View and manage Azure AD users",
      icon: "heroicons:users",
      color: "success",
      href: "/users",
      disabled: !isConfigured,
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Azure AD Integration
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              Manage Azure Active Directory authentication and user synchronization
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
              onClick={() => router.push("/sign-in")}
              startContent={<Icon icon="heroicons:arrow-left" width={16} />}
            >
              Back to Sign In
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Status Card */}
          <div className="lg:col-span-1">
            <AzureStatus showActions={false} />
          </div>

          {/* Quick Actions */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <Icon icon="heroicons:bolt" className="h-6 w-6 text-blue-600" />
                  <div>
                    <h3 className="text-lg font-semibold">Quick Actions</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Common tasks and configuration options
                    </p>
                  </div>
                </div>
              </CardHeader>
              <Divider />
              <CardBody>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {quickActions.map((action, index) => (
                    <Card
                      key={index}
                      className={`cursor-pointer transition-all hover:shadow-md ${
                        action.disabled ? "opacity-50" : ""
                      }`}
                      isPressable={!action.disabled}
                      onPress={() => !action.disabled && router.push(action.href)}
                    >
                      <CardBody className="p-4">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg bg-${action.color}-100 dark:bg-${action.color}-900/20`}>
                            <Icon
                              icon={action.icon}
                              className={`h-5 w-5 text-${action.color}-600`}
                            />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-medium text-sm">{action.title}</h4>
                            <p className="text-xs text-gray-600 dark:text-gray-400">
                              {action.description}
                            </p>
                          </div>
                        </div>
                      </CardBody>
                    </Card>
                  ))}
                </div>
              </CardBody>
            </Card>
          </div>
        </div>

        {/* Configuration Details */}
        {isConfigured && config && (
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <Icon icon="heroicons:information-circle" className="h-6 w-6 text-blue-600" />
                <div>
                  <h3 className="text-lg font-semibold">Configuration Details</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Current Azure AD application settings
                  </p>
                </div>
              </div>
            </CardHeader>
            <Divider />
            <CardBody>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">Tenant ID</label>
                  <div className="mt-1 font-mono text-sm bg-gray-100 dark:bg-gray-800 px-3 py-2 rounded">
                    {config.tenant_id}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Client ID</label>
                  <div className="mt-1 font-mono text-sm bg-gray-100 dark:bg-gray-800 px-3 py-2 rounded">
                    {config.client_id}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Authority</label>
                  <div className="mt-1 font-mono text-sm bg-gray-100 dark:bg-gray-800 px-3 py-2 rounded">
                    {config.authority}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Redirect URI</label>
                  <div className="mt-1 font-mono text-sm bg-gray-100 dark:bg-gray-800 px-3 py-2 rounded">
                    {config.redirect_uri}
                  </div>
                </div>
              </div>
              
              <div className="mt-4">
                <label className="text-sm font-medium text-gray-500">Scopes</label>
                <div className="mt-1 flex flex-wrap gap-2">
                  {config.scopes.map((scope, index) => (
                    <Badge key={index} variant="flat" color="primary" className="text-xs">
                      {scope}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardBody>
          </Card>
        )}

        {/* Help Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Icon icon="heroicons:academic-cap" className="h-6 w-6 text-blue-600" />
              <div>
                <h3 className="text-lg font-semibold">Need Help?</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Resources and documentation for Azure AD integration
                </p>
              </div>
            </div>
          </CardHeader>
          <Divider />
          <CardBody>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                <Icon icon="heroicons:question-mark-circle" className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                <h4 className="font-medium mb-1">FAQ</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  Common questions and troubleshooting tips
                </p>
                <Button
                  size="sm"
                  variant="bordered"
                  href="/docs/azure-ad-faq"
                  as="a"
                >
                  View FAQ
                </Button>
              </div>
              
              <div className="text-center p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <Icon icon="heroicons:envelope" className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                <h4 className="font-medium mb-1">Support</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  Get help from our support team
                </p>
                <Button
                  size="sm"
                  variant="bordered"
                  href="/contact"
                  as="a"
                >
                  Contact Support
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
