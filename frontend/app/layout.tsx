import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IAM — Intellectual Artificial Mainbrain",
  description: "One IAM · many independent conversations · an evolving autonomous intelligence",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
