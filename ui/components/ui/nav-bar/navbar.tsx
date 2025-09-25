
import { ReactNode } from "react";

import { ThemeSwitch } from "@/components/ThemeSwitch";
import { UserProfileProps } from "@/types";
import { auth } from "@/auth.config";


import Link from "next/link";
import { Button } from "../button/button";

interface NavbarProps {
  title: string;
  icon: string | ReactNode;
  user: UserProfileProps;
}

export async function Navbar({ title, icon, user }: NavbarProps) {
  const session = await auth();
  const tenantPrefix = (session as any)?.tenantPrefix || (session as any)?.tenant_prefix;
  const tenantSuffix = (session as any)?.tenantSuffix || (session as any)?.tenant_suffix;
  const tenantName = (session as any)?.tenantName || (session as any)?.tenant_name;
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
          {tenantName && (
            <div className="px-3 py-1 rounded-full bg-blue-100 text-blue-800 text-sm font-semibold border border-blue-300">
              {tenantPrefix ? `[${tenantPrefix}] ` : ""}
              {tenantName}
              {tenantSuffix ? ` - ${tenantSuffix}` : ""}
            </div>
          )}
        </div>

        {/* Right spacer to keep layout */}
        <div className="flex-1" />

        {/* Right: User/Theme/Trial */}
        <div className="flex items-center flex-none gap-3">
          {tenantName && (
            <span className="px-3 py-1 rounded bg-yellow-100 text-yellow-800 text-sm font-medium border border-yellow-300">
              {tenantPrefix ? `${tenantPrefix}-` : ''}{tenantSuffix || ''}
            </span>
          )}
          <ThemeSwitch />
         
        </div>
      </div>
    </header>
  );
}