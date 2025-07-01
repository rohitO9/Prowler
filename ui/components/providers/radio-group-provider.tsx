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
            <div
              className={`group flex flex-col items-center bg-white dark:bg-gray-800 p-4 rounded-lg hover:bg-yellow-200 cursor-pointer shadow-lg transition-all duration-300 w-40 h-40 ${
                field.value === "aws" ? "bg-yellow-100 dark:bg-yellow-900 border-2 border-yellow-400 dark:border-yellow-500" : ""
              }`}
              onClick={() => field.onChange("aws")}
            >
              <FaAws className="text-yellow-500 dark:text-white dark:group-hover:text-[#FF9900]" size={50} />
              <h3 className="text-lg font-semibold mt-2 text-gray-900 dark:text-white dark:group-hover:text-[#FF9900]">AWS</h3>
            </div>
            
            <div
              className={`group flex flex-col items-center bg-white dark:bg-gray-800 p-4 shadow-lg rounded-lg hover:bg-green-200 transition-all duration-300 cursor-pointer w-40 h-40 ${
                field.value === "azure" ? "bg-green-100 dark:bg-green-900 border-2 border-green-400 dark:border-green-500" : ""
              }`}
              onClick={() => field.onChange("azure")}
            >
              <FaWindows className="text-blue-600 dark:text-white dark:group-hover:text-[#0078D4]" size={50} />
              <h3 className="text-lg font-semibold mt-2 text-gray-900 dark:text-white dark:group-hover:text-[#0078D4]">Azure</h3>
            </div>
            
            <div
              className={`group flex flex-col items-center bg-white dark:bg-gray-800 p-4 shadow-lg rounded-lg transition-all duration-300 hover:bg-blue-200 cursor-pointer w-40 h-40 ${
                field.value === "gcp" ? "bg-blue-100 dark:bg-blue-900 border-2 border-blue-400 dark:border-blue-500" : ""
              }`}
              onClick={() => field.onChange("gcp")}
            >
              <FaGoogle className="text-blue-500 dark:text-white dark:group-hover:text-[#4285F4]" size={50} />
              <h3 className="text-lg font-semibold mt-2 text-gray-900 dark:text-white dark:group-hover:text-[#4285F4]">GCP</h3>
            </div>
            
            <div
              className={`group flex flex-col items-center bg-white dark:bg-gray-800 p-4 shadow-lg rounded-lg transition-all duration-300 hover:bg-purple-200 cursor-pointer w-40 h-40 ${
                field.value === "m365" ? "bg-purple-100 dark:bg-purple-900 border-2 border-purple-400 dark:border-purple-500" : ""
              }`}
              onClick={() => field.onChange("m365")}
            >
              <FaMicrosoft className="text-red-500 dark:text-white dark:group-hover:text-[#81BC06]" size={50} />
              <h3 className="text-lg font-semibold mt-2 text-gray-900 dark:text-white dark:group-hover:text-[#81BC06]">Microsoft 365</h3>
            </div>
            
            <div
              className={`group flex flex-col items-center bg-white dark:bg-gray-800 p-4 shadow-lg rounded-lg transition-all duration-300 hover:bg-indigo-200 cursor-pointer w-40 h-40 ${
                field.value === "kubernetes" ? "bg-indigo-100 dark:bg-indigo-900 border-2 border-indigo-400 dark:border-indigo-500" : ""
              }`}
              onClick={() => field.onChange("kubernetes")}
            >
              <SiKubernetes className="text-[#326CE5] dark:text-white dark:group-hover:text-[#326CE5]" size={50} />
              <h3 className="text-lg font-semibold mt-2 text-gray-900 dark:text-white dark:group-hover:text-[#326CE5]">Kubernetes</h3>
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
