import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dancing with the SARs",
  description:
    "NISAR L-band radar shows surface change from space: forest clearing in Rondônia, a sinking coast in Demak and a wildfire above Okanagan Lake, each with a way to act.",
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
  colorScheme: "light dark",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
