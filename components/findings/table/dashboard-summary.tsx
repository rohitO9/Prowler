"use client";

import React, { useState } from "react";
import { Spacer } from "@nextui-org/react";
import { FindingProps } from "@/types";
import { DataTable, DataTableFilterCustom } from "@/components/ui/table";
import { SkeletonTableFindings, ColumnFindings } from "@/components/findings/table";
import { FilterControls } from "@/components/filters/filter-controls";
import { CustomButton } from "@/components/ui/custom";
import { ChevronDownIcon, ArrowUpIcon } from "@/components/icons";

interface DashboardStats {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  passed: number;
  failed: number;
  manual: number;
  muted: number;
  todayNew: number;
}

interface DashboardSummaryProps {
  findingsData: FindingProps[];
  filters?: any[];
  tableData?: any;
  tableMetadata?: any;
  tableErrors?: any;
  searchParamsKey?: string;
  aggregateStats?: {
    total: number;
    passed: number;
    failed: number;
    manual: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

const processFindingsForDashboard = (findings: FindingProps[]): DashboardStats => {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  return {
    total: findings.length,
    critical: findings.filter(f => f.attributes.severity === 'critical').length,
    high: findings.filter(f => f.attributes.severity === 'high').length,
    medium: findings.filter(f => f.attributes.severity === 'medium').length,
    low: findings.filter(f => f.attributes.severity === 'low').length,
    passed: findings.filter(f => f.attributes.status === 'PASS').length,
    failed: findings.filter(f => f.attributes.status === 'FAIL').length,
    manual: findings.filter(f => f.attributes.status === 'MANUAL').length,
    muted: findings.filter(f => f.attributes.muted).length,
    todayNew: findings.filter(f => {
      const insertedAt = new Date(f.attributes.inserted_at);
      return insertedAt >= today;
    }).length,
  };
};

export const DashboardSummary: React.FC<DashboardSummaryProps> = ({ 
  findingsData, 
  filters = [], 
  tableData = [], 
  tableMetadata = null, 
  tableErrors = null,
  searchParamsKey = "",
  aggregateStats,
}) => {
  // Compute stats based on the current table data (what the user sees)
  const pageStats = processFindingsForDashboard(tableData || []);
  const stats = pageStats;
  const totalFindings = aggregateStats?.total ?? tableMetadata?.pagination?.count ?? stats.total;
  const totalPassed = aggregateStats?.passed ?? stats.passed;
  const totalFailed = aggregateStats?.failed ?? stats.failed;
  const totalManual = aggregateStats?.manual ?? stats.manual;
  
  // Risk overview section removed
  
  const [showFilters, setShowFilters] = useState(true);

  return (
    <div className="mb-8">
      {/* Executive Summary Header */}
      <div className="mb-6 border-b border-gray-300 dark:border-gray-600 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
            Security Findings Executive Summary
          </h1>
         {/* <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Comprehensive security assessment report as of {new Date().toLocaleDateString('en-US', { 
              year: 'numeric', 
              month: 'long', 
              day: 'numeric' 
            })}
          </p>*/}
        </div>
      </div>

      {/* Key Metrics Section */}
      <div className="bg-white dark:bg-prowler-blue-400 border border-gray-300 dark:border-gray-600 shadow-sm">
        <div className="px-6 py-4 bg-gray-100 dark:bg-gray-700 border-b border-gray-300 dark:border-gray-600">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Key Security Metrics</h2>
        </div>
        
          <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 items-stretch">
            {/* Total Findings */}
            <div className="text-center h-full flex flex-col justify-center">
              <div className="text-3xl font-bold text-gray-900 dark:text-white mb-1">{totalFindings.toLocaleString()}</div>
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300">Total Findings</div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">Across current filters</div>
            </div>
            
            {/* Passed Findings */}
            <div className="text-center h-full flex flex-col justify-center">
              <div className="text-3xl font-bold text-green-700 dark:text-green-400 mb-1">{totalPassed.toLocaleString()}</div>
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300">Passed Findings</div>
              <div className="text-xs text-green-600 dark:text-green-400 mt-1 font-medium">Across current filters</div>
            </div>
            
            {/* Failed Findings */}
            <div className="text-center h-full flex flex-col justify-center">
              <div className="text-3xl font-bold text-red-700 dark:text-red-400 mb-1">{totalFailed.toLocaleString()}</div>
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300">Failed Findings</div>
              <div className="text-xs text-red-600 dark:text-red-400 mt-1 font-medium">Across current filters</div>
            </div>

            {/* Manual Findings */}
            <div className="text-center h-full flex flex-col justify-center">
              <div className="text-3xl font-bold text-blue-700 dark:text-blue-400 mb-1">{totalManual.toLocaleString()}</div>
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300">Manual Findings</div>
              <div className="text-xs text-blue-600 dark:text-blue-400 mt-1 font-medium">Across current filters</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Controls Section with Hide/Show */}
      <div className="mt-6 bg-white dark:bg-prowler-blue-400 border border-gray-300 dark:border-gray-600 shadow-sm">
        <div className="px-6 py-4 bg-gray-100 dark:bg-gray-700 border-b border-gray-300 dark:border-gray-600 flex justify-between items-center">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Filters & Search</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Use these filters to control the findings table below</p>
          </div>
          <CustomButton
            ariaLabel={showFilters ? "Hide filters" : "Show filters"}
            className="w-fit"
            onPress={() => setShowFilters(!showFilters)}
            variant="light"
            size="sm"
            endContent={showFilters ? <ArrowUpIcon size={16} /> : <ChevronDownIcon size={16} />}
            radius="sm"
          >
            {showFilters ? "Hide Filters" : "Show Filters"}
          </CustomButton>
        </div>
        
        {showFilters && (
          <div className="p-6">
            <FilterControls search date />
            <Spacer y={4} />
            {filters.length > 0 && (
              <DataTableFilterCustom
                filters={filters}
                defaultOpen={true}
              />
            )}
          </div>
        )}
        </div>
        
      {/* Table with Suspense */}
      {searchParamsKey && (
        <React.Suspense key={searchParamsKey} fallback={<SkeletonTableFindings />}>
          <div className="mt-6">
            {tableErrors && (
              <div className="mb-4 flex rounded-lg border border-red-500 bg-red-100 p-2 text-small text-red-700">
                <p className="mr-2 font-semibold">Error:</p>
                <p>{tableErrors[0]?.detail}</p>
        </div>
            )}
            {/* <FindingCardGrid data={tableData || []} metadata={tableMetadata} /> */}
            <DataTable
              columns={ColumnFindings}
              data={tableData || []}
              metadata={tableMetadata}
            />
          </div>
        </React.Suspense>
      )}
    </div>
  );
}; 