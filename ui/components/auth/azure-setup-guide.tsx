"use client";

import { useState } from "react";
import { Button, Card, CardBody, CardHeader, Divider, Link } from "@nextui-org/react";
import { Icon } from "@iconify/react";

interface AzureSetupGuideProps {
  onClose?: () => void;
}

export const AzureSetupGuide = ({ onClose }: AzureSetupGuideProps) => {
  const [activeStep, setActiveStep] = useState(1);

  const steps = [
    {
      id: 1,
      title: "Register Application in Azure AD",
      description: "Create a new application registration in your Azure AD tenant",
      content: (
        <div className="space-y-4">
          <ol className="list-decimal list-inside space-y-2 text-sm">
            <li>Sign in to the <Link href="https://portal.azure.com" target="_blank" className="text-primary">Azure Portal</Link></li>
            <li>Navigate to <strong>Azure Active Directory</strong> → <strong>App registrations</strong></li>
            <li>Click <strong>New registration</strong></li>
            <li>Fill in the application details:
              <ul className="list-disc list-inside ml-4 mt-2 space-y-1">
                <li><strong>Name:</strong> Prowler Security Scanner</li>
                <li><strong>Supported account types:</strong> Accounts in this organizational directory only</li>
                <li><strong>Redirect URI:</strong> <code className="bg-gray-100 px-2 py-1 rounded">http://localhost:3000/azure/callback</code></li>
              </ul>
            </li>
            <li>Click <strong>Register</strong></li>
          </ol>
        </div>
      ),
    },
    {
      id: 2,
      title: "Configure Application Permissions",
      description: "Set up the required permissions for the application",
      content: (
        <div className="space-y-4">
          <ol className="list-decimal list-inside space-y-2 text-sm">
            <li>In your registered application, go to <strong>API permissions</strong></li>
            <li>Click <strong>Add a permission</strong></li>
            <li>Select <strong>Microsoft Graph</strong></li>
            <li>Choose <strong>Delegated permissions</strong></li>
            <li>Add the following permissions:
              <ul className="list-disc list-inside ml-4 mt-2 space-y-1">
                <li><code>User.Read</code> - Read user profile</li>
                <li><code>User.Read.All</code> - Read all users (for user sync)</li>
                <li><code>GroupMember.Read.All</code> - Read group membership (for role mapping)</li>
              </ul>
            </li>
            <li>Click <strong>Add permissions</strong></li>
            <li>Click <strong>Grant admin consent</strong></li>
          </ol>
        </div>
      ),
    },
    {
      id: 3,
      title: "Create Client Secret",
      description: "Generate a client secret for application authentication",
      content: (
        <div className="space-y-4">
          <ol className="list-decimal list-inside space-y-2 text-sm">
            <li>Go to <strong>Certificates & secrets</strong></li>
            <li>Click <strong>New client secret</strong></li>
            <li>Add a description (e.g., "Prowler Integration")</li>
            <li>Select expiration period (recommend 12 months)</li>
            <li>Click <strong>Add</strong></li>
            <li><strong>Important:</strong> Copy the generated secret value immediately - you won't be able to see it again!</li>
          </ol>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-sm text-yellow-800">
              <strong>Security Note:</strong> Store the client secret securely and never commit it to version control.
            </p>
          </div>
        </div>
      ),
    },
    {
      id: 4,
      title: "Note Application Details",
      description: "Record the essential information for configuration",
      content: (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-900 mb-2">Required Information:</h4>
            <div className="space-y-2 text-sm">
              <div><strong>Application (client) ID:</strong> Found in the Overview page</div>
              <div><strong>Directory (tenant) ID:</strong> Found in the Overview page</div>
              <div><strong>Client Secret:</strong> The value you copied in the previous step</div>
              <div><strong>Redirect URI:</strong> <code className="bg-blue-100 px-2 py-1 rounded">http://localhost:3000/azure/callback</code></div>
            </div>
          </div>
          <p className="text-sm text-gray-600">
            You'll need these values to configure Azure AD integration in Prowler.
          </p>
        </div>
      ),
    },
         {
       id: 5,
       title: "Configure Backend Environment Variables",
       description: "Set up the required environment variables in your backend",
       content: (
         <div className="space-y-4">
           <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
             <h4 className="font-semibold text-blue-900 mb-2">Backend Configuration:</h4>
             <p className="text-sm text-blue-800 mb-3">
               Azure AD is configured through backend environment variables for secure single-tenant setup.
             </p>
           </div>
           <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
             <h4 className="font-semibold text-gray-900 mb-2">Environment Variables:</h4>
             <pre className="text-sm bg-gray-100 p-3 rounded overflow-x-auto">
 {`# Azure AD Configuration (Backend .env file)
 AZURE_AD_ENABLED=True
 AZURE_AD_CLIENT_ID=your_client_id_here
 AZURE_AD_CLIENT_SECRET=your_client_secret_here
 AZURE_AD_TENANT_ID=your_tenant_id_here
 AZURE_AD_REDIRECT_URI=http://localhost:3000/azure/callback

 # Optional Settings
 AZURE_AD_AUTO_CREATE_USERS=True
 AZURE_AD_SYNC_GROUPS=False
 AZURE_AD_REQUIRE_EMAIL_VERIFICATION=False`}
             </pre>
           </div>
           <p className="text-sm text-gray-600">
             Add these variables to your backend <code>.env</code> file. The frontend will automatically detect the configuration.
           </p>
         </div>
       ),
     },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-hidden">
        <CardHeader className="flex justify-between items-center">
          <div>
            <h2 className="text-xl font-semibold">Azure AD Setup Guide</h2>
            <p className="text-sm text-gray-600">Follow these steps to configure Azure AD integration</p>
          </div>
          <Button
            isIconOnly
            variant="light"
            onClick={onClose}
            className="text-gray-500"
          >
            <Icon icon="heroicons:x-mark" width={20} />
          </Button>
        </CardHeader>
        
        <Divider />
        
        <CardBody className="overflow-y-auto">
          <div className="flex gap-6">
            {/* Step Navigation */}
            <div className="w-64 flex-shrink-0">
              <nav className="space-y-2">
                {steps.map((step) => (
                  <button
                    key={step.id}
                    onClick={() => setActiveStep(step.id)}
                    className={`w-full text-left p-3 rounded-lg transition-colors ${
                      activeStep === step.id
                        ? "bg-primary text-white"
                        : "bg-gray-50 hover:bg-gray-100"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${
                        activeStep === step.id
                          ? "bg-white text-primary"
                          : "bg-gray-300 text-gray-600"
                      }`}>
                        {step.id}
                      </div>
                      <div>
                        <div className="font-medium">{step.title}</div>
                        <div className="text-xs opacity-75">{step.description}</div>
                      </div>
                    </div>
                  </button>
                ))}
              </nav>
            </div>

            {/* Step Content */}
            <div className="flex-1">
              {steps.find(step => step.id === activeStep)?.content}
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
};
