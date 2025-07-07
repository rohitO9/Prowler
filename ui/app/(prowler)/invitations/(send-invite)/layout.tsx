import "@/styles/globals.css";

import { Spacer } from "@nextui-org/react";
import React from "react";

import { WorkflowSendInvite } from "@/components/invitations/workflow";
import { NavigationHeader } from "@/components/ui";

interface InvitationLayoutProps {
  children: React.ReactNode;
}

export default function InvitationLayout({ children }: InvitationLayoutProps) {
  return (
    <>
      <NavigationHeader
        title="Send Invitation"
        icon="icon-park-outline:close-small"
        href="/invitations"
      />
      <Spacer y={16} />
      <div className="flex flex-col items-center w-full gap-8">
        <div className="w-full max-w-2xl">
          <WorkflowSendInvite />
        </div>
        <div className="w-full max-w-2xl">
          {children}
        </div>
      </div>
    </>
  );
}
