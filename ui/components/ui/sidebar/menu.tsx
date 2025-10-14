"use client";

import { Divider } from "@nextui-org/react";
import { Search } from "lucide-react";
import { Ellipsis, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { logOut } from "@/actions/auth";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui";
import { AddIcon, InfoIcon } from "@/components/icons";
import { FileBarChart } from "lucide-react";
import { FlyoutMenuButton } from "./flyout-menu-button";
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
  console.log('🔍 [Menu] Sidebar Menu rendering with user:', user);
  console.log('🔍 [Menu] User type:', typeof user);
  console.log('🔍 [Menu] User keys:', user ? Object.keys(user) : 'No user');
  
  const pathname = usePathname();
  const menuList = getMenuList(pathname ?? "");
  const router = useRouter();
  const { toast } = useToast();

  const handleLogout = async () => {
    try {
      const result = await logOut();
      
      if (result.success) {
        toast({
          title: "👋 Logged Out Successfully",
          description: "You have been logged out and redirected to the home page.",
          variant: "default",
        });
        
        // Redirect to home page after successful logout
        router.push('/');
        router.refresh(); // Force refresh to clear any cached data
      } else {
        toast({
          title: "❌ Logout Failed",
          description: result.message || "Unable to log out. Please try again.",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
      toast({
        title: "❌ Logout Error",
        description: "An unexpected error occurred during logout.",
        variant: "destructive",
      });
    }
  };

  return (
    <>
      <div className=" space-y-2 px-2">
        {/* Removed search bar and Generate Report button */}
      </div>
      <ScrollArea className="[&>div>div[style]]:!block">
        <nav className="mt-10 h-full w-full">
          <ul className="flex min-h-[calc(100vh-16px-60px-40px-16px-32px-40px-32px-44px)] flex-col items-start space-y-5 px-2 lg:min-h-[calc(100vh-16px-60px-40px-16px-64px-16px-41px)]">
            {menuList.map(({ menus }, index) => (
              <li
                className="w-full"
                key={index}
              >
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
                                    {Icon && <Icon size={18} />}
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
                        <FlyoutMenuButton
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
     

      <div className="absolute left-0 bottom-7 w-full text-muted-foreground border-t border-gray-400 
      dark:border-white border-border bg-inherit flex items-center justify-center gap-x-8 pt-10 pb-2 px-2 mb-4">
        <UserNav user={user}  />
        <TooltipProvider disableHoverableContent>
          <Tooltip delayDuration={100}>
            <TooltipTrigger asChild>
              <Button
                onClick={handleLogout}
                variant="ghost"
                className={cn(
                  "text-default-700 bg-transparent shadow-none border-none hover:bg-transparent hover:text-indigo-600 transition-all duration-200",
                  isOpen
                    ? "px-8 py-3 pr-4 text-base justify-center"
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