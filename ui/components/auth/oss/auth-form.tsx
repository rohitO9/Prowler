"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Icon } from "@iconify/react";
import { Button, Checkbox, Divider, Link, Tooltip } from "@nextui-org/react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { useEffect, useState } from "react";
import { z } from "zod";

import { authenticate, createNewUser } from "@/actions/auth";
import { configureAzureAD } from "@/actions/auth/azure-config";
import { AzureADLogin } from "@/components/auth/azure-ad-login";
import { useAzureAD } from "@/hooks/use-azure-ad";
import { NotificationIcon, ProwlerExtended } from "@/components/icons";
import { ThemeSwitch } from "@/components/ThemeSwitch";
import { useToast } from "@/components/ui";
import { CustomButton, CustomInput } from "@/components/ui/custom";
import {
  Form,
  FormControl,
  FormField,
  FormMessage,
} from "@/components/ui/form";
import { ApiError, authFormSchema } from "@/types";

export const AuthForm = ({
  type,
  invitationToken,
  isCloudEnv,
  googleAuthUrl,
  githubAuthUrl,
  isGoogleOAuthEnabled,
  isGithubOAuthEnabled,
  // azureAuthUrl is NOT used - Azure AD URL is fetched dynamically from database via AzureADLogin component
  host,
}: {
  type: string;
  invitationToken?: string | null;
  isCloudEnv?: boolean;
  googleAuthUrl?: string;
  githubAuthUrl?: string;
  isGoogleOAuthEnabled?: boolean;
  isGithubOAuthEnabled?: boolean;
  // azureAuthUrl?: string; // Removed - Azure AD uses dynamic config from DB
  host?: string;
}) => {
  const formSchema = authFormSchema(type);
  const router = useRouter();
  const { isConfigured: isAzureOAuthEnabled } = useAzureAD();

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      password: "",
      ...(type === "sign-up" && {
        name: "",
        company: "", // Organization
        confirmPassword: "",
        ...(invitationToken && { invitationToken }),
      }),
      ...(type === "azure-config" && {
        tenant_name: "",
        client_id: "",
        tenant_id: "",
        client_secret: "",
      }),
    },
  });

  const isLoading = form.formState.isSubmitting;
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const [isSSOMode, setIsSSOMode] = useState(false);

  // Prefill organization from localStorage on sign-in
  useEffect(() => {
    if (typeof window !== "undefined" && type === "sign-in") {
      try {
        const saved = localStorage.getItem("company");
        console.log("Setting company from localStorage:", saved);
        if (saved && !form.getValues("company")) {
          form.setValue("company", saved);
          console.log("Company field set to:", saved);
        }
      } catch (error) {
        console.error("Error setting company field:", error);
      }
    }
  }, [type, form]);

  // Check for SSO mode from URL params
  useEffect(() => {
    if (type === "sign-in") {
      const mode = searchParams?.get('mode');
      const inviteAccepted = searchParams?.get('invite_accepted');
      if (mode === 'sso' || inviteAccepted === 'true') {
        setIsSSOMode(true);
      }
    }
  }, [type, searchParams]);

  const onSubmit = async (data: z.infer<typeof formSchema>) => {
    console.log("Form submitted with data:", data);
    if (type === "sign-in") {
      console.log("Attempting sign-in with:", {
        email: data.email?.toLowerCase() || "",
        password: data.password ? "***" : "",
        company: data.company || "none"
      });
      const result = await authenticate(null, {
        email: data.email?.toLowerCase() || "",
        password: data.password || "",
        // Forward organization as company for enterprise tenant selection
        ...(data.company ? { company: data.company } : {}),
      });
      if (result?.message === "Success") {
        router.push("/home");
      } else if (result?.errors && "credentials" in result.errors) {
        const errorMessage = result.errors.credentials ?? "Incorrect email or password";
        
        // Show specific error messages based on the error type
        if (result.message === "User not found") {
          toast({
            variant: "destructive",
            title: "User Not Found",
            description: "No account found with this email address. Please check your email or sign up for a new account.",
          });
        } else if (result.message === "Access denied") {
          toast({
            variant: "destructive",
            title: "Access Denied",
            description: "You don't have access to this tenant. Please contact your administrator.",
          });
        } else if (result.message?.includes("SSO") || errorMessage?.includes("SSO") || errorMessage?.includes("Azure AD")) {
          // SSO-only user error - redirect to SSO
          toast({
            variant: "destructive",
            title: "SSO Login Required",
            description: "This account can only be accessed via Azure AD SSO. Please use the Azure AD login button below.",
          });
          // Highlight SSO button and scroll to it
          setTimeout(() => {
            const ssoButton = document.querySelector('[data-sso-button]');
            if (ssoButton) {
              ssoButton.scrollIntoView({ behavior: 'smooth', block: 'center' });
              (ssoButton as HTMLElement).style.border = '2px solid #3b82f6';
              setTimeout(() => {
                (ssoButton as HTMLElement).style.border = '';
              }, 3000);
            }
          }, 500);
        } else {
          toast({
            variant: "destructive",
            title: "Login Failed",
            description: errorMessage,
          });
        }
        
        form.setError("email", {
          type: "server",
          message: errorMessage,
        });
      } else if (result?.message === "User email is not verified") {
        router.push("/email-verification");
      } else {
        toast({
          variant: "destructive",
          title: "Oops! Something went wrong",
          description: "An unexpected error occurred. Please try again.",
        });
      }
    }

    if (type === "sign-up") {
      // Auto-detect subdomain on client-side and add to form data
      let subdomain = '';
      if (typeof window !== 'undefined') {
        const hostname = window.location.hostname;
        if (hostname.includes('localhost') && hostname !== 'localhost') {
          subdomain = hostname.split('.')[0];
          console.log('🔍 [AuthForm] Client-side detected subdomain:', subdomain);
        }
      }
      
      // Add subdomain to form data
      const formDataWithSubdomain = {
        ...data,
        subdomain: subdomain
      };
      
      // Ensure company is collected on sign-up and stored in DB via company_name
      const newUser = await createNewUser(formDataWithSubdomain, host);

      if (!newUser.errors) {
        toast({
          title: "Success!",
          description: "The user was registered successfully.",
        });
        form.reset();

        if (isCloudEnv) {
          router.push("/email-verification");
        } else {
          router.push("/sign-in");
        }
      } else {
        newUser.errors.forEach((error: ApiError) => {
          const errorMessage = error.detail;
          
          // Show specific toast notifications for common errors
          if (errorMessage.includes("already exists") || errorMessage.includes("duplicate")) {
            toast({
              variant: "destructive",
              title: "User Already Exists",
              description: "An account with this email address already exists. Please try signing in instead.",
            });
          }
          
          switch (error.source.pointer) {
            case "/data/attributes/name":
              form.setError("name", { type: "server", message: errorMessage });
              break;
            case "/data/attributes/email":
              form.setError("email", { type: "server", message: errorMessage });
              break;
            case "/data/attributes/company_name":
              form.setError("company", {
                type: "server",
                message: errorMessage,
              });
              break;
            case "/data/attributes/password":
              form.setError("password", {
                type: "server",
                message: errorMessage,
              });
              break;
            case "/data":
              form.setError("invitationToken", {
                type: "server",
                message: errorMessage,
              });
              break;
            default:
              toast({
                variant: "destructive",
                title: "Registration Failed",
                description: errorMessage,
              });
          }
        });
      }
    }

    if (type === "azure-config") {
      const result = await configureAzureAD(data);
      
      if (result?.message === "Azure AD configured successfully") {
        toast({
          title: "Success!",
          description: "Azure AD has been configured successfully.",
        });
        form.reset();
        router.push("/sign-in");
      } else if (result?.errors) {
        result.errors.forEach((error: ApiError) => {
          const errorMessage = error.detail;
          switch (error.source.pointer) {
            case "/data/attributes/tenant_name":
              form.setError("tenant_name", { type: "server", message: errorMessage });
              break;
            case "/data/attributes/client_id":
              form.setError("client_id", { type: "server", message: errorMessage });
              break;
            case "/data/attributes/tenant_id":
              form.setError("tenant_id", { type: "server", message: errorMessage });
              break;
            case "/data/attributes/client_secret":
              form.setError("client_secret", { type: "server", message: errorMessage });
              break;
            default:
              toast({
                variant: "destructive",
                title: "Configuration Failed",
                description: errorMessage,
              });
          }
        });
      } else {
        toast({
          variant: "destructive",
          title: "Configuration Failed",
          description: "An unexpected error occurred while configuring Azure AD.",
        });
      }
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden transition-colors duration-300 dark:bg-[linear-gradient(to_top,_#000000_60%,_#1a1f3c_100%,_#2d0b3c)]">
      {/* Left Section */}
      <div className="hidden w-1/2 flex-col items-center justify-center pl-20 text-black dark:text-white lg:flex transition-colors duration-300">
        {/* Top Left: VQ Logo and Cloud Security Tool text */}
        <div className="absolute top-4 left-4 flex flex-col items-center">
          <div className="relative mb-2">
            <div className="bg-gradient-to-r from-indigo-600 to-blue-600 rounded-xl w-16 h-16 flex items-center justify-center shadow-lg after:content-[''] after:absolute after:inset-0 after:rounded-xl after:-z-10 after:blur-md after:bg-gradient-to-br after:from-purple-400/40 after:to-indigo-500/30">
              <span className="text-3xl font-black text-white select-none z-10">VQ</span>
            </div>
          </div>
          <span className="text-xs text-gray-500 dark:text-gray-400 text-center w-full">Cloud Security Tool</span>
        </div>
        {/* Login Logo Image and Welcome Message */}
        <div className="mt-8 mb-6  flex flex-col items-center">
          <img
            src="/loginlogo.png"
            alt="Login Logo"
            className="w-[400px] h-[400px] object-contain"
          />
          <h2 className="mt-2 text-3xl font-bold text-center">
            Welcome to <span className="bg-gradient-to-r from-indigo-600 via-blue-600 to-indigo-900 bg-clip-text text-transparent dark:from-indigo-400 dark:via-blue-400 dark:to-indigo-600">VulneraIQ!</span>
          </h2>
          <p className="mt-4 max-w-md text-center text-lg">
            Simplify your infrastructure and compliance workflows with ease.
          </p>
        </div>
      </div>

      {/* Right Section */}
      <div className="relative flex w-full items-center justify-center px-6 lg:w-1/2 transition-colors duration-300">
        {/* Background Pattern */}
       

        <div
          className={`relative z-10 w-full shadow-md max-w-sm flex-col gap-4 rounded-large border-2 px-8 ${type === "sign-up" ? "pt-4 pb-10" : "py-10"} text-black dark:text-white md:max-w-md dark:bg-[linear-gradient(to_top,_#000000_60%,_#1a1f3c_100%,_#2d0b3c)] ${
            type === "sign-up" ? "h-[640px]" : ""
          }`}
        >
          {/* Prowler Logo */}
          
          <div className="flex items-center justify-between">
            <p className="pb-2 text-xl font-medium">
              {type === "sign-in" ? "Sign In" : type === "sign-up" ? "Sign Up" : "Configure Azure AD"}
            </p>
            <ThemeSwitch aria-label="Toggle theme" />
          </div>

          <Form {...form}>
            <form
              className="flex flex-col gap-4"
              onSubmit={form.handleSubmit(onSubmit)}
            >
              {type === "sign-up" && (
                <>
                  <CustomInput
                    control={form.control}
                    name="name"
                    type="text"
                    label="Name"
                    placeholder="Enter your name"
                    isInvalid={!!form.formState.errors.name}
                  />
                  <CustomInput
                    control={form.control}
                    name="company"
                    type="text"
                    label="Company name"
                    placeholder="Enter your company name"
                    isRequired={false}
                    isInvalid={!!form.formState.errors.company}
                  />
                </>
              )}

              {type === "azure-config" && (
                <>
                  <CustomInput
                    control={form.control}
                    name="tenant_name"
                    type="text"
                    label="Tenant Name"
                    placeholder="Enter your Tenant Name"
                    isInvalid={!!form.formState.errors.tenant_name}
                  />
                  <CustomInput
                    control={form.control}
                    name="client_id"
                    password
                    label="Client ID"
                    placeholder="Enter your Client ID"
                    isInvalid={!!form.formState.errors.client_id}
                  />
                  <CustomInput
                    control={form.control}
                    name="tenant_id"
                    password
                    label="Tenant ID"
                    placeholder="Enter your Tenant ID"
                    isInvalid={!!form.formState.errors.tenant_id}
                  />
                  <CustomInput
                    control={form.control}
                    name="client_secret"
                    password
                    label="Client Secret"
                    placeholder="Enter your Client Secret"
                    isInvalid={!!form.formState.errors.client_secret}
                  />
                </>
              )}

              {/* SSO Mode Banner for Invited Users */}
              {type === "sign-in" && isSSOMode && (
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
                  <div className="flex items-start space-x-3">
                    <Icon
                      icon="logos:microsoft-azure"
                      className="text-blue-600 dark:text-blue-400 mt-0.5"
                      width={20}
                      height={20}
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                        SSO Login Required
                      </p>
                      <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                        This account can only be accessed via Azure AD SSO. Please use the Azure AD login button below.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {(type === "sign-in" || type === "sign-up") && (
                <>
                  <CustomInput
                    control={form.control}
                    name="email"
                    type="email"
                    label="Email"
                    placeholder="Enter your email"
                    isInvalid={!!form.formState.errors.email}
                    showFormMessage={type !== "sign-in"}
                  />

                  {type === "sign-in" ? (
                    <div className={isSSOMode ? "opacity-50 pointer-events-none" : ""}>
                      <CustomInput
                        control={form.control}
                        name="password"
                        password
                        isInvalid={
                          !!form.formState.errors.password ||
                          !!form.formState.errors.email
                        }
                        isDisabled={isSSOMode}
                      />
                      {/* Hidden company field for sign-in to pass tenant context */}
                      <input
                        type="hidden"
                        {...form.register("company")}
                      />
                      {isSSOMode && (
                        <p className="text-xs text-gray-500 mt-1 ml-1">
                          Password login is disabled for invited users. Please use Azure AD SSO.
                        </p>
                      )}
                    </div>
                  ) : (
                    <CustomInput
                      control={form.control}
                      name="password"
                      password
                      isInvalid={
                        !!form.formState.errors.password ||
                        !!form.formState.errors.email
                      }
                    />
                  )}
                </>
              )}

               {type === "sign-in" && (
                <div className="flex items-center justify-between px-1 py-2">
                  <Checkbox name="remember" size="sm">
                    Remember me
                  </Checkbox>
                  <Link className="text-default-500 hover:text-indigo-500" href="#">
                    Forgot password?
                  </Link>
                </div>
              )} 
              {type === "sign-up" && (
                <>
                  <CustomInput
                    control={form.control}
                    name="confirmPassword"
                    confirmPassword
                  />
                  {invitationToken && (
                    <CustomInput
                      control={form.control}
                      name="invitationToken"
                      type="text"
                      label="Invitation Token"
                      placeholder={invitationToken}
                      defaultValue={invitationToken}
                      isRequired={false}
                      isInvalid={!!form.formState.errors.invitationToken}
                      isDisabled={invitationToken !== null && true}
                    />
                  )}

                  {process.env.NEXT_PUBLIC_IS_CLOUD_ENV === "true" && (
                    <FormField
                      control={form.control}
                      name="termsAndConditions"
                      render={({ field }) => (
                        <>
                          <FormControl>
                            <Checkbox
                              isRequired
                              className="py-4"
                              size="sm"
                              checked={field.value}
                              onChange={(e) => field.onChange(e.target.checked)}
                            >
                              I agree with the&nbsp;
                              <Link
                                href="https://prowler.com/terms-of-service/"
                                size="sm"
                                target="_blank"
                              >
                                Terms of Service
                              </Link>
                              &nbsp;of Prowler
                            </Checkbox>
                          </FormControl>
                          <FormMessage className="text-system-error dark:text-system-error" />
                        </>
                      )}
                    />
                  )}
                </>
              )}

              {type === "sign-in" && form.formState.errors?.email && (
                <div className="flex flex-row items-center text-system-error bg-red-50 dark:bg-red-900/20 p-3 rounded-lg border border-red-200 dark:border-red-800">
                  <NotificationIcon size={16} />
                  <p className="text-small ml-2 font-medium">
                    {form.formState.errors.email.message || "Invalid email or password"}
                  </p>
                </div>
              )}
              
              {type === "sign-up" && (form.formState.errors?.email || form.formState.errors?.name) && (
                <div className="flex flex-col gap-2">
                  {form.formState.errors?.email && (
                    <div className="flex flex-row items-center text-system-error bg-red-50 dark:bg-red-900/20 p-3 rounded-lg border border-red-200 dark:border-red-800">
                      <NotificationIcon size={16} />
                      <p className="text-small ml-2 font-medium">
                        {form.formState.errors.email.message}
                      </p>
                    </div>
                  )}
                  {form.formState.errors?.name && (
                    <div className="flex flex-row items-center text-system-error bg-red-50 dark:bg-red-900/20 p-3 rounded-lg border border-red-200 dark:border-red-800">
                      <NotificationIcon size={16} />
                      <p className="text-small ml-2 font-medium">
                        {form.formState.errors.name.message}
                      </p>
                    </div>
                  )}
                </div>
              )}

              <CustomButton
                type="submit"
                ariaLabel={type === "sign-in" ? "Log In" : type === "sign-up" ? "Sign Up" : "Configure Azure AD"}
                ariaDisabled={isLoading || (type === "sign-in" && isSSOMode)}
                className={`w-full bg-[#47C6F2] text-white hover:bg-[#1f497a] ${type === "sign-in" && isSSOMode ? "opacity-50 cursor-not-allowed" : ""}`}
                variant="solid"
                color="action"
                size="md"
                radius="md"
                isLoading={isLoading}
                isDisabled={isLoading || (type === "sign-in" && isSSOMode)}
              >
                {isLoading ? (
                  <span>Loading</span>
                ) : (
                  <span>
                    {type === "sign-in" && isSSOMode 
                      ? "Use Azure AD SSO Below" 
                      : type === "sign-in" 
                        ? "Log In" 
                        : type === "sign-up" 
                          ? "Sign Up" 
                          : "Configure Azure AD"}
                  </span>
                )}
              </CustomButton>
              
              {type === "azure-config" && (
                <p className="text-center mt-2 text-sm text-default-500">
                  Need help configuring Azure AD ?&nbsp;&nbsp;&nbsp;
                  <Link 
                    href="" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-primary  hover:underline"
                  >
                    View setup guide
                  </Link>
                </p>
              )}
            </form>
          </Form>

          {!invitationToken && type !== "azure-config" && (
            <>
              <div className="flex items-center gap-4 mt-2 mb-2 py-2">
                <Divider className="flex-1" />
                <p className="shrink-0 text-tiny text-default-500">OR</p>
                <Divider className="flex-1" />
              </div>
              <div className="flex flex-col gap-2">
                                 {type === "sign-in" && (
                   <Link
                     href="/azure"
                     className="w-full flex items-center justify-center gap-2 px-3 py-2 border-2 border-default-200 rounded-lg hover:bg-default-100 transition-colors"
                   >
                     <Icon
                       className="text-default-500"
                       icon="logos:microsoft-azure"
                       width={24}
                     />
                     Azure AD Status
                   </Link>
                 )}
                <Tooltip
                  content={
                    <div className="flex-inline text-small">
                      Social Login with Google is not enabled.{" "}
                      <Link
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-medium text-primary"
                      >
                        Read the docs
                      </Link>
                    </div>
                  }
                  placement="right-start"
                  shadow="sm"
                  isDisabled={isGoogleOAuthEnabled}
                  className="w-96"
                >
                  <span>
                    <Button
                      startContent={
                        <Icon icon="flat-color-icons:google" width={24} />
                      }
                      variant="bordered"
                      className="w-full"
                      as="a"
                      href={googleAuthUrl}
                      isDisabled={!isGoogleOAuthEnabled}
                    >
                      Continue with Google
                    </Button>
                  </span>
                </Tooltip>
                <Tooltip
                  content={
                    <div className="flex-inline text-small">
                      Social Login with Github is not enabled.{" "}
                      <Link
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-medium text-primary"
                      >
                        Read the docs
                      </Link>
                    </div>
                  }
                  placement="right-start"
                  shadow="sm"
                  isDisabled={isGithubOAuthEnabled}
                  className="w-96"
                >
                  <span>
                    <Button
                      startContent={
                        <Icon
                          className="text-default-500"
                          icon="fe:github"
                          width={24}
                        />
                      }
                      variant="bordered"
                      className="w-full"
                      as="a"
                      href={githubAuthUrl}
                      isDisabled={!isGithubOAuthEnabled}
                    >
                      Continue with Github
                    </Button>
                  </span>
                </Tooltip>
                <Tooltip
                  content={
                    <div className="flex-inline text-small">
                      Azure AD Login is not configured.{" "}
                      <Link
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-medium text-primary"
                      >
                        Read the docs
                      </Link>
                    </div>
                  }
                  placement="right-start"
                  shadow="sm"
                  isDisabled={isAzureOAuthEnabled}
                  className="w-96"
                >
                  <span>
                    <AzureADLogin
                      className={`w-full ${isSSOMode ? "ring-2 ring-blue-500 shadow-lg" : ""}`}
                      variant={isSSOMode ? "solid" : "bordered"}
                      disabled={!isAzureOAuthEnabled}
                      data-sso-button
                    />
                  </span>
                </Tooltip>
              </div>
            </>
          )}
          {type === "sign-in" ? (
            <p className="text-center mt-4 text-small">
              Need to create an account?&nbsp;
              <Link href="/sign-up">Sign Up</Link>
            </p>
          ) : type === "sign-up" ? (
            <p className="text-center mt-2 text-small">
              Already have an account?&nbsp;
              <Link href="/sign-in">Log In</Link>
            </p>
          ) : (
            <p className="text-center mt-2 text-small">
              Back to&nbsp;&nbsp;&nbsp;
              <Link href="/sign-in">Sign In</Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
