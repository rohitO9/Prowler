"use client";

import clsx from "clsx";
import Link from "next/link";
import React, { useEffect, useState } from "react";


import { useSidebar } from "@/hooks/use-sidebar";
import { useStore } from "@/hooks/use-store";
import { cn } from "@/lib/utils";
import { UserProfileProps } from "@/types";

import { Button } from "../button/button";
import { Menu } from "./menu";
import { SidebarToggle } from "./sidebar-toggle";

export function Sidebar({ user }: { user: UserProfileProps }) {
  const sidebar = useStore(useSidebar, (x) => x);
  if (!sidebar) return null;
  const { isOpen, toggleOpen, getOpenState, setIsHover, settings } = sidebar;
  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-20 h-screen bg-gray-100 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 shadow-sm transition-[width] duration-300 ease-in-out",
        !getOpenState() ? "w-[90px]" : "w-72",
        settings.disabled && "hidden",
      )}
    >
      
      <div
        onMouseEnter={() => setIsHover(true)}
        onMouseLeave={() => setIsHover(false)}
        className="no-scrollbar relative flex h-full flex-col overflow-y-auto overflow-x-hidden px-4 py-6 pb-16"
      >
        <div className="flex flex-col items-center justify-center mb-6">
          <Link href="/" className="group flex flex-row items-center gap-3">
            <div className="bg-gradient-to-r from-indigo-600 to-blue-600 rounded-xl w-12 h-12 flex items-center justify-center shadow-lg transition-transform duration-300 group-hover:scale-105">
              <span className="text-2xl font-black text-white select-none">SS</span>
            </div>
            {getOpenState() && (
              <div className="flex flex-col justify-center">
                <span className="text-2xl font-extrabold tracking-tight text-black dark:text-white font-serif bg-gradient-to-r from-indigo-600 to-blue-600 bg-clip-text text-transparent">
                  SecureStack
                </span>
                <span className="block text-xs text-gray-400 tracking-wide text-center w-full">
                  Cloud Security Platform
                </span>
              </div>
            )}
          </Link>
        </div>
        <div className="border-b border-gray-200 dark:border-white mb-4"></div>
        <Menu isOpen={getOpenState()} user={user} />
      </div>
    </aside>
  );
}