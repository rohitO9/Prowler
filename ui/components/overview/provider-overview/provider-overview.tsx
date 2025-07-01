"use client";

import { Card, CardBody } from "@nextui-org/react";
import { useState } from "react";

import { AddIcon } from "@/components/icons/Icons";
import {
  AWSProviderBadge,
  AzureProviderBadge,
  GCPProviderBadge,
  KS8ProviderBadge,
  M365ProviderBadge,
} from "@/components/icons/providers-badge";
import { ProviderDetailsModal } from "@/components/overview/provider-details-modal/provider-details-modal";
import { CustomButton } from "@/components/ui/custom/custom-button";
import { ProviderOverviewProps } from "@/types";

export const ProvidersOverview = ({
  providersOverview,
}: {
  providersOverview: ProviderOverviewProps;
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);

  const handleProviderClick = (providerId: string) => {
    console.log("Provider clicked:", providerId);
    setSelectedProvider(providerId);
    setIsModalOpen(true);
    console.log("Modal should open for provider:", providerId);
  };

  const calculatePassingPercentage = (pass: number, total: number) =>
    total > 0 ? ((pass / total) * 100).toFixed(2) : "0.00";

  const renderProviderBadge = (providerId: string) => {
    switch (providerId) {
      case "aws":
        return <AWSProviderBadge width={30} height={30} />;
      case "azure":
        return <AzureProviderBadge width={30} height={30} />;
      case "m365":
        return <M365ProviderBadge width={30} height={30} />;
      case "gcp":
        return <GCPProviderBadge width={30} height={30} />;
      case "kubernetes":
        return <KS8ProviderBadge width={30} height={30} />;
      default:
        return null;
    }
  };

  const providers = [
    { id: "aws", name: "AWS" },
    { id: "azure", name: "Azure" },
    { id: "m365", name: "M365" },
    { id: "gcp", name: "GCP" },
    { id: "kubernetes", name: "Kubernetes" },
  ];

  // If no data, show empty cards
  if (!providersOverview || !Array.isArray(providersOverview.data)) {
    return (
      <>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
          {providers.map((providerTemplate) => (
            <div 
              key={providerTemplate.id}
              onClick={() => handleProviderClick(providerTemplate.id)}
              className="cursor-pointer"
            >
              <Card 
                className="h-full dark:bg-prowler-blue-400 flex flex-col items-center justify-center p-4 transition-all duration-300 ease-in-out hover:scale-105 hover:shadow-lg dark:hover:shadow-xl hover:shadow-indigo-100 dark:hover:shadow-gray-800 border border-transparent hover:border-transparent dark:hover:border-gray-600 relative overflow-hidden group"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-lg"></div>
                <CardBody className="flex flex-col items-center justify-center relative z-10">
                  {renderProviderBadge(providerTemplate.id)}
                  <div className="mt-2 text-lg font-semibold">{providerTemplate.name}</div>
                  <div className="mt-2 text-center">
                    <div className="text-sm">Pass: 0.00%</div>
                    <div className="text-sm">Failing: -</div>
                    <div className="text-sm">Resources: -</div>
                  </div>
                </CardBody>
              </Card>
            </div>
          ))}
        </div>
        <div className="mt-8 flex w-full items-center justify-center">
          <CustomButton
            asLink="/providers"
            ariaLabel="Go to Providers page"
            variant="solid"
            color="action"
            size="md"
            endContent={<AddIcon size={20} />}
          >
            Add Provider
          </CustomButton>
        </div>
        <ProviderDetailsModal
          isOpen={isModalOpen}
          onOpenChange={setIsModalOpen}
          selectedProvider={selectedProvider}
        />
      </>
    );
  }

  // Map provider data to cards
  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
        {providers.map((providerTemplate) => {
          const providerData = providersOverview.data.find(
            (p) => p.id === providerTemplate.id,
          );

          return (
            <div 
              key={providerTemplate.id}
              onClick={() => handleProviderClick(providerTemplate.id)}
              className="cursor-pointer"
            >
              <Card 
                className="h-full dark:bg-prowler-blue-400 flex flex-col items-center justify-center p-4 transition-all duration-300 ease-in-out hover:scale-105 hover:shadow-lg dark:hover:shadow-xl hover:shadow-indigo-100 dark:hover:shadow-gray-800 border border-transparent hover:border-transparent dark:hover:border-gray-600 relative overflow-hidden group"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-lg"></div>
                <CardBody className="flex flex-col items-center justify-center relative z-10">
                  {renderProviderBadge(providerTemplate.id)}
                  <div className="mt-2 text-lg font-semibold">{providerTemplate.name}</div>
                  <div className="mt-2 text-center">
                    <div className="text-sm">
                      Pass: {providerData
                        ? calculatePassingPercentage(
                            providerData.attributes.findings.pass,
                            providerData.attributes.findings.total,
                          )
                        : "0.00"}
                      %
                    </div>
                    <div className="text-sm">
                      Failing: {providerData ? providerData.attributes.findings.fail : "-"}
                    </div>
                    <div className="text-sm">
                      Resources: {providerData ? providerData.attributes.resources.total : "-"}
                    </div>
                  </div>
                </CardBody>
              </Card>
            </div>
          );
        })}
      </div>
      <div className="mt-4 flex w-full items-center justify-center">
        <CustomButton
          asLink="/providers"
          ariaLabel="Go to Providers page"
          variant="solid"
          color="action"
          size="sm"
          endContent={<AddIcon size={20} />}
        >
          Add Provider
        </CustomButton>
      </div>
      <ProviderDetailsModal
        isOpen={isModalOpen}
        onOpenChange={setIsModalOpen}
        selectedProvider={selectedProvider}
      />
    </>
  );
};
