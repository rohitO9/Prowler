import { Suspense } from "react";
import { Spacer } from "@nextui-org/react";

import { getAdminUsers } from "@/actions/admin/admin-user-management";
import { getAdminRoles } from "@/actions/admin/admin-user-management";
import { ContentLayout } from "@/components/ui";
import { AdminUserManagement } from "@/components/admin/admin-user-management";
import { SearchParamsProps } from "@/types";
import { Users as UsersIcon } from "lucide-react";

export default async function AdminUsers({
  searchParams,
}: {
  searchParams: SearchParamsProps;
}) {
  const searchParamsKey = JSON.stringify(searchParams || {});

  return (
    <ContentLayout title="Admin - User Management" icon="ci:users">
      <div className="flex w-full justify-center mb-8">
        <div className="max-w-xl w-full rounded-xl bg-background">
          <div className="flex flex-col items-center mb-6">
            <span className="bg-blue-100 text-blue-700 rounded-full p-3 mb-2">
              <UsersIcon size={40} />
            </span>
            <h2 className="text-2xl font-bold mt-1 bg-gradient-to-r from-blue-500 to-indigo-500 bg-clip-text text-transparent">
              Admin User Management
            </h2>
            <p className="text-gray-500 text-sm text-center">
              Manage users, assign roles, and control permissions for your organization.
            </p>
          </div>
        </div>
      </div>

      <Suspense key={searchParamsKey} fallback={<AdminUserManagementSkeleton />}>
        <SSRAdminUserManagement searchParams={searchParams} />
      </Suspense>
    </ContentLayout>
  );
}

const SSRAdminUserManagement = async ({
  searchParams,
}: {
  searchParams: SearchParamsProps;
}) => {
  const page = parseInt(searchParams.page?.toString() || "1", 10);
  const sort = searchParams.sort?.toString();
  const pageSize = parseInt(searchParams.pageSize?.toString() || "10", 10);

  // Extract all filter parameters
  const filters = Object.fromEntries(
    Object.entries(searchParams).filter(([key]) => key.startsWith("filter[")),
  );

  // Extract query from filters
  const query = (filters["filter[search]"] as string) || "";

  const [usersData, rolesData] = await Promise.all([
    getAdminUsers({ query, page, sort, filters, pageSize }),
    getAdminRoles(),
  ]);

  const users = usersData?.users || [];
  const roles = rolesData?.roles || [];

  const handleRefresh = async () => {
    // This will be handled by the client component
    window.location.reload();
  };

  return (
    <AdminUserManagement
      users={users}
      roles={roles}
      onRefresh={handleRefresh}
    />
  );
};

const AdminUserManagementSkeleton = () => {
  return (
    <div className="space-y-6">
      {/* Header Skeleton */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-gray-200 rounded-lg animate-pulse">
            <div className="h-6 w-6 bg-gray-300 rounded" />
          </div>
          <div>
            <div className="h-8 w-48 bg-gray-200 rounded animate-pulse mb-2" />
            <div className="h-4 w-64 bg-gray-200 rounded animate-pulse" />
          </div>
        </div>
        <div className="flex space-x-2">
          <div className="h-10 w-32 bg-gray-200 rounded animate-pulse" />
          <div className="h-10 w-20 bg-gray-200 rounded animate-pulse" />
        </div>
      </div>

      {/* Table Skeleton */}
      <div className="border rounded-lg">
        <div className="p-6 border-b">
          <div className="h-6 w-24 bg-gray-200 rounded animate-pulse" />
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
                <div className="h-4 w-32 bg-gray-200 rounded animate-pulse" />
                <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
                <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
                <div className="h-4 w-28 bg-gray-200 rounded animate-pulse" />
                <div className="h-8 w-24 bg-gray-200 rounded animate-pulse ml-auto" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
