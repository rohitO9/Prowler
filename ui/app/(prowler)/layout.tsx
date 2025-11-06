import "@/styles/globals.css";

import { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import React from "react";

import MainLayout from "@/components/ui/main-layout/main-layout";
import { getUserInfo } from "@/actions/users/users";
import { Toaster } from "@/components/ui/toast";
import { siteConfig } from "@/config/site";

import { Providers } from "../providers";

export const metadata: Metadata = {
  title: {
    default: siteConfig.name,
    template: `%s - ${siteConfig.name}`,
  },
  description: siteConfig.description,
  icons: {
    icon: "/favicon.ico",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "white" },
    { media: "(prefers-color-scheme: dark)", color: "black" },
  ],
};

export default async function ProwlerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const headersList = await headers();
  const host = headersList.get('host');
  const user = await getUserInfo(host || undefined);
  return (
    <Providers themeProps={{ attribute: "class", defaultTheme: "dark" }}>
      <MainLayout user={user}>{children}</MainLayout>
      <Toaster />
    </Providers>
  );
}
