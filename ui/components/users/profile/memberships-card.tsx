"use client";

import { Card, CardBody, CardHeader } from "@nextui-org/react";
import { Shield, Building2, Users } from "lucide-react";

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
    <Card className="shadow-xl border-0 bg-white dark:bg-gray-900">
      <CardHeader className="pb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex flex-col w-full">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900">
              <Users className="w-5 h-5 text-indigo-600 dark:text-indigo-300" />
            </div>
            <h4 className="text-2xl font-bold text-gray-900 dark:text-white">
              Organizations & Roles
            </h4>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Manage your organization memberships and view assigned roles
          </p>
        </div>
      </CardHeader>
      <CardBody className="pt-6 space-y-8">
        {/* Roles section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Shield className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                <h5 className="text-lg font-bold text-gray-900 dark:text-white">Active Roles</h5>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                View and manage your role permissions across organizations
              </p>
            </div>
          </div>
          <div className="flex justify-start">
            <CustomButton
              type="button"
              ariaLabel="Show Active Roles"
              className="bg-gradient-to-r from-indigo-500 to-blue-600 text-white font-semibold px-6 py-2.5 rounded-lg shadow-md hover:from-indigo-600 hover:to-blue-700 transition-all duration-200 hover:shadow-lg"
              variant="solid"
              color="primary"
              size="md"
              onPress={() => setIsRolesOpen(true)}
            >
              View All Roles ({roles?.length || 0})
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
        </div>

        {/* Divider */}
        <div className="border-t border-gray-200 dark:border-gray-700"></div>

        {/* Organizations section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-1">
            <Building2 className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            <h5 className="text-lg font-bold text-gray-900 dark:text-white">Organizations</h5>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
            Organizations you are a member of
          </p>
          {memberships.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-700">
              <Building2 className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">No organizations found</p>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">You're not a member of any organization yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {memberships.map((membership) => {
                // Handle nested structure for tenant ID
                // Type assertion needed for runtime properties not in type definition
                const membershipAny = membership as any;
                const tenantId = membershipAny?.relationships?.tenant?.data?.id || 
                                membershipAny?.relationships?.tenant?.id ||
                                membershipAny?.tenant_id;
                
                // Handle nested structure for tenant name
                let tenantName = 'Unknown Organization';
                if (tenantId && tenantsMap[tenantId]) {
                  const tenant = tenantsMap[tenantId] as any;
                  // Type assertion needed for nested data structures
                  tenantName = tenant?.attributes?.name || 
                              tenant?.data?.attributes?.name ||
                              tenant?.name ||
                              'Unknown Organization';
                } else if (membershipAny?.attributes?.tenant_name) {
                  tenantName = membershipAny.attributes.tenant_name;
                }
                
                console.log('🔍 [MembershipsCard] Membership:', {
                  membershipId: membership.id,
                  tenantId,
                  tenantName,
                  hasTenantInMap: !!tenantsMap[tenantId]
                });
                
                return (
                  <MembershipItem
                    key={membership.id}
                    membership={membership}
                    tenantId={tenantId || ''}
                    tenantName={tenantName}
                    isOwner={isOwner}
                    roles={roles}
                    roleDetails={roleDetails}
                  />
                );
              })}
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  );
};