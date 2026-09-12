import type { Metadata, Viewport } from "next";

import { PwaRegistration } from "@/components/pwa-registration";

import "./globals.css";

const themeScript = `(function(){try{var t=localStorage.getItem("planna-theme");var d=t==="dark"||(t!=="light"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.classList.toggle("dark",d)}catch(e){}})()`;

export const metadata: Metadata = {
  title: "Planna",
  description: "Painel financeiro doméstico compartilhado.",
};

export const viewport: Viewport = {
  themeColor: "#f7f8fb",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full antialiased">
        {children}
        <PwaRegistration />
      </body>
    </html>
  );
}
