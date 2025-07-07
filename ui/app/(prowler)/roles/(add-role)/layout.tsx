import "@/styles/globals.css";

import { Spacer } from "@nextui-org/react";
import React from "react";

import { WorkflowAddEditRole } from "@/components/roles/workflow";
import { NavigationHeader } from "@/components/ui";

interface RoleLayoutProps {
  children: React.ReactNode;
}

export default function RoleLayout({ children }: RoleLayoutProps) {
  return (
    <>
      <NavigationHeader
        title="Role Management"
        icon="icon-park-outline:close-small"
        href="/roles"
      />
      <Spacer y={10} />
      <div className="flex flex-col items-center gap-0 w-full">
        <div className="order-1 w-full max-w-xl">
          <WorkflowAddEditRole />
        </div>
        <div className="order-2 w-full">
          {children}
        </div>
      </div>
    </>
  );
}
