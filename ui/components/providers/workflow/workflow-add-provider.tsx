"use client";

import { Progress, Spacer } from "@nextui-org/react";
import { usePathname } from "next/navigation";
import React from "react";

import { VerticalSteps } from "./vertical-steps";

const steps = [
  {
    title: "Select a Cloud Service",
    href: "/providers/connect-account",
  },
  {
    title: "Provide Authentication Info",
    href: "/providers/add-credentials",
  },
  {
    title: "Validate Setup & Launch Scan",
    href: "/providers/test-connection",
  },
];

export const WorkflowAddProvider = () => {
  const pathname = usePathname();

  // Determine current step from path
  const currentStepIndex = steps.findIndex((step) =>
    pathname.endsWith(step.href),
  );
  const currentStep = currentStepIndex === -1 ? 0 : currentStepIndex;

  return (
    <section className="w-full max-w-4xl mt-8">
      <h1 className="mb-2 text-xl text-center font-medium" id="getting-started">
        Connect Your Cloud Service
      </h1>
      <p className="mb-5 text-small text-center text-default-500">
        Follow the guided process below to set up your cloud environment and begin scanning.
      </p>
      <Progress
        classNames={{
          base: "px-0.5 mb-5",
          label: "text-small",
          value: "text-small text-default-400",
        }}
        label="Steps"
        maxValue={steps.length - 1}
        minValue={0}
        showValueLabel={true}
        size="md"
        value={currentStep}
        valueLabel={`${currentStep + 1} of ${steps.length}`}
      />
      <VerticalSteps
        hideProgressBars
        currentStep={currentStep}
        stepClassName="border border-default-200 dark:border-default-50 aria-[current]:bg-default-100 dark:aria-[current]:bg-prowler-blue-800 cursor-default"
        steps={steps}
      />
      <Spacer y={4} />
    </section>
  );
};
