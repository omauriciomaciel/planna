import type { Metadata, Viewport } from "next";

import { PwaRegistration } from "@/components/pwa-registration";

import "./globals.css";

export const metadata: Metadata = {
  title: "Planna",
  description: "Painel financeiro doméstico compartilhado.",
};

export const viewport: Viewport = {
  themeColor: "#f6f3eb",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR">
      <body className="min-h-full antialiased">
        {children}
        <PwaRegistration />
      </body>
    </html>
  );
}
