"use client";

import React from "react";
import { Control, Controller } from "react-hook-form";
import { z } from "zod";
import { FaAws, FaGoogle, FaMicrosoft, FaWindows } from "react-icons/fa";
import { SiKubernetes } from "react-icons/si";

import { addProviderFormSchema } from "@/types";

import { FormMessage } from "../ui/form";

interface RadioGroupProviderProps {
  control: Control<z.infer<typeof addProviderFormSchema>>;
  isInvalid: boolean;
  errorMessage?: string;
}

export const RadioGroupProvider: React.FC<RadioGroupProviderProps> = ({
  control,
  isInvalid,
  errorMessage,
}) => {
  return (
    <Controller
      name="providerType"
      control={control}
      render={({ field }) => (
        <>
          <div className="flex flex-row justify-center gap-8 my-10 overflow-x-auto">
            {/* AWS - Clickable */}
            <div
              className={`group flex flex-col items-center bg-white dark:bg-gray-800 p-4 border border-default-200 rounded-lg shadow-sm hover:bg-yellow-200 cursor-pointer transition-all duration-300 w-40 h-40 ${
                field.value === "aws" ? "bg-yellow-100 dark:bg-yellow-900 border-2 border-yellow-400 dark:border-yellow-500" : ""
              }`}
              onClick={() => field.onChange("aws")}
            >
              <FaAws className="text-yellow-500 dark:text-white dark:group-hover:text-[#FF9900]" size={50} />
              <h3 className="text-lg font-semibold mt-2 text-gray-900 dark:text-white dark:group-hover:text-[#FF9900]">AWS</h3>
            </div>
            {/* GCP - Clickable */}
            <div
              className={`group flex flex-col items-center bg-white dark:bg-gray-800 p-4 border border-default-200 rounded-lg shadow-sm hover:bg-blue-200 cursor-pointer transition-all duration-300 w-40 h-40 ${
                field.value === "gcp" ? "bg-blue-100 dark:bg-blue-900 border-2 border-blue-400 dark:border-blue-500" : ""
              }`}
              onClick={() => field.onChange("gcp")}
            >
              <FaGoogle className="text-blue-500 dark:text-white dark:group-hover:text-blue-500" size={50} />
              <h3 className="text-lg font-semibold mt-2 text-gray-900 dark:text-white dark:group-hover:text-blue-500">GCP</h3>
            </div>
            {/* Kubernetes - Clickable */}
            <div
              className={`group flex flex-col items-center bg-white dark:bg-gray-800 p-4 border border-default-200 rounded-lg shadow-sm hover:bg-indigo-200 cursor-pointer transition-all duration-300 w-40 h-40 ${
                field.value === "kubernetes" ? "bg-indigo-100 dark:bg-indigo-900 border-2 border-indigo-400 dark:border-indigo-500" : ""
              }`}
              onClick={() => field.onChange("kubernetes")}
            >
              <SiKubernetes className="text-purple-500 dark:text-white dark:group-hover:text-purple-500" size={50} />
              <h3 className="text-lg font-semibold mt-2 text-gray-900 dark:text-white dark:group-hover:text-purple-500">Kubernetes</h3>
            </div>
            {/* Azure - Disabled, Coming Soon at bottom */}
            <div
              className={`group relative flex flex-col items-center bg-white dark:bg-gray-800 p-4 border border-default-200 rounded-lg shadow-sm w-40 h-40 opacity-50 cursor-not-allowed select-none transition-all duration-300`}
            >
              <FaWindows className="text-blue-600 dark:text-white" size={50} />
              <h3 className="text-lg font-semibold mt-2 text-gray-900 dark:text-white">Azure</h3>
              <div className="absolute mt-2 bottom-2 left-1/2 -translate-x-1/2 w-11/12 px-2 py-1 rounded bg-gray-300 dark:bg-gray-700 text-center">
                <span className="text-xs  font-medium text-gray-900 dark:text-gray-100">Coming Soon: Azure provider will be available shortly</span>
              </div>
            </div>
            {/* Microsoft 365 - Disabled, Coming Soon at bottom */}
            <div
              className={`group relative flex flex-col items-center bg-white dark:bg-gray-800 p-4 border border-default-200 rounded-lg shadow-sm w-40 h-40 opacity-50 cursor-not-allowed select-none transition-all duration-300`}
            >
              <FaMicrosoft className="text-red-500 dark:text-white" size={50} />
              <h3 className="text-lg font-semibold mt-2 text-gray-900 dark:text-white">Microsoft 365</h3>
              <div className="absolute mt-2 bottom-2 left-1/2 -translate-x-1/2 w-11/12 px-2 py-1 rounded bg-gray-300 dark:bg-gray-700 text-center">
                <span className="text-xs  font-medium text-gray-900 dark:text-gray-100">Coming Soon: M 365 provider will be available shortly</span>
              </div>
            </div>
           
          </div>
          {errorMessage && (
            <FormMessage className="text-system-error dark:text-system-error">
              {errorMessage}
            </FormMessage>
          )}
        </>
      )}
    />
  );
};
