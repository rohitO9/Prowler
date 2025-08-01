"use server";

import { z } from "zod";
import { apiBaseUrl } from "@/lib";
import { authFormSchema } from "@/types";

const azureConfigSchema = authFormSchema("azure-config");

export const configureAzureAD = async (
  formData: z.infer<typeof azureConfigSchema>,
) => {
  const url = new URL(`${apiBaseUrl}/azure-config`);

  const bodyData = {
    data: {
      type: "azure_configurations",
      attributes: {
        tenant_name: formData.tenant_name,
        client_id: formData.client_id,
        tenant_id: formData.tenant_id,
      },
    },
  };

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": " application/vnd.api+json ",
        Accept: " application/vnd.api+json ",
      },
      body: JSON.stringify(bodyData),
    });

    const parsedResponse = await response.json();
    if (!response.ok){
      return parsedResponse;
    }

    return {
      message: "Azure AD configured successfully",
    };
  } catch (error) {
    return {
      errors: [
        {
          source: { pointer: "" },
          detail: " Network error or server is unreachable ",
        },
      ],
    };
  }
}; 