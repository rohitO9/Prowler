import { Divider, Spacer } from "@nextui-org/react";
import { redirect } from "next/navigation";
import React, { Suspense } from "react";

import {
  getProviderGroupInfoById,
  getProviderGroups,
} from "@/actions/manage-groups/manage-groups";
import { getProviders } from "@/actions/providers";
import { getRoles } from "@/actions/roles";
import { FilterControls } from "@/components/filters/filter-controls";
import { AddGroupForm, EditGroupForm } from "@/components/manage-groups/forms";
import { SkeletonManageGroups } from "@/components/manage-groups/skeleton-manage-groups";
import { ColumnGroups } from "@/components/manage-groups/table";
import { DataTable } from "@/components/ui/table";
import { ProviderProps, Role, SearchParamsProps } from "@/types";

export default function ManageGroupsPage({
  searchParams,
}: {
  searchParams: SearchParamsProps;
}) {
  const searchParamsKey = JSON.stringify(searchParams);
  const providerGroupId = searchParams.groupId;

  return (
    <div className="flex flex-col gap-8 min-h-[70vh]">
      {/* Top: Form (Create or Edit) */}
      <div className="w-full flex justify-center">
        <div className="w-full max-w-xl 
         mx-auto p-4  ">
          <Suspense key={searchParamsKey} fallback={<SkeletonManageGroups />}>
            {providerGroupId ? (
              <SSRDataEditGroup searchParams={searchParams} />
            ) : (
              <div className="flex flex-col">
               
                <SSRAddGroupForm />
              </div>
            )}
          </Suspense>
        </div>
      </div>

      {/* Bottom: Table with Filters */}
      <div>
        <FilterControls />
        <Spacer y={8} />
        <h3 className="mb-4 text-sm font-bold uppercase">Provider Groups</h3>
        <Suspense key={searchParamsKey} fallback={<SkeletonManageGroups />}>
          <SSRDataTable searchParams={searchParams} />
        </Suspense>
      </div>
    </div>
  );
}

const SSRAddGroupForm = async () => {
  const providersResponse = await getProviders({ pageSize: 50 });
  const rolesResponse = await getRoles({});

  const providersData =
    providersResponse?.data?.map((provider: ProviderProps) => ({
      id: provider.id,
      name: provider.attributes.alias || provider.attributes.uid,
    })) || [];

  const rolesData =
    rolesResponse?.data?.map((role: Role) => ({
      id: role.id,
      name: role.attributes.name,
    })) || [];

  return <AddGroupForm providers={providersData} roles={rolesData} />;
};

const SSRDataEditGroup = async ({
  searchParams,
}: {
  searchParams: SearchParamsProps;
}) => {
  const providerGroupId = searchParams.groupId;

  // Redirect if no group ID is provided or if the parameter is invalid
  if (!providerGroupId || Array.isArray(providerGroupId)) {
    redirect("/manage-groups");
  }

  // Fetch the provider group details
  const providerGroupData = await getProviderGroupInfoById(providerGroupId);

  if (!providerGroupData || providerGroupData.error) {
    return <div>Provider group not found</div>;
  }

  const providersResponse = await getProviders({ pageSize: 50 });
  const rolesResponse = await getRoles({});

  const providersList =
    providersResponse?.data?.map((provider: ProviderProps) => ({
      id: provider.id,
      name: provider.attributes.alias || provider.attributes.uid,
    })) || [];

  const rolesList =
    rolesResponse?.data?.map((role: Role) => ({
      id: role.id,
      name: role.attributes.name,
    })) || [];

  const { attributes, relationships } = providerGroupData.data;

  const associatedProviders = relationships.providers?.data.map(
    (provider: ProviderProps) => {
      const matchingProvider = providersList.find(
        (p: { id: string; name: string }) => p.id === provider.id,
      );
      return {
        id: provider.id,
        name: matchingProvider?.name || "Unavailable for your role",
      };
    },
  );

  const associatedRoles = relationships.roles?.data.map((role: Role) => {
    const matchingRole = rolesList.find((r: Role) => r.id === role.id);
    return {
      id: role.id,
      name: matchingRole?.name || "Unavailable for your role",
    };
  });

  const formData = {
    name: attributes.name,
    providers: associatedProviders,
    roles: associatedRoles,
  };

  return (
    <div className="flex flex-col">
      <h1 className="mb-2 text-xl font-medium" id="getting-started">
        Edit provider group
      </h1>
      <p className="mb-5 text-small text-default-500">
        Edit the provider group to manage the providers and roles.
      </p>
      <EditGroupForm
        providerGroupId={providerGroupId}
        providerGroupData={formData}
        allProviders={providersList}
        allRoles={rolesList}
      />
    </div>
  );
};

const SSRDataTable = async ({
  searchParams,
}: {
  searchParams: SearchParamsProps;
}) => {
  const page = parseInt(searchParams.page?.toString() || "1", 10);
  const sort = searchParams.sort?.toString();
  const pageSize = parseInt(searchParams.pageSize?.toString() || "10", 10);

  // Convert filters to the correct type
  const filters: Record<string, string> = {};
  Object.entries(searchParams)
    .filter(([key]) => key.startsWith("filter["))
    .forEach(([key, value]) => {
      filters[key] = value?.toString() || "";
    });

  const query = (filters["filter[search]"] as string) || "";
  const providerGroupsData = await getProviderGroups({
    query,
    page,
    sort,
    filters,
    pageSize,
  });
  return (
    <DataTable
      columns={ColumnGroups}
      data={providerGroupsData?.data || []}
      metadata={providerGroupsData?.meta}
    />
  );
};
