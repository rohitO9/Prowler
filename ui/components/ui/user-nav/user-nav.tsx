"use client";

import { LogOut, User } from "lucide-react";
import Link from "next/link";

import { logOut } from "@/actions/auth";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/components/ui/avatar/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip/tooltip";
import { UserProfileProps } from "@/types";

// Removed Button wrapper to avoid extra containers

export const UserNav = ({ user }: { user?: UserProfileProps }) => {
  console.log('🔍 [UserNav] Component rendering with user:', user);
  console.log('🔍 [UserNav] User data structure:', {
    hasUser: !!user,
    hasData: !!(user && user.data),
    hasAttributes: !!(user && user.data && user.data.attributes),
    userKeys: user ? Object.keys(user) : [],
    dataKeys: user?.data ? Object.keys(user.data) : [],
    attributesKeys: user?.data?.attributes ? Object.keys(user.data.attributes) : []
  });

  const attributes = user?.data?.data?.attributes || user?.data?.attributes;

  if (!user || !attributes) {
    console.log('🔍 [UserNav] Returning null - missing user data');
    console.log('🔍 [UserNav] Available paths:', {
      'user.data': !!user?.data,
      // 'user.data.data': !!user?.data?.data,
      'user.data.attributes': !!user?.data?.attributes, 
      'user.data.data.attributes': !!user?.data?.data?.attributes
    });
    return null;
  }

  const { name, email, company_name } = attributes;
  console.log('🔍 [UserNav] Extracted attributes:', { name, email, company_name });
  const firstName = (name && typeof name === 'string') ? name.split(" ")[0] : "User";
  const attrs = attributes as unknown as {
    avatar_url?: string;
    image_url?: string;
    profile_image?: string;
    profile_image_url?: string;
    picture?: string;
  };
  const avatarUrl =
    attrs?.avatar_url ||
    attrs?.profile_image_url ||
    attrs?.profile_image ||
    attrs?.image_url ||
    attrs?.picture ||
    undefined;

  return (
    <DropdownMenu>
      <TooltipProvider disableHoverableContent>
        <Tooltip delayDuration={100}>
          <TooltipTrigger asChild>
            <DropdownMenuTrigger asChild>
              <div className="relative flex flex-col items-center justify-center  cursor-pointer select-none">
                <Avatar className="h-8 w-8 border border-gray-800 dark:border-white">
                  <AvatarImage src={avatarUrl} alt={name ?? "Avatar"} />
                  <AvatarFallback className="bg-transparent flex items-center justify-center">
                    <User className="text-muted-foreground" size={20} />
                  </AvatarFallback>
                </Avatar>
                <span className="text-md mt-2 font-medium leading-none max-w-[120px] truncate text-center">
                  {firstName}
                </span>
              </div>
            </DropdownMenuTrigger>
          </TooltipTrigger>
          <TooltipContent side="bottom">Profile</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <DropdownMenuContent className="w-56" align="end" forceMount>
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-small font-medium leading-none">
              {name && typeof name === 'string' ? name : "User"}
              {company_name && typeof company_name === 'string' && (
                <span className="text-xs">{` | ${company_name}`}</span>
              )}
            </p>
            <p className="text-muted-foreground text-xs leading-none">
              {email && typeof email === 'string' ? email : "No email"}
            </p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem className="hover:cursor-pointer" asChild>
            <Link href="/profile" className="flex items-center">
              <User className="text-muted-foreground mr-3 h-4 w-4" />
              Account
            </Link>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="hover:cursor-pointer"
          onClick={() => logOut()}
        >
          <LogOut className="text-muted-foreground mr-3 h-4 w-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};