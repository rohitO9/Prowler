"use client";

import { Spacer } from "@nextui-org/react";
import { format, subDays } from "date-fns";
import { Suspense, useEffect, useState } from "react";

import { getFindings } from "@/actions/findings/findings";
import {
  getFindingsBySeverity,
  getFindingsByStatus,
} from "@/actions/overview/overview";
import {
  FindingsBySeverityChart,
  FindingsByStatusChart,
  LinkToFindings,
  SkeletonFindingsBySeverityChart,
  SkeletonFindingsByStatusChart,
} from "@/components/overview";
import { ColumnNewFindingsToDate } from "@/components/overview/new-findings-table/table/column-new-findings-to-date";
import { SkeletonTableNewFindings } from "@/components/overview/new-findings-table/table/skeleton-table-new-findings";
import { CustomAlertModal } from "@/components/ui/custom";
import { DataTable } from "@/components/ui/table";
import { createDict } from "@/lib/helper";
import { FindingProps } from "@/types";

interface ProviderDetailsModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  selectedProvider: string | null;
}

export const ProviderDetailsModal = ({
  isOpen,
  onOpenChange,
  selectedProvider,
}: ProviderDetailsModalProps) => {
  console.log("ProviderDetailsModal props:", { isOpen, selectedProvider });
  
  const [findingsByStatus, setFindingsByStatus] = useState<any>(null);
  const [findingsBySeverity, setFindingsBySeverity] = useState<any>(null);
  const [tableData, setTableData] = useState<any>(null);
 
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && selectedProvider) {
      setLoading(true);
      // Load data when modal opens
      const loadData = async () => {
        try {
          const filters = { "filter[provider_type]": selectedProvider };
          console.log("Loading data for provider:", selectedProvider);
          console.log("Using filters:", filters);
          
          const [statusData, severityData, tableData] = await Promise.all([
            getFindingsByStatus({ filters }),
            getFindingsBySeverity({ filters }),
            getFindings({
              query: undefined,
              page: 1,
              sort: "severity,-inserted_at",
              filters: {
                "filter[status__in]": "FAIL",
                "filter[delta__in]": "new",
                "filter[inserted_at__gte]": format(subDays(new Date(), 2), "yyyy-MM-dd"),
                "filter[provider_type]": selectedProvider,
              },
            }),
          ]);
          
          console.log("Status data:", statusData);
          console.log("Severity data:", severityData);
          console.log("Table data:", tableData);
          
          // Use dummy data if no real data is available for testing
          setFindingsByStatus(statusData);
          setFindingsBySeverity(severityData);
          setTableData(tableData);
          
        } catch (error) {
          console.error("Error loading provider data:", error);
          // Use dummy data on error for testing
          setFindingsByStatus(null);
          setFindingsBySeverity(null);
          setTableData(null);
        } finally {
          setLoading(false);
        }
      };
      
      loadData();
    }
  }, [isOpen, selectedProvider]);
  
  if (!selectedProvider) return null;

  const providerName = selectedProvider.charAt(0).toUpperCase() + selectedProvider.slice(1);
  
  // Default zero state for charts
  const zeroStatusData = {
    data: {
      attributes: {
        fail: 0,
        pass: 0,
        pass_new: 0,
        fail_new: 0,
        total: 0,
      },
    },
  };

  const zeroSeverityData = {
    data: {
      attributes: {
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
        informational: 0,
      },
    },
  };

  return (
    <CustomAlertModal
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      title={
        <div className="flex flex-col gap-2">
          <h2 className="text-2xl font-extrabold tracking-tight text-gray-900 dark:text-white">
            {providerName} Security Findings Overview
          </h2>
          <div className="h-1 w-16 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full mb-1" />
        </div>
      }
      description={
        <span className="text-base ml-4 font-medium text-gray-600 dark:text-gray-300">
          Comprehensive security findings and compliance reports for <span className="font-semibold text-indigo-600 dark:text-indigo-400">{providerName}</span>
        </span>
      }
    >
      <div className="space-y-8">
        {/* Charts Section - Horizontal Layout */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-8">
          {/* Findings by Status Chart */}
          <div className="p-0">
            <h3 className="mb-4 text-sm font-bold uppercase text-gray-700 dark:text-gray-300">Findings by Status</h3>
            {loading ? (
              <SkeletonFindingsByStatusChart />
            ) :
              <FindingsByStatusChart findingsByStatus={
                findingsByStatus && findingsByStatus.data && findingsByStatus.data.attributes
                  ? findingsByStatus
                  : zeroStatusData
              } />
            }
          </div>

          {/* Findings by Severity Chart */}
          <div className="p-0">
            <h3 className="mb-4 text-sm font-bold uppercase text-gray-700 dark:text-gray-300">Findings by Severity</h3>
            {loading ? (
              <SkeletonFindingsBySeverityChart />
            ) :
              <FindingsBySeverityChart findingsBySeverity={
                findingsBySeverity && findingsBySeverity.data && findingsBySeverity.data.attributes
                  ? findingsBySeverity
                  : zeroSeverityData
              } />
            }
          </div>
        </div>
        <Spacer y={8} />
        {/* Latest New Failing Findings Table */}
        <div>
          <FindingsTable findingsData={
            tableData && tableData.data && tableData.data.length > 0
              ? tableData
              : { data: [] }
          } />
        </div>
      </div>
    </CustomAlertModal>
  );
  
};

const FindingsTable = ({ findingsData }: { findingsData: any }) => {
  // Create dictionaries for resources, scans, and providers
  const resourceDict = findingsData ? createDict("resources", findingsData) : {};
  const scanDict = findingsData ? createDict("scans", findingsData) : {};
  const providerDict = findingsData ? createDict("providers", findingsData) : {};

  // Expand each finding with its corresponding resource, scan, and provider
  const expandedFindings = findingsData?.data
    ? findingsData.data.map((finding: FindingProps) => {
        const scan = scanDict[finding.relationships?.scan?.data?.id];
        const resource =
          resourceDict[finding.relationships?.resources?.data?.[0]?.id];
        const provider = providerDict[scan?.relationships?.provider?.data?.id];

        return {
          ...finding,
          relationships: { scan, resource, provider },
        };
      })
    : [];

  // Create the new object while maintaining the original structure
  const expandedResponse = {
    ...findingsData,
    data: expandedFindings,
  };

  return (
    <>
      <div className="relative flex w-full">
        <div className="flex w-full items-center gap-2">
          <h3 className="text-sm font-bold uppercase">
            Latest new failing findings
          </h3>
          <p className="text-xs text-gray-500">
            Showing the latest 10 new failing findings by severity from the last 2 days.
          </p>
        </div>
        <div className="absolute -top-6 right-0">
          <LinkToFindings />
        </div>
      </div>
      <Spacer y={4} />
      <DataTable
        columns={ColumnNewFindingsToDate}
        data={expandedResponse?.data && expandedResponse.data.length > 0 ? expandedResponse.data : []}
      />
    </>
  );
}; 