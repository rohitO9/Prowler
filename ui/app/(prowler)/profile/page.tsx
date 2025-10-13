import React, { Suspense } from "react";
import { headers } from "next/headers";
import ErrorBoundary from "@/src/components/ErrorBoundary";

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
      <ErrorBoundary>
        <Suspense fallback={<SkeletonUserInfo />}>
          <SSRDataUser />
        </Suspense>
      </ErrorBoundary>
    </ContentLayout>
  );
}

const SSRDataUser = async () => {
  const headersList = await headers();
  const host = headersList.get('host');
  const userProfile = await getUserInfo(host || undefined);
  if (!userProfile?.data) {
    return (
      <div className="flex items-center justify-center min-h-32">
        <p className="text-muted-foreground">No user data available</p>
      </div>
    );
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
  
  // Try to get tenants, but handle permission errors gracefully
  let tenants = null;
  let tenantsMap = {};
  let userTenant = null;
  
  try {
    tenants = await getAllTenants();
    if (tenants?.data) {
      tenantsMap = tenants.data.reduce(
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

      userTenant = tenants.data.find((tenant: TenantDetailData) =>
        tenant.relationships?.memberships?.data?.some(
          (membership: { id: string }) => userMembershipIds.includes(membership.id),
        ),
      );
    }
  } catch (error) {
    console.log('🔍 [Profile] Could not fetch all tenants (permission denied):', error);
    // Continue without tenants data - page will still show user info and memberships
  }

  const isOwner = isUserOwnerAndHasManageAccount(
    roleDetails,
    memberships?.data || [],
    userProfile.data.id,
  );

  return (
    <div key="profile-content" className="flex w-full flex-col gap-4">
      <UserBasicInfoCard 
        user={userProfile?.data} 
        tenantId={userTenant?.id || undefined} 
      />
      <div className="flex flex-col gap-4 lg:flex-row">
        {/* Removed RolesCard section */}
        <div className="w-full">
          <MembershipsCard
            memberships={memberships?.data || []}
            tenantsMap={tenantsMap || {}}
            isOwner={isOwner}
            roles={roleDetails || []}
            roleDetails={roleDetailsMap}
          />
        </div>
      </div>
    </div>
  );
};