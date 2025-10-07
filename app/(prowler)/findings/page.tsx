import { Spacer } from "@nextui-org/react";
import React, { Suspense } from "react";

import {
  getFindings,
  getLatestFindings,
  getLatestMetadataInfo,
  getMetadataInfo,
} from "@/actions/findings";
import { getProviders } from "@/actions/providers";
import { getScans } from "@/actions/scans";
import { filterFindings } from "@/components/filters/data-filters";
import { FilterControls } from "@/components/filters/filter-controls";
import {
  ColumnFindings,
  SkeletonTableFindings,
} from "@/components/findings/table";
import { ContentLayout } from "@/components/ui";
import { DataTable, DataTableFilterCustom } from "@/components/ui/table";
import {
  createDict,
  createScanDetailsMapping,
  extractFiltersAndQuery,
  extractSortAndKey,
  hasDateOrScanFilter,
} from "@/lib";
import {
  createProviderDetailsMapping,
  extractProviderUIDs,
} from "@/lib/provider-helpers";
import { ScanProps } from "@/types";
import { FindingProps, SearchParamsProps } from "@/types/components";
import { DashboardSummary } from "@/components/findings/table/dashboard-summary";

export default async function Findings({
  searchParams,
}: {
  searchParams: SearchParamsProps;
}) {
  const { searchParamsKey, encodedSort } = extractSortAndKey(searchParams);
  const { filters, query } = extractFiltersAndQuery(searchParams);

  // Check if the searchParams contain any date or scan filter
  const hasDateOrScan = hasDateOrScanFilter(searchParams);

  const [metadataInfoData, providersData, scansData] = await Promise.all([
    (hasDateOrScan ? getMetadataInfo : getLatestMetadataInfo)({
      query,
      sort: encodedSort,
      filters,
    }),
    getProviders({ pageSize: 50 }),
    getScans({ pageSize: 50 }),
  ]);

  // Extract unique regions and services from the new endpoint
  const uniqueRegions = metadataInfoData?.data?.attributes?.regions || [];
  const uniqueServices = metadataInfoData?.data?.attributes?.services || [];
  const uniqueResourceTypes =
    metadataInfoData?.data?.attributes?.resource_types || [];

  // Extract provider UIDs and details using helper functions
  const providerUIDs = providersData ? extractProviderUIDs(providersData) : [];
  const providerDetails = providersData
    ? createProviderDetailsMapping(providerUIDs, providersData)
    : [];

  // Update the Provider UID filter
  const updatedFilters = filterFindings.map((filter) => {
    if (filter.key === "provider_uid__in") {
      return {
        ...filter,
        values: providerUIDs,
        valueLabelMapping: providerDetails,
      };
    }
    return filter;
  });

  // Extract scan UUIDs with "completed" state and more than one resource
  const completedScans = scansData?.data?.filter(
    (scan: ScanProps) =>
      scan.attributes.state === "completed" &&
      scan.attributes.unique_resource_count > 1,
  );

  const completedScanIds =
    completedScans?.map((scan: ScanProps) => scan.id) || [];

  const scanDetails = createScanDetailsMapping(completedScans, providersData);

  // After fetching and expanding findings data for the table, reuse it for the dashboard summary
  // expandedFindings is already created in SSRDataTable, but we need to fetch it here for the summary as well

  // Fetch findings data for the summary (first page, large pageSize for accuracy)
  const page = 1;
  const pageSize = 1000; // Get more data for accurate dashboard stats
  const defaultSort = "severity,status,-inserted_at";
  const { encodedSort: encodedSortForSummary } = extractSortAndKey({
    ...searchParams,
    sort: searchParams.sort ?? defaultSort,
  });
  const { filters: filtersForSummary, query: queryForSummary } = extractFiltersAndQuery(searchParams);
  const hasDateOrScanForSummary = hasDateOrScanFilter(searchParams);
  const fetchFindingsForSummary = hasDateOrScanForSummary ? getFindings : getLatestFindings;
  const findingsDataForSummary = await fetchFindingsForSummary({
    query: queryForSummary,
    page,
    sort: encodedSortForSummary,
    filters: filtersForSummary,
    pageSize,
  });
  const resourceDictForSummary = createDict("resources", findingsDataForSummary);
  const scanDictForSummary = createDict("scans", findingsDataForSummary);
  const providerDictForSummary = createDict("providers", findingsDataForSummary);
  const expandedFindingsForSummary = findingsDataForSummary?.data
    ? findingsDataForSummary.data.map((finding: FindingProps) => {
        const scan = scanDictForSummary[finding.relationships?.scan?.data?.id];
        const resource = resourceDictForSummary[finding.relationships?.resources?.data?.[0]?.id];
        const provider = providerDictForSummary[scan?.relationships?.provider?.data?.id];
        return {
          ...finding,
          relationships: { scan, resource, provider },
        };
      })
    : [];

  // No separate full counts needed; metrics will reflect current table data directly

  // Get table data for the dashboard
  const tablePage = parseInt(searchParams.page?.toString() || "1", 10);
  const tablePageSize = parseInt(searchParams.pageSize?.toString() || "10", 10);
  const tableDefaultSort = "severity,status,-inserted_at";
  const { encodedSort: tableEncodedSort } = extractSortAndKey({
    ...searchParams,
    sort: searchParams.sort ?? tableDefaultSort,
  });
  const { filters: tableFilters, query: tableQuery } = extractFiltersAndQuery(searchParams);
  const tableHasDateOrScan = hasDateOrScanFilter(searchParams);
  const tableFetchFindings = tableHasDateOrScan ? getFindings : getLatestFindings;
  const tableFindingsData = await tableFetchFindings({
    query: tableQuery,
    page: tablePage,
    sort: tableEncodedSort,
    filters: tableFilters,
    pageSize: tablePageSize,
  });

  // Create dictionaries for table data
  const tableResourceDict = createDict("resources", tableFindingsData);
  const tableScanDict = createDict("scans", tableFindingsData);
  const tableProviderDict = createDict("providers", tableFindingsData);

  // Expand table findings
  const expandedTableFindings = tableFindingsData?.data
    ? tableFindingsData.data.map((finding: FindingProps) => {
        const scan = tableScanDict[finding.relationships?.scan?.data?.id];
        const resource = tableResourceDict[finding.relationships?.resources?.data?.[0]?.id];
        const provider = tableProviderDict[scan?.relationships?.provider?.data?.id];
        return {
          ...finding,
          relationships: { scan, resource, provider },
        };
      })
    : [];

  // Create the expanded table response
  const expandedTableResponse = {
    ...tableFindingsData,
    data: expandedTableFindings,
  };

  // Aggregate stats across ALL filtered entries using small count queries
  // These mirror the table filters and compute counts beyond the current page
  const filtersWithoutStatus = Object.fromEntries(
    Object.entries(tableFilters || {}).filter(([key]) => !key.includes("filter[status__in]")),
  );

  const statusFilterRaw = (tableFilters || {})["filter[status__in]"] as string | undefined;
  const selectedStatuses = statusFilterRaw
    ? String(statusFilterRaw)
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean)
    : undefined;

  // Build status-specific promises respecting current selection
  const passPromise = selectedStatuses
    ? (selectedStatuses.includes("PASS")
        ? tableFetchFindings({ query: tableQuery, page: 1, sort: tableEncodedSort, filters: { ...tableFilters, "filter[status__in]": "PASS" }, pageSize: 1 })
        : Promise.resolve(undefined))
    : tableFetchFindings({ query: tableQuery, page: 1, sort: tableEncodedSort, filters: { ...filtersWithoutStatus, "filter[status__in]": "PASS" }, pageSize: 1 });

  const failPromise = selectedStatuses
    ? (selectedStatuses.includes("FAIL")
        ? tableFetchFindings({ query: tableQuery, page: 1, sort: tableEncodedSort, filters: { ...tableFilters, "filter[status__in]": "FAIL" }, pageSize: 1 })
        : Promise.resolve(undefined))
    : tableFetchFindings({ query: tableQuery, page: 1, sort: tableEncodedSort, filters: { ...filtersWithoutStatus, "filter[status__in]": "FAIL" }, pageSize: 1 });

  const manualPromise = selectedStatuses
    ? (selectedStatuses.includes("MANUAL")
        ? tableFetchFindings({ query: tableQuery, page: 1, sort: tableEncodedSort, filters: { ...tableFilters, "filter[status__in]": "MANUAL" }, pageSize: 1 })
        : Promise.resolve(undefined))
    : tableFetchFindings({ query: tableQuery, page: 1, sort: tableEncodedSort, filters: { ...filtersWithoutStatus, "filter[status__in]": "MANUAL" }, pageSize: 1 });

  const [totalResp, passResp, failResp, manualResp, criticalResp, highResp, mediumResp, lowResp] = await Promise.all([
    tableFetchFindings({ query: tableQuery, page: 1, sort: tableEncodedSort, filters: { ...tableFilters }, pageSize: 1 }),
    passPromise,
    failPromise,
    manualPromise,
    tableFetchFindings({ query: tableQuery, page: 1, sort: tableEncodedSort, filters: { ...tableFilters, "filter[severity__in]": "critical" }, pageSize: 1 }),
    tableFetchFindings({ query: tableQuery, page: 1, sort: tableEncodedSort, filters: { ...tableFilters, "filter[severity__in]": "high" }, pageSize: 1 }),
    tableFetchFindings({ query: tableQuery, page: 1, sort: tableEncodedSort, filters: { ...tableFilters, "filter[severity__in]": "medium" }, pageSize: 1 }),
    tableFetchFindings({ query: tableQuery, page: 1, sort: tableEncodedSort, filters: { ...tableFilters, "filter[severity__in]": "low" }, pageSize: 1 }),
  ]);

  const totalCount = totalResp?.meta?.pagination?.count ?? 0;
  const passedCount = passResp?.meta?.pagination?.count ?? 0;
  const failedCount = failResp?.meta?.pagination?.count ?? 0;
  const manualCount = manualResp?.meta?.pagination?.count ?? 0;

  const aggregateStats = {
    total: totalCount,
    passed: passedCount,
    failed: failedCount,
    manual: manualCount,
    critical: criticalResp?.meta?.pagination?.count ?? 0,
    high: highResp?.meta?.pagination?.count ?? 0,
    medium: mediumResp?.meta?.pagination?.count ?? 0,
    low: lowResp?.meta?.pagination?.count ?? 0,
  };

  // Prepare filters for dashboard
  const dashboardFilters = [
          ...updatedFilters,
          {
            key: "region__in",
            labelCheckboxGroup: "Regions",
            values: uniqueRegions,
            index: 5,
          },
          {
            key: "service__in",
            labelCheckboxGroup: "Services",
            values: uniqueServices,
            index: 6,
          },
          {
            key: "resource_type__in",
            labelCheckboxGroup: "Resource Type",
            values: uniqueResourceTypes,
            index: 7,
          },
          {
            key: "scan__in",
            labelCheckboxGroup: "Scan ID",
            values: completedScanIds,
            valueLabelMapping: scanDetails,
            index: 9,
          },
  ];

  return (
    <ContentLayout title="Findings" icon="carbon:data-view-alt">
      <DashboardSummary 
        findingsData={expandedFindingsForSummary} 
        filters={dashboardFilters}
        tableData={expandedTableResponse?.data || []}
        tableMetadata={tableFindingsData?.meta}
        tableErrors={tableFindingsData?.errors}
        searchParamsKey={searchParamsKey}
        aggregateStats={aggregateStats}
      />
    </ContentLayout>
  );
}