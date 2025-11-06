import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "../styles/globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SecureStack - Enterprise Cloud Security Platform",
  description: "Secure your cloud infrastructure with SecureStack's comprehensive security scanning and Azure AD integration",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  console.log('🔍 [RootLayout] Layout rendering');
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <Providers themeProps={{ attribute: "class", defaultTheme: "dark" }}>
          {children}
        </Providers>
      </body>
    </html>
  );
}
