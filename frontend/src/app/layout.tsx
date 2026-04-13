import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "PortfolioAI — Build your dev portfolio in minutes",
  description:
    "Connect GitHub, upload your resume. AI builds and auto-maintains your portfolio site.",
  openGraph: {
    title: "PortfolioAI",
    description: "AI-powered portfolio builder for developers",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
