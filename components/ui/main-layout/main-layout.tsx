"use client";

import { Suspense, use } from "react";
import { getUserInfo } from "@/actions/users/users";
import { UserProfileProps } from "@/types";
import { useSidebar } from "@/hooks/use-sidebar";
import { useStore } from "@/hooks/use-store";
import { cn } from "@/lib/utils";

import { Sidebar } from "../sidebar/sidebar";

function MainLayoutInner({ children }: { children: React.ReactNode }) {
  const sidebar = useStore(useSidebar, (x) => x);
  const user = use(getUserInfo());
  if (!sidebar) return null;
  const { getOpenState, settings } = sidebar;
  return (
    <div className="flex h-dvh items-center justify-center overflow-hidden">
      <Sidebar user={user} />
      <main
        className={cn(
          "no-scrollbar mb-auto h-full flex-1 flex-col overflow-y-auto transition-[margin-left] duration-300 ease-in-out",
          !settings.disabled && (!getOpenState() ? "lg:ml-[90px]" : "lg:ml-72"),
        )}
      >
        {children}
      </main>
    </div>
  );
}

export default function MainLayout({ children, user }: { children: React.ReactNode; user: UserProfileProps }) {
  const sidebar = useStore(useSidebar, (x) => x);
  if (!sidebar) return null;
  const { getOpenState, settings } = sidebar;
  return (
    <div className="flex h-dvh items-center justify-center overflow-hidden">
      <Sidebar user={user} />
      <main
        className={cn(
          "no-scrollbar mb-auto h-full flex-1 flex-col overflow-y-auto transition-[margin-left] duration-300 ease-in-out",
          !settings.disabled && (!getOpenState() ? "lg:ml-[90px]" : "lg:ml-72"),
        )}
      >
        {children}
      </main>
    </div>
  );
}
