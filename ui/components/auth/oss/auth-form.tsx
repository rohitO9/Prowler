"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Icon } from "@iconify/react";
import { Button, Checkbox, Divider, Link, Tooltip } from "@nextui-org/react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
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
  azureAuthUrl,
}: {
  type: string;
  invitationToken?: string | null;
  isCloudEnv?: boolean;
  googleAuthUrl?: string;
  githubAuthUrl?: string;
  isGoogleOAuthEnabled?: boolean;
  isGithubOAuthEnabled?: boolean;
  azureAuthUrl?: string;
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
        company: "",
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

  const onSubmit = async (data: z.infer<typeof formSchema>) => {
    if (type === "sign-in") {
      const result = await authenticate(null, {
        email: data.email?.toLowerCase() || "",
        password: data.password || "",
      });
      if (result?.message === "Success") {
        router.push("/");
      } else if (result?.errors && "credentials" in result.errors) {
        form.setError("email", {
          type: "server",
          message: result.errors.credentials ?? "Incorrect email or password",
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
      const newUser = await createNewUser(data);

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
                title: "Oops! Something went wrong",
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
        {/* Top Left: SS Logo and Cloud Security Tool text */}
        <div className="absolute top-4 left-4 flex flex-col items-center">
          <div className="relative mb-2">
            <div className="bg-gradient-to-r from-indigo-600 to-blue-600 rounded-xl w-16 h-16 flex items-center justify-center shadow-lg after:content-[''] after:absolute after:inset-0 after:rounded-xl after:-z-10 after:blur-md after:bg-gradient-to-br after:from-purple-400/40 after:to-indigo-500/30">
              <span className="text-3xl font-black text-white select-none z-10">SS</span>
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
            Welcome to <span className="bg-gradient-to-r from-indigo-600 via-blue-600 to-indigo-900 bg-clip-text text-transparent dark:from-indigo-400 dark:via-blue-400 dark:to-indigo-600">SecureStack!</span>
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
                    <div className="">
                      <CustomInput
                        control={form.control}
                        name="password"
                        password
                        isInvalid={
                          !!form.formState.errors.password ||
                          !!form.formState.errors.email
                        }
                      />
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
                <div className="flex flex-row items-center text-system-error">
                  <NotificationIcon size={16} />
                  <p className="text-small">Invalid email or password</p>
                </div>
              )}

              <CustomButton
                type="submit"
                ariaLabel={type === "sign-in" ? "Log In" : type === "sign-up" ? "Sign Up" : "Configure Azure AD"}
                ariaDisabled={isLoading}
                className="w-full bg-[#47C6F2] text-white hover:bg-[#1f497a]"
                variant="solid"
                color="action"
                size="md"
                radius="md"
                isLoading={isLoading}
                isDisabled={isLoading}
              >
                {isLoading ? (
                  <span>Loading</span>
                ) : (
                  <span>{type === "sign-in" ? "Log In" : type === "sign-up" ? "Sign Up" : "Configure Azure AD"}</span>
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
                      className="w-full"
                      variant="bordered"
                      disabled={!isAzureOAuthEnabled}
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
