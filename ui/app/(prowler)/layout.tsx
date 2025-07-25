import "@/styles/globals.css";

import { Metadata, Viewport } from "next";
import React from "react";

import MainLayout from "@/components/ui/main-layout/main-layout";
import { getUserInfo } from "@/actions/users/users";
import { UserProfileProps } from "@/types";
import { Toaster } from "@/components/ui/toast";
import { fontSans } from "@/config/fonts";
import { siteConfig } from "@/config/site";
import { cn } from "@/lib/utils";

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

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getUserInfo();
  return (
    <html suppressHydrationWarning lang="en">
      <head />
      <body
        suppressHydrationWarning
        className={cn(
          "min-h-screen bg-background font-sans antialiased",
          fontSans.variable,
        )}
      >
        <Providers themeProps={{ attribute: "class", defaultTheme: "dark" }}>
          <MainLayout user={user}>{children}</MainLayout>
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
