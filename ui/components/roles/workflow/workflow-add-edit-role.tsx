"use client";

import { Progress, Spacer, Modal, ModalContent, ModalHeader, ModalBody, ModalFooter, useDisclosure } from "@nextui-org/react";
import { usePathname, useRouter } from "next/navigation";
import React, { useState, useEffect } from "react";
import { EditIcon, PlusIcon } from "lucide-react";

import { getRoles } from "@/actions/roles/roles";
import { CustomButton } from "@/components/ui/custom";
import { useToast } from "@/components/ui";
import { RolesProps } from "@/types";

import { VerticalSteps } from "./vertical-steps";

const steps = [
  {
    title: "Create a new role",
    description: "Enter the name of the role",
    href: "/roles/new",
  },
  {
    title: "Edit an existing role",
    description: "Update the role's details",
    href: "/roles/edit",
  },
];

export const WorkflowAddEditRole = () => {
  const pathname = usePathname();
  const router = useRouter();
  const { toast } = useToast();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [roles, setRoles] = useState<RolesProps["data"]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Calculate current step based on pathname
  const currentStepIndex = steps.findIndex((step) =>
    pathname?.endsWith(step.href),
  );
  const currentStep = currentStepIndex === -1 ? 0 : currentStepIndex;

  // Fetch roles when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchRoles();
    }
  }, [isOpen]);

  const fetchRoles = async () => {
    setIsLoading(true);
    try {
      const rolesData = await getRoles({ pageSize: 100 });
      setRoles(rolesData?.data || []);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to fetch roles. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateNewRole = () => {
    router.push("/roles/new");
  };

  const handleEditExistingRole = () => {
    onOpen();
  };

  const handleRoleSelect = (roleId: string) => {
    router.push(`/roles/edit?roleId=${roleId}`);
    onClose();
  };

  return (
    <>
      <div className="w-full flex justify-center">
        <section className="max-w-md w-full">
          <h1 className="mb-2 text-2xl font-medium text-center bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent" id="getting-started">
            Role Creation & Permissions
          </h1>
          <p className="mb-5 text-small text-default-500 text-center">
            Set up a new role and customize its permissions as needed.
          </p>
          <div className="flex justify-center w-full">
            <div className="w-full max-w-lg">
              <Progress
                classNames={{
                  base: "px-0.5 mb-5",
                  label: "text-small",
                  value: "text-small text-default-400",
                  indicator: "bg-gradient-to-r from-indigo-500 to-purple-500",
                }}
                label="Steps"
                maxValue={steps.length}
                minValue={0}
                showValueLabel={true}
                size="md"
                value={currentStep + 1}
                valueLabel={`${currentStep + 1} of ${steps.length}`}
              />
            </div>
          </div>
          <div className="flex flex-row gap-8 justify-center mt-4">
            {steps.map((step, idx) => (
              <div
                key={step.title}
                className={`rounded-xl border border-default-200 dark:border-default-50 px-6 py-4 flex flex-row items-center min-w-[272px] cursor-pointer hover:bg-default-100 dark:hover:bg-prowler-blue-800 transition-colors ${idx === currentStep ? 'bg-default-100 dark:bg-prowler-blue-800' : ''}`}
                onClick={idx === 0 ? handleCreateNewRole : handleEditExistingRole}
              >
                <div className="flex flex-col justify-center">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent text-sm">{idx + 1}.</span>
                    <span className="font-semibold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent text-sm">{step.title}</span>
                  </div>
                  <div className="text-xs text-default-500 mt-0.5 text-left">{step.description}</div>
                </div>
              </div>
            ))}
          </div>
          
        </section>
      </div>

      {/* Role Selection Modal */}
      <Modal 
        isOpen={isOpen} 
        onClose={onClose}
        size="4xl"
        scrollBehavior="inside"
        classNames={{
          base: "max-h-[80vh] dark:bg-prowler-blue-800",
          body: "p-0",
        }}
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1">
          <h3 className="text-xl font-semibold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">
  Select Role to Edit
</h3>
            <p className="text-sm text-default-500">
              Choose a role from the list below to edit its permissions and settings.
            </p>
          </ModalHeader>
          <ModalBody>
            {isLoading ? (
              <div className="flex justify-center items-center py-8">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
                  <p className="text-sm text-default-500">Loading roles...</p>
                </div>
              </div>
            ) : roles.length === 0 ? (
              <div className="flex justify-center items-center py-8">
                <div className="text-center">
                  <p className="text-sm text-default-500 mb-2">No roles found</p>
                  <p className="text-xs text-default-400">Create a new role first to edit it later.</p>
                </div>
              </div>
            ) : (
              <div className="max-h-[60vh] overflow-auto">
                <div className="grid grid-cols-1 gap-4 p-4">
                  {roles.map((role) => (
                    <div key={role.id} className="flex items-center justify-between p-4 border border-default-200 rounded-lg hover:bg-default-50">
                      <div className="flex flex-col">
                        <h4 className="font-semibold text-sm">{role.attributes.name}</h4>
                        <p className="text-xs text-default-500">
                          {role.attributes.permission_state[0].toUpperCase() + role.attributes.permission_state.slice(1).toLowerCase()} permissions • {role.relationships.users.meta.count} users
                        </p>
                      </div>
                      <CustomButton
                        ariaLabel="Edit Role"
                        onPress={() => handleRoleSelect(role.id)}
                        size="sm"
                        variant="solid"
                        color="primary"
                      >
                        Edit
                      </CustomButton>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </ModalBody>
          <ModalFooter>
            <CustomButton
              ariaLabel="Cancel"
              onPress={onClose}
              variant="bordered"
              color="transparent"
            >
              Cancel
            </CustomButton>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
};
