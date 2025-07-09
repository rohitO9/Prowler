"use client";

import { Divider } from "@nextui-org/react";
import { Search } from "lucide-react";
import { Ellipsis, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { logOut } from "@/actions/auth";
import { AddIcon, InfoIcon } from "@/components/icons";
import { FileBarChart } from "lucide-react";
import { CollapseMenuButton } from "@/components/ui/sidebar/collapse-menu-button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip/tooltip";
import { getMenuList } from "@/lib/menu-list";
import { cn } from "@/lib/utils";

import { Button } from "../button/button";
import { CustomButton } from "../custom/custom-button";
import { ScrollArea } from "../scroll-area/scroll-area";
import { ThemeSwitch } from "@/components/ThemeSwitch";

export const Menu = ({ isOpen }: { isOpen: boolean }) => {
  const pathname = usePathname();
  const menuList = getMenuList(pathname ?? "");

  return (
    <>
      <div className=" space-y-2 px-2">
        <div className="relative w-full">
          <Search
            className="text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2"
            size={16}
          />
          <input
            type="text"
            placeholder="Search menu..."
            className={cn(
              "border-input placeholder:text-muted-foreground w-full rounded-xl border bg-background py-2 pl-10 pr-4 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500",
              isOpen ? "" : "hidden",
            )}
            onChange={(e) => {
              // add filtering logic if needed
            }}
          />
        </div>

        <Button
          asChild
          className={cn(
            "w-full rounded-xl  bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md transition-all duration-200 hover:from-indigo-700 hover:to-purple-700",
            isOpen
              ? "justify-between px-4 py-3 text-base"
              : "justify-center p-2",
          )}
        >
          <Link href="/scans">
            {isOpen ? (
              <>
                <span className="font-semibold">Generate Report</span>
                <FileBarChart size={20} />
              </>
            ) : (
              <FileBarChart size={20} />
            )}
          </Link>
        </Button>
      </div>
      <ScrollArea className="[&>div>div[style]]:!block">
        <nav className="mt-4 h-full w-full">
          <ul className="flex min-h-[calc(100vh-16px-60px-40px-16px-32px-40px-32px-44px)] flex-col items-start space-y-1 px-2 lg:min-h-[calc(100vh-16px-60px-40px-16px-64px-16px-41px)]">
            {menuList.map(({ groupLabel, menus }, index) => (
              <li
                className={cn(
                  "w-full",
                  groupLabel ? "pt-2" : "",
                  "last:!mt-auto",
                )}
                key={index}
              >
                {(isOpen && groupLabel) || isOpen === undefined ? (
                  <p className="text-muted-foreground max-w-[248px] truncate px-4 pb-2 text-xs font-normal">
                    {groupLabel}
                  </p>
                ) : !isOpen && isOpen !== undefined && groupLabel ? (
                  <TooltipProvider>
                    <Tooltip delayDuration={100}>
                      <TooltipTrigger className="w-full">
                        <div className="flex w-full items-center justify-center">
                          <Ellipsis className="h-5 w-5" />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent className="z-100" side="right">
                        <p>{groupLabel}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                ) : (
                  <p className="pb-2"></p>
                )}
                {menus.map(
                  (
                    { href, label, icon: Icon, active, submenus, defaultOpen },
                    index,
                  ) =>
                    !submenus || submenus.length === 0 ? (
                      <div className="w-full" key={index}>
                        <TooltipProvider disableHoverableContent>
                          <Tooltip delayDuration={100}>
                            <TooltipTrigger asChild>
                              <Button
                                variant={
                                  (active === undefined &&
                                    pathname?.startsWith(href)) ||
                                  active
                                    ? "secondary"
                                    : "ghost"
                                }
                                className="mb-1 h-8 w-full justify-start"
                                asChild
                              >
                                <Link href={href}>
                                  <span
                                    className={cn(
                                      isOpen === false ? "" : "mr-4",
                                    )}
                                  >
                                    <Icon size={18} />
                                  </span>
                                  <p
                                    className={cn(
                                      "max-w-[200px] truncate",
                                      isOpen === false
                                        ? "-translate-x-96 opacity-0"
                                        : "translate-x-0 opacity-100",
                                    )}
                                  >
                                    {label}
                                  </p>
                                </Link>
                              </Button>
                            </TooltipTrigger>
                            {isOpen === false && (
                              <TooltipContent side="right">
                                {label}
                              </TooltipContent>
                            )}
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    ) : (
                      <div className="w-full" key={index}>
                        <CollapseMenuButton
                          icon={Icon}
                          label={label}
                          submenus={submenus}
                          isOpen={isOpen}
                          defaultOpen={defaultOpen ?? false}
                        />
                      </div>
                    ),
                )}
              </li>
            ))}
          </ul>
        </nav>
      </ScrollArea>
      <div className="flex w-full grow items-end">
        <div className="flex w-full items-center justify-between px-2 pb-4">
          <ThemeSwitch />
          <TooltipProvider disableHoverableContent>
            <Tooltip delayDuration={100}>
              <TooltipTrigger asChild>
                <Button
                  onClick={() => logOut()}
                  variant="ghost"
                  className={cn(
                    "rounded-xl bg-gradient-to-r from-rose-600 to-red-500 text-white shadow-md transition-all duration-200 hover:from-rose-700 hover:to-red-600",
                    isOpen
                      ? "px-4 py-3 text-base"
                      : "p-2",
                  )}
                >
                  {isOpen ? (
                    <>
                      <span className="font-semibold">Sign Out</span>
                      <LogOut size={20} />
                    </>
                  ) : (
                    <LogOut size={20} />
                  )}
                </Button>
              </TooltipTrigger>
              {isOpen === false && (
                <TooltipContent side="right">Sign out</TooltipContent>
              )}
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      <div className="text-muted-foreground border-border mt-2 flex items-center justify-center gap-2 border-t pt-2 text-center text-xs">
        <span>v1.0.0</span>
        {process.env.NEXT_PUBLIC_IS_CLOUD_ENV === "true" && (
          <>
            <Divider orientation="vertical" />
            <Link
              href="https://status.prowler.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1"
            >
              <InfoIcon size={16} />
              <span className="text-muted-foreground font-normal opacity-80 transition-opacity hover:font-bold hover:opacity-100">
                Service Status
              </span>
            </Link>
          </>
        )}
      </div>
    </>
  );
};
