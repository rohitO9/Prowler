import React, { Suspense } from "react";

import { getAllTenants } from "@/actions/users/tenants";
import { getUserInfo } from "@/actions/users/users";
import { getUserMemberships } from "@/actions/users/users";
import { ContentLayout } from "@/components/ui";
import { UserBasicInfoCard } from "@/components/users/profile";
import { MembershipsCard } from "@/components/users/profile/memberships-card";
import { RolesCard } from "@/components/users/profile/roles-card";
import { SkeletonUserInfo } from "@/components/users/profile/skeleton-user-info";
import { isUserOwnerAndHasManageAccount } from "@/lib/permissions";
import { RoleDetail, TenantDetailData } from "@/types/users";

export default async function Profile() {
  return (
    <ContentLayout title="User Profile" icon="ci:users">
      <Suspense fallback={<SkeletonUserInfo />}>
        <SSRDataUser />
      </Suspense>
    </ContentLayout>
  );
}

const SSRDataUser = async () => {
  const userProfile = await getUserInfo();
  if (!userProfile?.data) {
    return null;
  }

  const roleDetails =
    userProfile.included?.filter((item: any) => item.type === "roles") || [];

  const roleDetailsMap = roleDetails.reduce(
    (acc: Record<string, RoleDetail>, role: RoleDetail) => {
      acc[role.id] = role;
      return acc;
    },
    {} as Record<string, RoleDetail>,
  );

  const memberships = await getUserMemberships(userProfile.data.id);
  const tenants = await getAllTenants();

  const tenantsMap = tenants?.data?.reduce(
    (acc: Record<string, TenantDetailData>, tenant: TenantDetailData) => {
      acc[tenant.id] = tenant;
      return acc;
    },
    {} as Record<string, TenantDetailData>,
  );

  const userMembershipIds =
    userProfile.data.relationships?.memberships?.data?.map(
      (membership: { id: string }) => membership.id,
    ) || [];

  const userTenant = tenants?.data?.find((tenant: TenantDetailData) =>
    tenant.relationships?.memberships?.data?.some(
      (membership: { id: string }) => userMembershipIds.includes(membership.id),
    ),
  );

  const isOwner = isUserOwnerAndHasManageAccount(
    roleDetails,
    memberships?.data || [],
    userProfile.data.id,
  );

  return (
    <div className="flex w-full flex-col gap-4">
      <UserBasicInfoCard user={userProfile?.data} tenantId={userTenant?.id} />
      <div className="flex flex-col gap-4 lg:flex-row">
        {/* Removed RolesCard section */}
        <div className="w-full">
          <MembershipsCard
            memberships={memberships?.data || []}
            tenantsMap={tenantsMap}
            isOwner={isOwner}
            roles={roleDetails || []}
            roleDetails={roleDetailsMap}
          />
        </div>
      </div>
    </div>
  );
};
