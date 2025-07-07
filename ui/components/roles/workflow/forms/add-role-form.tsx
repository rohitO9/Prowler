"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Checkbox, Divider, Tooltip } from "@nextui-org/react";
import clsx from "clsx";
import { InfoIcon, SaveIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { addRole } from "@/actions/roles/roles";
import { useToast } from "@/components/ui";
import {
  CustomButton,
  CustomDropdownSelection,
  CustomInput,
} from "@/components/ui/custom";
import { Form } from "@/components/ui/form";
import { permissionFormFields } from "@/lib";
import { addRoleFormSchema, ApiError } from "@/types";

type FormValues = z.infer<typeof addRoleFormSchema>;

export const AddRoleForm = ({
  groups,
}: {
  groups: { id: string; name: string }[];
}) => {
  const { toast } = useToast();
  const router = useRouter();

  const form = useForm<FormValues>({
    resolver: zodResolver(addRoleFormSchema),
    defaultValues: {
      name: "",
      manage_users: false,
      manage_providers: false,
      manage_scans: false,
      unlimited_visibility: false,
      groups: [],
      ...(process.env.NEXT_PUBLIC_IS_CLOUD_ENV === "true" && {
        manage_billing: false,
      }),
    },
  });

  const { watch, setValue } = form;

  const manageProviders = watch("manage_providers");
  const unlimitedVisibility = watch("unlimited_visibility");

  useEffect(() => {
    if (manageProviders && !unlimitedVisibility) {
      setValue("unlimited_visibility", true, {
        shouldValidate: true,
        shouldDirty: true,
        shouldTouch: true,
      });
    }
  }, [manageProviders, unlimitedVisibility, setValue]);

  const isLoading = form.formState.isSubmitting;

  const onSelectAllChange = (checked: boolean) => {
    const permissions = [
      "manage_users",
      "manage_account",
      "manage_billing",
      "manage_providers",
      // "manage_integrations",
      "manage_scans",
      "unlimited_visibility",
    ];
    permissions.forEach((permission) => {
      form.setValue(permission as keyof FormValues, checked, {
        shouldValidate: true,
        shouldDirty: true,
        shouldTouch: true,
      });
    });
  };

  const onSubmitClient = async (values: FormValues) => {
    const formData = new FormData();

    formData.append("name", values.name);
    formData.append("manage_users", String(values.manage_users));
    formData.append("manage_providers", String(values.manage_providers));
    formData.append("manage_scans", String(values.manage_scans));
    formData.append("manage_account", String(values.manage_account));
    formData.append(
      "unlimited_visibility",
      String(values.unlimited_visibility),
    );

    // Conditionally append manage_account and manage_billing
    if (process.env.NEXT_PUBLIC_IS_CLOUD_ENV === "true") {
      formData.append("manage_billing", String(values.manage_billing));
    }

    if (values.groups && values.groups.length > 0) {
      values.groups.forEach((group) => {
        formData.append("groups[]", group);
      });
    }

    try {
      const data = await addRole(formData);

      if (data?.errors && data.errors.length > 0) {
        data.errors.forEach((error: ApiError) => {
          const errorMessage = error.detail;
          switch (error.source.pointer) {
            case "/data/attributes/name":
              form.setError("name", {
                type: "server",
                message: errorMessage,
              });
              break;
            default:
              toast({
                variant: "destructive",
                title: "Error",
                description: errorMessage,
              });
          }
        });
      } else {
        toast({
          title: "Role Added",
          description: "The role was added successfully.",
        });
        router.push("/roles");
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
        className="px-6 sm:p-10 flex flex-col gap-8 w-full max-w-4xl mx-auto"
      >
        <div className="w-full max-w-xl mx-auto">
          <CustomInput
            control={form.control}
            name="name"
            type="text"
            label="Role Name"
            labelPlacement="inside"
            placeholder="Enter role name"
            variant="bordered"
            isRequired
            isInvalid={!!form.formState.errors.name}
          />
        </div>

        <div className="flex flex-col sm:flex-row gap-10">
          {/* Admin Permissions Section */}
          <div className="flex-1 flex flex-col gap-4">
            <span className="text-xl font-semibold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">Admin Permissions</span>
            <Checkbox
              isSelected={permissionFormFields.every((perm) =>
                form.watch(perm.field as keyof FormValues),
              )}
              onChange={(e) => onSelectAllChange(e.target.checked)}
              classNames={{
                label: "text-small",
                wrapper: "checkbox-update",
              }}
            >
              Grant all admin permissions
            </Checkbox>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {permissionFormFields
                .filter(
                  (permission) =>
                    permission.field !== "manage_billing" ||
                    process.env.NEXT_PUBLIC_IS_CLOUD_ENV === "true",
                )
                .map(({ field, label, description }) => (
                  <div key={field} className="flex items-center gap-2">
                    <Checkbox
                      {...form.register(field as keyof FormValues)}
                      isSelected={!!form.watch(field as keyof FormValues)}
                      classNames={{
                        label: "text-small",
                        wrapper: "checkbox-update",
                      }}
                    >
                      {label}
                    </Checkbox>
                    <Tooltip content={description} placement="right">
                      <div className="flex w-fit items-center justify-center">
                        <InfoIcon
                          className={clsx(
                            "cursor-pointer text-default-400 group-data-[selected=true]:text-foreground",
                          )}
                          aria-hidden={"true"}
                          width={16}
                        />
                      </div>
                    </Tooltip>
                  </div>
                ))}
            </div>
          </div>

          {/* Groups and Account Visibility Section */}
          {!unlimitedVisibility && (
            <div className="flex-1 flex flex-col gap-4">
              <span className="text-xl font-semibold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">
                Groups and Account Visibility
              </span>
              <p className="text-small font-medium text-default-700">
                Select the groups this role will have access to. If no groups are
                selected and unlimited visibility is not enabled, the role will
                not have access to any accounts.
              </p>
              <Controller
                name="groups"
                control={form.control}
                render={({ field }) => (
                  <CustomDropdownSelection
                    label="Select Groups"
                    name="groups"
                    values={groups}
                    selectedKeys={field.value || []}
                    onChange={(name, selectedValues) =>
                      field.onChange(selectedValues)
                    }
                  />
                )}
              />
              {form.formState.errors.groups && (
                <p className="mt-2 text-sm text-red-600">
                  {form.formState.errors.groups.message}
                </p>
              )}
            </div>
          )}
        </div>

        <div className="flex w-full justify-center sm:justify-end gap-4 ">
          <CustomButton
            type="submit"
            ariaLabel="Add Role"
            className="w-full sm:w-1/3"
            variant="solid"
            color="action"
            size="lg"
            isLoading={isLoading}
            startContent={!isLoading && <SaveIcon size={24} />}
          >
            {isLoading ? <>Loading</> : <span>Add Role</span>}
          </CustomButton>
        </div>
      </form>
    </Form>
  );
};
