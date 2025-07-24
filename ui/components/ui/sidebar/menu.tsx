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
import { UserProfileProps } from "@/types";
import { UserNav } from "../user-nav/user-nav";

export const Menu = ({ isOpen, user }: { isOpen: boolean; user: UserProfileProps }) => {
  const pathname = usePathname();
  const menuList = getMenuList(pathname ?? "");

  return (
    <>
      <div className=" space-y-2 px-2">
        {/* Removed search bar and Generate Report button */}
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
     

      <div className="absolute left-0 bottom-0 w-full text-muted-foreground border-t border-border bg-inherit flex items-center justify-center gap-x-2 pt-2 pb-2 px-2 mb-4">
        <UserNav user={user} />
        <TooltipProvider disableHoverableContent>
          <Tooltip delayDuration={100}>
            <TooltipTrigger asChild>
              <Button
                onClick={() => logOut()}
                variant="ghost"
                className={cn(
                  "text-default-700 bg-transparent shadow-none border-none hover:bg-transparent hover:text-indigo-600 transition-all duration-200",
                  isOpen
                    ? "px-4 py-3 text-base justify-center"
                    : "p-2 justify-center",
                )}
              >
                {isOpen ? (
                  <>
                    <span className="font-semibold">Log Out</span>
                    <LogOut size={20} />
                  </>
                ) : (
                  <LogOut size={20} />
                )}
              </Button>
            </TooltipTrigger>
            {isOpen === false && (
              <TooltipContent side="right">Log out</TooltipContent>
            )}
          </Tooltip>
        </TooltipProvider>
      </div>
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
    </>
  );
};
