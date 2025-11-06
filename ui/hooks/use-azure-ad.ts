"use client";

import { useState, useEffect } from "react";
import { getAzureADConfig, checkTrialStatus } from "@/actions/auth/azure-ad";
import { AzureADConfig } from "@/actions/auth/azure-ad";

export interface UseAzureADReturn {
  config: AzureADConfig | null;
  isLoading: boolean;
  error: string | null;
  isConfigured: boolean;
  checkTrialStatus: (email: string) => Promise<any>;
}

export const useAzureAD = (): UseAzureADReturn => {
  const [config, setConfig] = useState<AzureADConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const azureConfig = await getAzureADConfig();
        setConfig(azureConfig);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load Azure AD configuration");
      } finally {
        setIsLoading(false);
      }
    };

    loadConfig();
  }, []);

  // Check if Azure AD is configured (config exists and is active)
  const isConfigured = !!config && !!config.client_id;

  return {
    config,
    isLoading,
    error,
    isConfigured,
    checkTrialStatus,
  };
};
