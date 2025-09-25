import { Spacer } from "@nextui-org/react";
import React, { Suspense } from "react";

import { getInvitations } from "@/actions/invitations/invitation";
import { getRoles } from "@/actions/roles";
import { FilterControls } from "@/components/filters";
import { filterInvitations } from "@/components/filters/data-filters";
import { SendInvitationButton } from "@/components/invitations";
import {
  ColumnsInvitation,
  SkeletonTableInvitation,
} from "@/components/invitations/table";
import { ContentLayout } from "@/components/ui";
import { DataTable, DataTableFilterCustom } from "@/components/ui/table";
import { InvitationProps, Role, SearchParamsProps } from "@/types";

export default async function Invitations({
  searchParams,
}: {
  searchParams: SearchParamsProps;
}) {
  const searchParamsKey = JSON.stringify(searchParams || {});

  return (
    <ContentLayout title="Invitations" icon="ci:users">
      <FilterControls search />
      <Spacer y={8} />
      <SendInvitationButton />
      <Spacer y={4} />
      <DataTableFilterCustom filters={filterInvitations || []} />
      <Spacer y={8} />

      <Suspense key={searchParamsKey} fallback={<SkeletonTableInvitation />}>
        <SSRDataTable searchParams={searchParams} />
      </Suspense>
    </ContentLayout>
  );
}

const SSRDataTable = async ({
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

  // Fetch invitations and roles
  const invitationsData = await getInvitations({
    query,
    page,
    sort,
    filters,
    pageSize,
  });
  const rolesData = await getRoles({});

  const fixedInvationData = Array.isArray(invitationsData.data) ? invitationsData.data : invitationsData?.data ? [invitationsData.data] : [];

  const newroles = Array.isArray(rolesData?.data)
  ? rolesData.data
  : rolesData?.data
  ? [rolesData.data] // wrap single object in array
  : [];

const roleDict = newroles.reduce(
  (acc: Record<string, Role>, role: Role) => {
    role.relationships?.invitations?.data?.forEach((invitation: any) => {
      acc[invitation.id] = role;
    });
    return acc;
  },
  {}
);


  // Generate the array of roles with all the roles available
  const roles = Array.from(
    new Map(
      (newroles?.data || []).map((role: Role) => [
        role.id,
        { id: role.id, name: role.attributes?.name || "Unnamed Role" },
      ]),
    ).values(),
  );

  // Expand the invitations
  const expandedInvitations = fixedInvationData?.data?.map(
    (invitation: InvitationProps) => {
      const role = roleDict[invitation.id];

      return {
        ...invitation,
        relationships: {
          ...invitation.relationships,
          role,
        },
        roles, // Include all roles here for each invitation
      };
    },
  );

  // Create the expanded response
  const expandedResponse = {
    ...invitationsData,
    data: expandedInvitations,
    roles,
  };

  return (
    <DataTable
      columns={ColumnsInvitation}
      data={expandedResponse?.data || []}
      metadata={invitationsData?.meta}
    />
  );
};
