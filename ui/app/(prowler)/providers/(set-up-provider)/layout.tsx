import "@/styles/globals.css";

import { Spacer } from "@nextui-org/react";
import React from "react";

import { WorkflowAddProvider } from "@/components/providers/workflow";
import { NavigationHeader } from "@/components/ui";
import { FileBarChart } from "lucide-react";

interface ProviderLayoutProps {
  children: React.ReactNode;
}

export default function ProviderLayout({ children }: ProviderLayoutProps) {
  return (
    <>
      <div className="w-full border-b-2 border-gray-400 dark:border-gray-500 my-10" />
      <Spacer y={0} />
      <div className="flex flex-col items-center w-full">
        <div className="w-full max-w-4xl">
          <WorkflowAddProvider />
        </div>
        <div className="w-full max-w-4xl mt-8">
          {children}
        </div>
      </div>
    </>
  );
}
