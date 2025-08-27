import { z } from "zod";

export type AuthSocialProvider = "google" | "github" | "azure";

export const authFormSchema = (type: string) =>
  z
    .object({
      // Sign Up
      company:
        type === "sign-in" ? z.string().optional() : z.string().optional(),
      name:
        type === "sign-in" || type === "azure-config"
          ? z.string().optional()
          : z
              .string()
              .min(3, {
                message: "The name must be at least 3 characters.",
              })
              .max(20),
      confirmPassword:
        type === "sign-in" || type === "azure-config"
          ? z.string().optional()
          : z.string().min(12, {
              message: "It must contain at least 12 characters.",
            }),
      invitationToken:
        type === "sign-in" ? z.string().optional() : z.string().optional(),

      termsAndConditions:
        type === "sign-in" || process.env.NEXT_PUBLIC_IS_CLOUD_ENV !== "true"
          ? z.boolean().optional()
          : z.boolean().refine((value) => value === true, {
              message: "You must accept the terms and conditions.",
            }),

      // Azure Configuration Fields
      tenant_name:
        type === "azure-config"
          ? z
              .string()
              .min(1, "Tenant Name is required")
              .min(3, "Tenant Name must be at least 3 characters")
          : z.string().optional(),
      client_id:
        type === "azure-config"
          ? z
              .string()
              .min(1, "Client ID is required")
              .regex(
                /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/,
                "Client ID must be a valid UUID format (e.g., 12345678-1234-1234-1234-123456789012)"
              )
              .min(36, "Client ID must be exactly 36 characters")
              .max(36, "Client ID must be exactly 36 characters")
          : z.string().optional(),
      tenant_id:
        type === "azure-config"
          ? z
              .string()
              .min(1, "Tenant ID is required")
              .regex(
                /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/,
                "Tenant ID must be a valid UUID format (e.g., 12345678-1234-1234-1234-123456789012)"
              )
              .min(36, "Tenant ID must be exactly 36 characters")
              .max(36, "Tenant ID must be exactly 36 characters")
          : z.string().optional(),
      client_secret:
        type === "azure-config"
          ? z
              .string()
              .min(1, "Client Secret is required")
              .min(8, "Client Secret must be at least 8 characters")
          : z.string().optional(),

      // Fields for Sign In and Sign Up
      email: 
        type === "azure-config" 
          ? z.string().optional() 
          : z.string().email(),
      password:
        type === "azure-config"
          ? z.string().optional()
          : type === "sign-in"
          ? z.string()
          : z.string().min(12, {
              message: "It must contain at least 12 characters.",
            }),
    })
    .refine(
      (data) => type === "sign-in" || type === "azure-config" || data.password === data.confirmPassword,
      {
        message: "The password must match",
        path: ["confirmPassword"],
      },
    );
