import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Sidebar } from "@/components/sidebar";
import { TopNavbar } from "@/components/top-navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "SpaceForge AI",
  description: "Workspace sistem analis virtual",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="id">
      <body>
        <div className="min-h-screen lg:grid lg:grid-cols-[220px_1fr]">
          <Sidebar />
          <div className="min-w-0">
            <TopNavbar />
            <main className="min-w-0 p-6 sm:p-8 lg:p-12">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}

