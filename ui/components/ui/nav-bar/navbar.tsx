
import { ReactNode } from "react";

import { ThemeSwitch } from "@/components/ThemeSwitch";
import { UserProfileProps } from "@/types";


import Link from "next/link";
import { Button } from "../button/button";

interface NavbarProps {
  title: string;
  icon: string | ReactNode;
  user: UserProfileProps;
}

export function Navbar({ title, icon, user }: NavbarProps) {
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
        </div>

        {/* Center: Links */}
        <div className="flex-1 flex justify-center items-center space-x-6">
          <Link href="/findings" className="text-sm font-medium text-default-700 hover:text-indigo-600 transition-colors">
            Findings
          </Link>
          <a href="https://docs.prowler.com/" target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-default-700 hover:text-indigo-600 transition-colors">
            Documentation
          </a>
          <a href="https://github.com/prowler-cloud/prowler/issues" target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-default-700 hover:text-indigo-600 transition-colors">
            Support
          </a>
        </div>

        {/* Right: User/Theme/Trial */}
        <div className="flex items-center flex-none gap-3">
          <span className="px-3 py-1 rounded bg-yellow-100 text-yellow-800 text-sm font-medium border border-yellow-300">
            Free Trial: 7 days remaining
          </span>
          <ThemeSwitch />
         
        </div>
      </div>
    </header>
  );
}
