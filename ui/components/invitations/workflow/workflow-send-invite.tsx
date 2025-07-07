"use client";

import { Progress, Spacer } from "@nextui-org/react";
import { usePathname } from "next/navigation";
import React from "react";

import { VerticalSteps } from "./vertical-steps";

const steps = [
  {
    title: "Add User Details",
    description:
      "Enter the email address.",
    href: "/invitations/new",
  },
  {
    title: "Confirm & Send",
    description:
      "Review the invitation details.",
    href: "/invitations/check-details",
  },
];

export const WorkflowSendInvite = () => {
  const pathname = usePathname();

  // Calculate current step based on pathname
  const currentStepIndex = steps.findIndex((step) =>
    pathname.endsWith(step.href),
  );
  const currentStep = currentStepIndex === -1 ? 0 : currentStepIndex;

  return (
    <section className="w-full max-w-3xl mx-auto flex flex-col items-center">
      <h1 className="text-2xl md:text-3xl font-bold text-center mb-2 mt-2 bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">Invite a User</h1>
      <p className="text-default-500 text-base text-center mb-6 max-w-2xl">
      Complete the steps below to invite a new user to your organization.
      </p>
      <div className="w-full">
        <Progress
          className="transition-all duration-1500 px-0.5 mb-5"
          classNames={{
            base: "px-0.5 mb-5",
            label: "text-small",
            value: "text-small text-default-400",
            indicator: "bg-gradient-to-r from-indigo-500 to-purple-500", // This is the filled bar
          }}
          label="Steps"
          maxValue={steps.length}
          minValue={0}
          showValueLabel={true}
          size="md"
          value={currentStep + 1}
          valueLabel={`${currentStep + 1} of ${steps.length}`}
        />
        <VerticalSteps
          horizontal
          hideProgressBars
          currentStep={currentStep}
          stepClassName="border border-default-200 dark:border-default-50 aria-[current]:bg-default-100 dark:aria-[current]:bg-prowler-blue-800 cursor-default"
          steps={steps}
        />
      </div>
      <Spacer y={4} />
    </section>
  );
};
