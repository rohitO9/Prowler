"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Select, SelectItem } from "@nextui-org/react";
import { SaveIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import * as z from "zod";

import { sendInvite } from "@/actions/invitations/invitation";
import { useToast } from "@/components/ui";
import { CustomButton, CustomInput } from "@/components/ui/custom";
import { Form } from "@/components/ui/form";
import { ApiError } from "@/types";

const sendInvitationFormSchema = z.object({
  email: z.string().email("Please enter a valid email"),
  roleId: z.string().nonempty("Role is required"),
});

export type FormValues = z.infer<typeof sendInvitationFormSchema>;

export const SendInvitationForm = ({
  roles = [],
  defaultRole = "admin",
  isSelectorDisabled = false,
}: {
  roles: Array<{ id: string; name: string }>;
  defaultRole?: string;
  isSelectorDisabled: boolean;
}) => {
  const { toast } = useToast();
  const router = useRouter();

  const form = useForm<FormValues>({
    resolver: zodResolver(sendInvitationFormSchema),
    defaultValues: {
      email: "",
      roleId: isSelectorDisabled ? defaultRole : "",
    },
  });

  const isLoading = form.formState.isSubmitting;

  const onSubmitClient = async (values: FormValues) => {
    const formData = new FormData();
    formData.append("email", values.email);
    formData.append("role", values.roleId);

    try {
      const data = await sendInvite(formData);

      if (data?.errors && data.errors.length > 0) {
        data.errors.forEach((error: ApiError) => {
          const errorMessage = error.detail;
          switch (error.source.pointer) {
            case "/data/attributes/email":
              form.setError("email", {
                type: "server",
                message: errorMessage,
              });
              break;
            case "/data/relationships/roles":
              form.setError("roleId", {
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
      } else {
        const invitationId = data?.data?.id || "";
        router.push(`/invitations/check-details/?id=${invitationId}`);
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "An unexpected error occurred. Please try again.",
      });
    }
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmitClient)}
        className="flex flex-col space-y-4"
      >
        {/* Email Field */}
        <div className="w-full flex justify-center">
          <div className="flex flex-row gap-4 w-full max-w-2xl">
            <div className="w-full max-w-xs">
              <CustomInput
                control={form.control}
                name="email"
                type="email"
                label="Email"
                labelPlacement="inside"
                placeholder="Enter the email address"
                variant="bordered"
                isRequired
                isInvalid={!!form.formState.errors.email}
              />
            </div>
            <div className="w-full max-w-xs">
              <Controller
                name="roleId"
                control={form.control}
                render={({ field }) => (
                  <>
                    <Select
                      {...field}
                      label="Role"
                      placeholder="Select a role"
                      classNames={{
                        selectorIcon: "right-2",
                      }}
                      variant="bordered"
                      isDisabled={isSelectorDisabled}
                      selectedKeys={[field.value]}
                      onSelectionChange={(selected) =>
                        field.onChange(selected?.currentKey || "")
                      }
                    >
                      {isSelectorDisabled ? (
                        <SelectItem key={defaultRole}>{defaultRole}</SelectItem>
                      ) : (
                        roles.map((role) => (
                          <SelectItem key={role.id}>{role.name}</SelectItem>
                        ))
                      )}
                    </Select>
                    {form.formState.errors.roleId && (
                      <p className="mt-2 text-sm text-red-600">
                        {form.formState.errors.roleId.message}
                      </p>
                    )}
                  </>
                )}
              />
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex w-full justify-center">
          <CustomButton
            type="submit"
            ariaLabel="Send Invitation"
            className="w-40 mx-auto"
            variant="solid"
            color="action"
            size="lg"
            isLoading={isLoading}
            startContent={!isLoading && <SaveIcon size={24} />}
          >
            {isLoading ? <>Loading</> : <span>Send Invitation</span>}
          </CustomButton>
        </div>
      </form>
    </Form>
  );
};
