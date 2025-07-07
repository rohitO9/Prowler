"use client";

import { Progress, Spacer } from "@nextui-org/react";
import { usePathname } from "next/navigation";
import React from "react";

import { VerticalSteps } from "./vertical-steps";

const steps = [
  {
    title: "Create a new role",
    description: "Enter the name of the role",
    href: "/roles/new",
  },
  {
    title: "Edit a existing role",
    description:
      "Update the role's details",
    href: "/roles/edit",
  },
];

export const WorkflowAddEditRole = () => {
  const pathname = usePathname();

  // Calculate current step based on pathname
  const currentStepIndex = steps.findIndex((step) =>
    pathname.endsWith(step.href),
  );
  const currentStep = currentStepIndex === -1 ? 0 : currentStepIndex;

  return (
    <div className="w-full flex justify-center">
      <section className="max-w-md w-full">
        <h1 className="mb-2 text-2xl font-medium text-center bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent" id="getting-started">
          Role Creation & Permissions
        </h1>
        <p className="mb-5 text-small text-default-500 text-center">
          Set up a new role and customize its permissions as needed.
        </p>
        <div className="flex justify-center w-full">
          <div className="w-full max-w-lg">
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
          </div>
        </div>
        <div className="flex flex-row gap-8 justify-center mt-4">
          {steps.map((step, idx) => (
            <div
              key={step.title}
              className={`rounded-xl border border-default-200 dark:border-default-50 px-6 py-4 flex flex-row items-center min-w-[272px] ${idx === currentStep ? 'bg-default-100 dark:bg-prowler-blue-800' : ''}`}
            >
              <div className="flex flex-col justify-center">
                <div className="flex items-center gap-2">
                  <span className="font-semibold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent text-sm">{idx + 1}.</span>
                  <span className="font-semibold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent text-sm">{step.title}</span>
                </div>
                <div className="text-xs text-default-500 mt-0.5 text-left">{step.description}</div>
              </div>
            </div>
          ))}
        </div>
        
      </section>
    </div>
  );
};
