'use client';

import { ReactNode, useEffect, useState } from "react";

import { ThemeSwitch } from "@/components/ThemeSwitch";
import { UserProfileProps } from "@/types";

import Link from "next/link";
import { Button } from "../button/button";

interface NavbarProps {
  title: string;
  icon: string | ReactNode;
  user: UserProfileProps;
}

interface TenantInfo {
  name?: string;
  trial_ends_at?: string;
}

export function Navbar({ title, icon, user }: NavbarProps) {
  const [tenantInfo, setTenantInfo] = useState<TenantInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function getTenantInfo() {
      try {
        setIsLoading(true);
        const host = window.location.hostname;
        
        // Extract subdomain from hostname
        const subdomain = host.split('.')[0];
        
        if (subdomain && subdomain !== 'localhost' && subdomain !== '127.0.0.1' && subdomain !== 'www') {
          const response = await fetch('/api/v1/tenant/public-info', {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          });
          
          if (response.ok) {
            const data = await response.json();
            
            // Handle nested response structure: data.data.data.tenant (three levels of nesting)
            let tenant = null;
            if (data.data?.data?.data?.tenant) {
              tenant = data.data.data.data.tenant;
            } else if (data.data?.data?.tenant) {
              tenant = data.data.data.tenant;
            } else if (data.data?.tenant) {
              tenant = data.data.tenant;
            } else if (data.data?.attributes) {
              tenant = data.data.attributes;
            } else if (data.data) {
              tenant = data.data;
            } else if (data.attributes) {
              tenant = data.attributes;
            } else {
              tenant = data;
            }
            
            setTenantInfo(tenant);
          }
        }
      } catch (error) {
        // Silently handle errors - don't break UI if tenant info fails to load
        setTenantInfo(null);
      } finally {
        setIsLoading(false);
      }
    }

    getTenantInfo();
  }, []);

  const tenantName = tenantInfo?.name;
  const trialEndsAt = tenantInfo?.trial_ends_at;
  
  // Calculate days remaining
  let daysRemaining: number | null = null;
  if (trialEndsAt) {
    try {
      const trialDate = new Date(trialEndsAt);
      const now = new Date();
      const diffMs = trialDate.getTime() - now.getTime();
      daysRemaining = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    } catch (error) {
      // Silently handle date parsing errors
      daysRemaining = null;
    }
  }
  return (
    <header className="sticky top-0 z-10 w-full bg-background/95 shadow backdrop-blur supports-[backdrop-filter] bg-gray-100 dark:bg-gray-900 dark:shadow-primary">
      <div className="mx-4 flex h-14 items-center sm:mx-8">
        
        <div className="flex items-center flex-none gap-2">
          <Button
            asChild
            className="rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-md transition-all duration-200 hover:from-indigo-600 hover:to-blue-700 px-4 py-2 text-base font-semibold flex items-center gap-2"
          >
            <Link href="/scans">
              Generate Report
            </Link>
          </Button>
          <Button
            asChild
            className="rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-md transition-all duration-200 hover:from-indigo-600 hover:to-blue-700 px-4 py-2 text-base font-semibold flex items-center gap-2"
          >
            <Link href="/overview">
              Overview
            </Link>
          </Button>
          <Button
            asChild
            className="rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-md transition-all duration-200 hover:from-indigo-600 hover:to-blue-700 px-4 py-2 text-base font-semibold flex items-center gap-2"
          >
            <Link href="/findings">
              Findings
            </Link>
          </Button>
         
        </div>

        {/* Center: Org badge if present */}
        <div className="flex-1 flex justify-center">
          {isLoading ? (
            <div className="px-3 py-1 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-sm font-semibold border border-gray-300 dark:border-gray-600">
              Loading...
            </div>
          ) : tenantName ? (
            <div className="px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-sm font-semibold border border-blue-300 dark:border-blue-700">
              {tenantName}
            </div>
          ) : (
            <div className="px-3 py-1 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-sm font-semibold border border-gray-300 dark:border-gray-600">
              No Company
            </div>
          )}
        </div>

        {/* Right spacer to keep layout */}
        <div className="flex-1" />

        {/* Right: User/Theme/Trial */}
        <div className="flex items-center flex-none gap-3">
          {isLoading ? (
            <div className="px-3 py-1 rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-sm font-medium border border-gray-300 dark:border-gray-600">
              Loading...
            </div>
          ) : trialEndsAt && daysRemaining !== null ? (
            <span className="px-3 py-1 rounded bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 text-sm font-medium border border-yellow-300 dark:border-yellow-700">
              {daysRemaining > 0 ? `${daysRemaining} days left` : daysRemaining === 0 ? 'Trial ends today' : 'Trial expired'}
            </span>
          ) : trialEndsAt ? (
            <span className="px-3 py-1 rounded bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 text-sm font-medium border border-yellow-300 dark:border-yellow-700">
              Trial ends: {new Date(trialEndsAt).toLocaleDateString()}
            </span>
          ) : null}
          <ThemeSwitch />
         
        </div>
      </div>
    </header>
  );
}