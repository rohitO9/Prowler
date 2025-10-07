"use client";

import type { ButtonProps } from "@nextui-org/react";
import { cn } from "@nextui-org/react";
import { useControlledState } from "@react-stately/utils";
import { domAnimation, LazyMotion, m } from "framer-motion";
import type { ComponentProps } from "react";
import React from "react";

export type VerticalStepProps = {
  className?: string;
  description?: React.ReactNode;
  title?: React.ReactNode;
};

export interface VerticalStepsProps
  extends React.HTMLAttributes<HTMLButtonElement> {
  /**
   * An array of steps.
   *
   * @default []
   */
  steps?: VerticalStepProps[];
  /**
   * The color of the steps.
   *
   * @default "primary"
   */
  color?: ButtonProps["color"];
  /**
   * The current step index.
   */
  currentStep?: number;
  /**
   * The default step index.
   *
   * @default 0
   */
  defaultStep?: number;
  /**
   * Whether to hide the progress bars.
   *
   * @default false
   */
  hideProgressBars?: boolean;
  /**
   * The custom class for the steps wrapper.
   */
  className?: string;
  /**
   * The custom class for the step.
   */
  stepClassName?: string;
  /**
   * Callback function when the step index changes.
   */
  onStepChange?: (stepIndex: number) => void;
}

function CheckIcon(props: ComponentProps<"svg">) {
  return (
    <svg
      {...props}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      viewBox="0 0 24 24"
    >
      <m.path
        animate={{ pathLength: 1 }}
        d="M5 13l4 4L19 7"
        initial={{ pathLength: 0 }}
        strokeLinecap="round"
        strokeLinejoin="round"
        transition={{
          delay: 0.2,
          type: "tween",
          ease: "easeOut",
          duration: 0.3,
        }}
      />
    </svg>
  );
}

export const VerticalSteps = React.forwardRef<
  HTMLButtonElement,
  VerticalStepsProps
>(
  (
    {
      color = "primary",
      steps = [],
      defaultStep = 0,
      onStepChange,
      currentStep: currentStepProp,
      hideProgressBars = false,
      stepClassName,
      className,
      ...props
    },
    ref,
  ) => {
    const [currentStep, setCurrentStep] = useControlledState(
      currentStepProp,
      defaultStep,
      onStepChange,
    );

    const colors = React.useMemo(() => {
      let userColor;
      let fgColor;

      const colorsVars = [
        "[--active-fg-color:var(--step-fg-color)]",
        "[--active-border-color:var(--step-color)]",
        "[--active-color:var(--step-color)]",
        "[--complete-background-color:var(--step-color)]",
        "[--complete-border-color:var(--step-color)]",
        "[--inactive-border-color:hsl(var(--nextui-default-300))]",
        "[--inactive-color:hsl(var(--nextui-default-300))]",
      ];

      switch (color) {
        case "primary":
          userColor = "[--step-color:hsl(var(--nextui-primary))]";
          fgColor = "[--step-fg-color:hsl(var(--nextui-primary-foreground))]";
          break;
        case "secondary":
          userColor = "[--step-color:hsl(var(--nextui-secondary))]";
          fgColor = "[--step-fg-color:hsl(var(--nextui-secondary-foreground))]";
          break;
        case "success":
          userColor = "[--step-color:hsl(var(--nextui-success))]";
          fgColor = "[--step-fg-color:hsl(var(--nextui-success-foreground))]";
          break;
        case "warning":
          userColor = "[--step-color:hsl(var(--nextui-warning))]";
          fgColor = "[--step-fg-color:hsl(var(--nextui-warning-foreground))]";
          break;
        case "danger":
          userColor = "[--step-color:hsl(var(--nextui-error))]";
          fgColor = "[--step-fg-color:hsl(var(--nextui-error-foreground))]";
          break;
        case "default":
          userColor = "[--step-color:hsl(var(--nextui-default))]";
          fgColor = "[--step-fg-color:hsl(var(--nextui-default-foreground))]";
          break;
        default:
          userColor = "[--step-color:hsl(var(--nextui-primary))]";
          fgColor = "[--step-fg-color:hsl(var(--nextui-primary-foreground))]";
          break;
      }

      if (!className?.includes("--step-fg-color")) colorsVars.unshift(fgColor);
      if (!className?.includes("--step-color")) colorsVars.unshift(userColor);
      if (!className?.includes("--inactive-bar-color"))
        colorsVars.push(
          "[--inactive-bar-color:hsl(var(--nextui-default-300))]",
        );

      return colorsVars;
    }, [color, className]);

    return (
      <nav aria-label="Progress" className="w-full max-w-4xl">
        <ol className={cn("flex flex-row gap-x-6", colors, className)}>
          {steps?.map((step, stepIdx) => {
            const status =
              currentStep === stepIdx
                ? "active"
                : currentStep < stepIdx
                  ? "inactive"
                  : "complete";

            return (
              <li key={stepIdx} className="relative min-w-[250px] ">
                <div className="flex w-100  max-w-full items-center">
                  <button
                    key={stepIdx}
                    ref={ref}
                    aria-current={status === "active" ? "step" : undefined}
                    className={cn(
                      "group flex w-full cursor-pointer items-center justify-center gap-4 rounded-large px-3 py-2.5",
                      stepClassName,
                    )}
                    onClick={() => setCurrentStep(stepIdx)}
                    {...props}
                  >
                    <div className="flex h-full items-center">
                      <LazyMotion features={domAnimation}>
                        <div className="relative">
                          <div className="flex items-center justify-center text-large font-semibold">
                            {status === "complete" ? (
                              <CheckIcon className="h-6 w-6" style={{ color: '#4F46E5' }} />
                            ) : (
                              <span style={status === 'active' ? { color: '#4F46E5' } : {}}>{stepIdx + 1}</span>
                            )}
                          </div>
                        </div>
                      </LazyMotion>
                    </div>
                    <div className="flex-1 text-left">
                      <div>
                        <div
                          className={cn(
                            "text-medium font-medium text-default-foreground transition-[color,opacity] duration-300 group-active:opacity-70",
                            {
                              "text-default-500": status === "inactive",
                            },
                          )}
                        >
                          {step.title}
                        </div>
                        <div
                          className={cn(
                            "text-tiny text-default-600 transition-[color,opacity] duration-300 group-active:opacity-70 lg:text-small",
                            {
                              "text-default-500": status === "inactive",
                            },
                          )}
                        >
                          {step.description}
                        </div>
                      </div>
                    </div>
                  </button>
                </div>
              </li>
            );
          })}
        </ol>
      </nav>
    );
  },
);

VerticalSteps.displayName = "VerticalSteps";
