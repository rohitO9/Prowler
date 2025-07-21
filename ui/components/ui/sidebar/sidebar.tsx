"use client";

import clsx from "clsx";
import Link from "next/link";
import React, { useEffect, useState } from "react";


import { useSidebar } from "@/hooks/use-sidebar";
import { useStore } from "@/hooks/use-store";
import { cn } from "@/lib/utils";

import { Button } from "../button/button";
import { Menu } from "./menu";
import { SidebarToggle } from "./sidebar-toggle";

export function Sidebar() {
  const sidebar = useStore(useSidebar, (x) => x);
  if (!sidebar) return null;
  const { isOpen, toggleOpen, getOpenState, setIsHover, settings } = sidebar;
  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-20 h-screen -translate-x-full transition-[width] duration-300 ease-in-out lg:translate-x-0",
        !getOpenState() ? "w-[90px]" : "w-72",
        settings.disabled && "hidden",
      )}
    >
      <SidebarToggle isOpen={isOpen} setIsOpen={toggleOpen} />
      <div
        onMouseEnter={() => setIsHover(true)}
        onMouseLeave={() => setIsHover(false)}
        className="no-scrollbar relative flex h-full flex-col overflow-y-auto overflow-x-hidden px-3 py-4 shadow-md dark:shadow-primary"
      >
        <div className="flex flex-col items-center justify-center my-4">
          <Link href="/" className="group flex flex-row items-center gap-3">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl w-14 h-14 flex items-center justify-center shadow-lg transition-transform duration-1500 group-hover:scale-125 group-hover:rotate-360">
              <span className="text-3xl font-black text-white select-none">SS</span>
            </div>
            {getOpenState() && (
              <div className="flex flex-col justify-center">
                <span className="text-3xl font-extrabold tracking-tight text-black dark:text-white font-serif bg-gradient-to-r from-indigo-500 to-purple-600 bg-clip-text text-transparent">
                  SecureStack
                </span>
                <span className="block text-xs text-gray-400 tracking-wide text-center w-full">
                  Cloud Security Platform
                </span>
              </div>
            )}
          </Link>
        </div>

        <Menu isOpen={getOpenState()} />
      </div>
    </aside>
  );
}
