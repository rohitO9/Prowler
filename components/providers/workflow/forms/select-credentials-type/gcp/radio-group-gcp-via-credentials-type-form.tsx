"use client";

import { RadioGroup } from "@nextui-org/react";
import React from "react";
import { Control, Controller } from "react-hook-form";

import { CustomRadio } from "@/components/ui/custom";
import { FormMessage } from "@/components/ui/form";
import { Key, ShieldCheck } from "lucide-react";
import { SiGooglecloud } from "react-icons/si";

type RadioGroupAWSViaCredentialsFormProps = {
  control: Control<any>;
  isInvalid: boolean;
  errorMessage?: string;
  onChange?: (value: string) => void;
};

export const RadioGroupGCPViaCredentialsTypeForm = ({
  control,
  isInvalid,
  errorMessage,
  onChange,
}: RadioGroupAWSViaCredentialsFormProps) => {
  return (
    <Controller
      name="gcpCredentialsType"
      control={control}
      render={({ field }) => (
        <>
          <div className="flex flex-col md:flex-row gap-6 w-full">
            {/* Service Account Key Option */}
            <div
              className={`group flex-1 cursor-pointer border rounded-xl p-5 transition-all duration-200 shadow-sm hover:shadow-lg ${field.value === "service-account" ? "border-blue-500" : "border-gray-200"} bg-white dark:bg-prowler-blue-800`}
              tabIndex={0}
              role="button"
              aria-pressed={field.value === "service-account"}
              onClick={() => {
                field.onChange("service-account");
                if (onChange) onChange("service-account");
              }}
              onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { field.onChange("service-account"); if (onChange) onChange("service-account"); } }}
            >
              <div className="flex items-center gap-3">
                <SiGooglecloud className="text-indigo-500" size={28} />
                <div>
                  <div className="font-semibold text-lg transition-colors duration-200 group-hover:text-indigo-500">
                    Connect using Service Account Key
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-300 mt-1">Recommended for production and team use. Uses a GCP Service Account Key JSON for secure, auditable access.</div>
                </div>
              </div>
            </div>
            {/* Application Default Credentials Option */}
            <div
              className={`group flex-1 cursor-pointer border rounded-xl p-5 transition-all duration-200 shadow-sm hover:shadow-lg ${field.value === "credentials" ? "border-blue-500" : "border-gray-200"} bg-white dark:bg-prowler-blue-800`}
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
                  <div className="font-semibold text-lg transition-colors duration-200 group-hover:text-indigo-500">
                    Connect via Application Default Credentials
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-300 mt-1">Quick setup for testing or personal use. Uses GCP Application Default Credentials from your environment.</div>
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
