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
  
  // Handle nested data structures: data.data.data or data.data or data
  let userData = null;
  if (userProfile?.data?.data?.data) {
    userData = userProfile.data.data.data;
  } else if (userProfile?.data?.data) {
    userData = userProfile.data.data;
  } else if (userProfile?.data) {
    userData = userProfile.data;
  } else if (userProfile) {
    userData = userProfile;
  }
  
  if (!userData) {
    return (
      <div className="flex items-center justify-center min-h-32">
        <p className="text-muted-foreground">No user data available</p>
      </div>
    );
  }

  // Extract user ID from various possible structures
  const userId = userData.id || userData.data?.id || userProfile?.data?.id;

  const roleDetails =
    userProfile.included?.filter((item: any) => item.type === "roles") || [];

  const roleDetailsMap = roleDetails.reduce(
    (acc: Record<string, RoleDetail>, role: RoleDetail) => {
      acc[role.id] = role;
      return acc;
    },
    {} as Record<string, RoleDetail>,
  );

  const memberships = await getUserMemberships(userId);
  
  // Try to get tenants, but handle permission errors gracefully
  let tenants = null;
  let tenantsMap = {} as Record<string, TenantDetailData>;
  let userTenant = null;
  
  try {
    tenants = await getAllTenants();
    
    if (tenants?.data) {
      tenantsMap = tenants.data.reduce(
        (acc: Record<string, TenantDetailData>, tenant: TenantDetailData) => {
          // Handle nested tenant structure
          // Type assertion needed for runtime properties not in type definition
          const tenantAny = tenant as any;
          const tenantId = tenant.id || tenantAny?.data?.id || tenantAny?.attributes?.id;
          if (tenantId) {
            acc[tenantId] = tenant;
          }
          return acc;
        },
        {} as Record<string, TenantDetailData>,
      );

      const userMembershipIds =
        userData.relationships?.memberships?.data?.map(
          (membership: { id: string }) => membership.id,
        ) || [];

      userTenant = tenants.data.find((tenant: TenantDetailData) => {
        // Type assertion needed for runtime properties not in type definition
        const tenantAny = tenant as any;
        const tenantId = tenant.id || tenantAny?.data?.id || tenantAny?.attributes?.id;
        return tenant.relationships?.memberships?.data?.some(
          (membership: { id: string }) => userMembershipIds.includes(membership.id),
        );
      });
    }
  } catch (error) {
    // Continue without tenants data - page will still show user info and memberships
  }

  const isOwner = isUserOwnerAndHasManageAccount(
    roleDetails,
    memberships?.data || [],
    userId,
  );

  // Extract tenant ID from various possible structures
  const tenantId = userTenant?.id || userTenant?.data?.id || undefined;

  return (
    <div key="profile-content" className="flex w-full flex-col gap-6 max-w-7xl mx-auto">
      {/* Hero Section */}
      <UserBasicInfoCard 
        user={userData as any} 
        tenantId={tenantId} 
      />
      
      {/* Content Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Organizations & Roles */}
        <div className="lg:col-span-2">
          <MembershipsCard
            memberships={memberships?.data || []}
            tenantsMap={tenantsMap || {}}
            isOwner={isOwner}
            roles={roleDetails || []}
            roleDetails={roleDetailsMap}
          />
        </div>
        
        {/* Sidebar - Quick Stats or Additional Info */}
        <div className="lg:col-span-1">
          <div className="space-y-6">
            {/* Quick Stats Card */}
            <div className="bg-white dark:bg-gray-900 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Quick Stats</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Organizations</span>
                  <span className="text-lg font-bold text-gray-900 dark:text-white">
                    {memberships?.data?.length || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Active Roles</span>
                  <span className="text-lg font-bold text-gray-900 dark:text-white">
                    {roleDetails?.length || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Account Status</span>
                  <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200">
                    Active
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};