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

// Updated SSRDataTable component with improved error handling

const SSRDataTable = async ({
  searchParams,
}: {
  searchParams: SearchParamsProps;
}) => {
  try {
    const page = parseInt(searchParams.page?.toString() || "1", 10);
    const sort = searchParams.sort?.toString();
    const pageSize = parseInt(searchParams.pageSize?.toString() || "10", 10);

    // Extract all filter parameters
    const filters = Object.fromEntries(
      Object.entries(searchParams).filter(([key]) => key.startsWith("filter[")),
    );

    // Extract query from filters
    const query = (filters["filter[search]"] as string) || "";

    console.log('SSRDataTable: Fetching data with params:', {
      query, page, sort, filters, pageSize
    });

<<<<<<< Updated upstream
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
=======
    // Fetch invitations and roles
    const [invitationsData, rolesData] = await Promise.all([
      getInvitations({
        query,
        page,
        sort,
        filters,
        pageSize,
      }),
      getRoles({})
    ]);

    console.log('SSRDataTable: Received invitations:', invitationsData);
    console.log('SSRDataTable: Received roles:', rolesData);

    // Check for errors in invitations
    if (invitationsData?.error) {
      console.error('Invitations API error:', invitationsData.error);
      
      // Handle specific error types
      if (invitationsData.error.status === 403) {
        return (
          <div className="p-8 text-center border border-orange-200 rounded-lg bg-orange-50">
            <div className="flex flex-col items-center space-y-4">
              <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center">
                <svg 
                  className="w-8 h-8 text-orange-600" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M12 15v2m0 0v2m0-2h2m-2 0H10m4-6V9a4 4 0 00-8 0v2M7 13h10a2 2 0 012 2v4a2 2 0 01-2 2H7a2 2 0 01-2-2v-4a2 2 0 012-2z" 
                  />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-orange-800 mb-2">
                  Access Denied
                </h3>
                <p className="text-orange-700 mb-2">
                  You don't have permission to view invitations.
                </p>
                <p className="text-sm text-orange-600">
                  Please contact your administrator to request access to this feature.
                </p>
              </div>
            </div>
          </div>
        );
      }
>>>>>>> Stashed changes

      // Handle other error types (401, 404, 500, etc.)
      const getErrorMessage = (status: number) => {
        switch (status) {
          case 401:
            return {
              title: "Authentication Required",
              message: "Please log in to view invitations.",
              suggestion: "Try refreshing the page or logging in again."
            };
          case 404:
            return {
              title: "Not Found",
              message: "The invitations service could not be found.",
              suggestion: "Please try again later or contact support if the issue persists."
            };
          case 500:
            return {
              title: "Server Error",
              message: "There was a problem loading the invitations.",
              suggestion: "Please try refreshing the page or contact support if the issue continues."
            };
          default:
            return {
              title: "Error Loading Invitations",
              message: invitationsData.error.message || "An unexpected error occurred.",
              suggestion: "Please try refreshing the page."
            };
        }
      };

      const errorInfo = getErrorMessage(invitationsData.error.status);

      return (
        <div className="p-6 border border-red-200 rounded-lg bg-red-50">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <svg 
                className="w-6 h-6 text-red-600" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
                />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-red-800 font-semibold mb-1">
                {errorInfo.title}
              </h3>
              <p className="text-red-700 mb-2">
                {errorInfo.message}
              </p>
              <p className="text-sm text-red-600">
                {errorInfo.suggestion}
              </p>
              {invitationsData.error.status && (
                <p className="text-xs text-red-500 mt-2">
                  Error Code: {invitationsData.error.status}
                </p>
              )}
            </div>
          </div>
        </div>
      );
    }

    // Check for errors in roles
    if (rolesData?.error) {
      console.warn('Roles API error (continuing with empty roles):', rolesData.error);
    }

    // Rest of your existing code remains the same...
    const fixedInvitationData = invitationsData?.data || [];
    const newroles = Array.isArray(rolesData?.data)
      ? rolesData.data
      : rolesData?.data
        ? [rolesData.data]
        : [];

    console.log('SSRDataTable: Processed invitations count:', fixedInvitationData.length);
    console.log('SSRDataTable: Processed roles count:', newroles.length);

    const roleDict = newroles.reduce(
      (acc: Record<string, Role>, role: Role) => {
        const invitations = role?.relationships?.invitations?.data;
        if (Array.isArray(invitations)) {
          invitations.forEach((invitation: any) => {
            if (invitation?.id) {
              acc[invitation.id] = role;
            }
          });
        }
        return acc;
      },
      {}
    );

    const roles = Array.from(
      new Map(
        newroles
          .filter((role: { id: any; }) => role?.id)
          .map((role: Role) => [
            role.id,
            { 
              id: role.id, 
              name: role?.attributes?.name || "Unnamed Role" 
            },
          ])
      ).values(),
    );

    console.log('SSRDataTable: Generated roles dict:', Object.keys(roleDict).length, 'entries');
    console.log('SSRDataTable: Generated roles array:', roles.length, 'entries');

    const expandedInvitations = fixedInvitationData.map(
      (invitation: InvitationProps) => {
        const role = invitation?.id ? roleDict[invitation.id] : null;

        return {
          ...invitation,
          relationships: {
            ...invitation?.relationships,
            role,
          },
          roles,
        };
      },
    );

    console.log('SSRDataTable: Expanded invitations:', expandedInvitations.length);

    const expandedResponse = {
      ...invitationsData,
      data: expandedInvitations,
      roles,
    };

    if (!expandedInvitations.length) {
      return (
        <div className="p-8 text-center text-gray-500">
          <div className="flex flex-col items-center space-y-3">
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
              <svg 
                className="w-6 h-6 text-gray-400" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" 
                />
              </svg>
            </div>
            <div>
              <p className="text-gray-600 font-medium">No invitations found</p>
              {query && (
                <p className="text-sm text-gray-500 mt-1">
                  Try adjusting your search criteria or filters
                </p>
              )}
            </div>
          </div>
        </div>
      );
    }

    return (
      <DataTable
        columns={ColumnsInvitation}
        data={expandedResponse?.data || []}
        metadata={invitationsData?.meta}
      />
    );

  } catch (error) {
    console.error('SSRDataTable unexpected error:', error);
    
    return (
      <div className="p-6 border border-red-200 rounded-lg bg-red-50">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <svg 
              className="w-6 h-6 text-red-600" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.664-.833-2.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" 
              />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-red-800 font-semibold mb-1">Unexpected Error</h3>
            <p className="text-red-700 mb-2">
              Something went wrong while loading the invitations.
            </p>
            <p className="text-sm text-red-600 mb-3">
              Please try refreshing the page. If the problem continues, contact support.
            </p>
            <details className="mt-2">
              <summary className="text-sm text-red-500 cursor-pointer hover:text-red-600">
                Technical Details
              </summary>
              <pre className="text-xs bg-red-100 p-3 mt-2 rounded overflow-auto border border-red-200 max-h-32">
                {error instanceof Error ? error.message : String(error)}
              </pre>
            </details>
          </div>
        </div>
      </div>
    );
  }
};