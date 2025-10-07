"use client";

import { RadioGroup } from "@nextui-org/react";
import React from "react";
import { Control, Controller } from "react-hook-form";

import { CustomRadio } from "@/components/ui/custom";
import { FormMessage } from "@/components/ui/form";
import { Key, ShieldCheck } from "lucide-react";

type RadioGroupAWSViaCredentialsFormProps = {
  control: Control<any>;
  isInvalid: boolean;
  errorMessage?: string;
  onChange?: (value: string) => void;
};

export const RadioGroupAWSViaCredentialsTypeForm = ({
  control,
  isInvalid,
  errorMessage,
  onChange,
}: RadioGroupAWSViaCredentialsFormProps) => {
  return (
    <Controller
      name="awsCredentialsType"
      control={control}
      render={({ field }) => (
        <>
          <div className="flex flex-col md:flex-row gap-6 w-full">
            {/* IAM Role Option */}
            <div
              className={`group flex-1 cursor-pointer border rounded-xl p-5 transition-all duration-200 shadow-sm hover:shadow-lg ${field.value === "role" ? "border-indigo-500" : "border-gray-200"} bg-white dark:bg-prowler-blue-800`}
              tabIndex={0}
              role="button"
              aria-pressed={field.value === "role"}
              onClick={() => {
                field.onChange("role");
                if (onChange) onChange("role");
              }}
              onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { field.onChange("role"); if (onChange) onChange("role"); } }}
            >
              <div className="flex items-center gap-3">
                <ShieldCheck className="text-indigo-500" size={28} />
                <div>
                  <div className="font-semibold text-lg transition-colors duration-200 group-hover:text-indigo-400">
                    Connect assuming IAM Role
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-300 mt-1">Recommended for production and team use. Uses AWS IAM Role for secure, auditable access.</div>
                </div>
              </div>
            </div>
            {/* Credentials Option */}
            <div
              className={`group flex-1 cursor-pointer border rounded-xl p-5 transition-all duration-200 shadow-sm hover:shadow-lg ${field.value === "credentials" ? "border-indigo-500" : "border-gray-200"} bg-white dark:bg-prowler-blue-800`}
              tabIndex={0}
              role="button"
              aria-pressed={field.value === "credentials"}
              onClick={() => {
                field.onChange("credentials");
                if (onChange) onChange("credentials");
              }}
              onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { field.onChange("credentials"); if (onChange) onChange("credentials"); } }}
            >
              <div className="flex items-center gap-3">
                <Key className="text-indigo-500" size={28} />
                <div>
                  <div className="font-semibold text-lg transition-colors duration-200 group-hover:text-indigo-400">
                    Connect via Credentials
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-300 mt-1">Quick setup for testing or personal use. Uses AWS Access Key and Secret Key.</div>
                </div>
              </div>
            </div>
          </div>
          {errorMessage && (
            <FormMessage className="text-system-error dark:text-system-error mt-2">
              {errorMessage}
            </FormMessage>
          )}
        </>
      )}
    />
  );
};
