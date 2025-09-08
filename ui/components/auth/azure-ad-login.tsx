"use client";

import { useState } from "react";
import { Button } from "@nextui-org/react";
import { Icon } from "@iconify/react";
import { getAzureADLoginUrl } from "@/actions/auth/azure-ad";
import { useToast } from "@/components/ui";

interface AzureADLoginProps {
  className?: string;
  variant?: "solid" | "bordered" | "light" | "flat" | "faded" | "shadow" | "ghost";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  children?: React.ReactNode;
}

export const AzureADLogin = ({
  className = "",
  variant = "bordered",
  size = "md",
  disabled = false,
  children,
}: AzureADLoginProps) => {
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handleAzureADLogin = async () => {
    setIsLoading(true);
    
    try {
      const loginUrl = await getAzureADLoginUrl();
      
      if (!loginUrl) {
        toast({
          variant: "destructive",
          title: "Azure AD Not Configured",
          description: "Azure AD authentication is not properly configured. Please contact your administrator.",
        });
        return;
      }

      // Redirect to Azure AD login
      window.location.href = loginUrl;
    } catch (error) {
      console.error("Azure AD login error:", error);
      toast({
        variant: "destructive",
        title: "Login Failed",
        description: "Failed to initiate Azure AD login. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Button
      startContent={
        <Icon
          className="text-default-500"
          icon="logos:microsoft-azure"
          width={24}
        />
      }
      variant={variant}
      size={size}
      className={className}
      onClick={handleAzureADLogin}
      isLoading={isLoading}
      isDisabled={disabled || isLoading}
    >
      {children || "Continue with Azure AD"}
    </Button>
  );
};

export default AzureADLogin;
