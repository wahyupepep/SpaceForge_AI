import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Sidebar } from "@/components/sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "SpecForge AI",
  description: "Virtual System Analyst workspace",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
          <Sidebar />
          <main className="min-w-0 p-6 sm:p-8 lg:p-12">{children}</main>
        </div>
      </body>
    </html>
  );
}

