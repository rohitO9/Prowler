"use client";

import { Card, CardBody, CardHeader } from "@nextui-org/react";

import { MembershipDetailData, TenantDetailData } from "@/types/users";
import { useState } from "react";
import { RolesCard } from "./roles-card";
import { CustomButton, CustomAlertModal } from "@/components/ui/custom";

import { MembershipItem } from "./membership-item";

export const MembershipsCard = ({
  memberships,
  tenantsMap,
  isOwner,
  roles,
  roleDetails,
}: {
  memberships: MembershipDetailData[];
  tenantsMap: Record<string, TenantDetailData>;
  isOwner: boolean;
  roles: any[];
  roleDetails: Record<string, any>;
}) => {
  const [isRolesOpen, setIsRolesOpen] = useState(false);
  return (
    <Card className="shadow-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-prowler-blue-400  ">
      <CardHeader className=" w-full">
        <div className="flex flex-col  w-full">
          <h4 className="w-full  text-2xl font-extrabold bg-gradient-to-r from-indigo-500 to-purple-700 bg-clip-text text-transparent">Organizations & Roles</h4>
          <p className="w-full  text-sm text-gray-500 dark:text-gray-300">
           Organizations and Active Roles assigned to this user account .
          </p>
        </div>
      </CardHeader>
      <CardBody className="pt-4">
        {/* Roles section */}
        <h5 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Roles</h5>
        <p className="text-xs text-gray-500 dark:text-gray-300 ">You can see the roles of the user by clicking the button below.</p>
        <div className="flex justify-start pl-0">
          <CustomButton
            type="button"
            ariaLabel="Show Active Roles"
            className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold px-4 py-2 rounded-md shadow hover:from-indigo-600 hover:to-purple-700 transition-colors duration-200 mt-2"
            variant="solid"
            color="primary"
            size="sm"
            onPress={() => setIsRolesOpen(true)}
          >
            Show Active Roles
          </CustomButton>
        </div>
        <CustomAlertModal
          isOpen={isRolesOpen}
          onOpenChange={setIsRolesOpen}
          title=""
          className="max-w-2xl"
        >
          <RolesCard roles={roles} roleDetails={roleDetails} />
        </CustomAlertModal>
        {/* Organizations section */}
        <h5 className="text-lg font-bold text-gray-900 dark:text-white mt-2 mb-1">Organizations</h5>
        <p className="text-xs text-gray-500 dark:text-gray-300 mb-4">
          View your associated organizations below.
        </p>
        {memberships.length === 0 ? (
          <div className="text-sm text-gray-500">No memberships found.</div>
        ) : (
          <div className="space-y-4">
            {memberships.map((membership) => {
              const tenantId = membership.relationships.tenant.data.id;
              return (
                <MembershipItem
                  key={membership.id}
                  membership={membership}
                  tenantId={tenantId}
                  tenantName={tenantsMap[tenantId]?.attributes.name}
                  isOwner={isOwner}
                  roles={roles}
                  roleDetails={roleDetails}
                />
              );
            })}
          </div>
        )}
      </CardBody>
    </Card>
  );
};
