import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AuditAI — Smart GST Compliance",
  description: "AI-powered GST audit tool for Indian CAs and businesses. Notice prediction, multi-language reports, ITC risk detection.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <head>
          <link rel="icon" href="/favicon.ico" sizes="any" />
          <link rel="icon" href="/logo.png" type="image/png" />
        </head>
        <body>{children}</body>
      </html>
    </ClerkProvider>
  );
}