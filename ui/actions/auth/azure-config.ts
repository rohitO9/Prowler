"use server";

import { z } from "zod";
import { apiBaseUrl } from "@/lib";
import { authFormSchema } from "@/types";

const azureConfigSchema = authFormSchema("azure-config");

export const configureAzureAD = async (
  formData: z.infer<typeof azureConfigSchema>,
) => {
  const url = new URL(`${apiBaseUrl}/tokens/azure/config`);

  const bodyData = {
    tenant_name: formData.tenant_name,
    client_id: formData.client_id,
    tenant_id: formData.tenant_id,
    client_secret: (formData as any).client_secret,
    redirect_uri: process.env.AZURE_AD_REDIRECT_URI || "",
    scopes: [
      "openid",
      "profile",
      "email",
      "offline_access",
      "User.Read",
      "GroupMember.Read.All",
    ],
  };

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
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