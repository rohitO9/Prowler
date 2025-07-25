import "@/styles/globals.css";

import { Spacer } from "@nextui-org/react";
import React from "react";

import { WorkflowAddProvider } from "@/components/providers/workflow";
import { ContentLayout } from "@/components/ui";
import { FileBarChart } from "lucide-react";

interface ProviderLayoutProps {
  children: React.ReactNode;
}

export default function ProviderLayout({ children }: ProviderLayoutProps) {
  return (
    <ContentLayout title="Connect Your Cloud Service" icon="fluent:cloud-sync-24-regular">
      <div className="flex flex-col items-center w-full">
        <div className="w-full max-w-4xl">
          <WorkflowAddProvider />
        </div>
        <div className="w-full max-w-4xl mt-8">
          {children}
        </div>
      </div>
    </ContentLayout>
  );
}
