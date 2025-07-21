import { Icon } from "@iconify/react";
import { ReactNode } from "react";

import { ThemeSwitch } from "@/components/ThemeSwitch";
import { UserProfileProps } from "@/types";

import { SheetMenu } from "../sidebar/sheet-menu";
import { UserNav } from "../user-nav/user-nav";
import { FileBarChart } from "lucide-react";
import Link from "next/link";
import { Button } from "../button/button";

interface NavbarProps {
  title: string;
  icon: string | ReactNode;
  user: UserProfileProps;
}

export function Navbar({ title, icon, user }: NavbarProps) {
  return (
    <header className="sticky top-0 z-10 w-full bg-background/95 shadow backdrop-blur supports-[backdrop-filter]:bg-background/60 dark:shadow-primary">
      <div className="mx-4 flex h-14 items-center sm:mx-8">
        <div className="flex items-center space-x-4">
          <Button
            asChild
            className="rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md transition-all duration-200 hover:from-indigo-700 hover:to-purple-700 px-4 py-2 text-base font-semibold flex items-center gap-2"
          >
            <Link href="/scans">
              Generate Report
              <FileBarChart size={20} />
            </Link>
          </Button>
          
          <Link href="/findings" className=" text-sm font-medium text-default-700 hover:text-indigo-600 transition-colors">
            Findings
          </Link>
          <a href="https://docs.prowler.com/" target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-default-700 hover:text-indigo-600 transition-colors">
            Documentation
          </a>
          <a href="https://github.com/prowler-cloud/prowler/issues" target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-default-700 hover:text-indigo-600 transition-colors">
            Support
          </a>
          
        </div>
        <div className="flex flex-1 items-center justify-end gap-3">
          <span className="px-3 py-1 rounded bg-yellow-100 text-yellow-800 text-sm font-medium border border-yellow-300">
            Free Trial: 7 days remaining
          </span>
          <ThemeSwitch />
          <UserNav user={user} />
        </div>
      </div>
    </header>
  );
}
