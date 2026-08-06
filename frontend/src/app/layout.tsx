import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AppQuestionnaireProvider } from "@/context/questionnaire-provider";
import { SiteHeader } from "@/components/brand/site-header";
import { UnderstandingTreeCompanion } from "@/components/brand/understanding-tree-companion";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://optime-nursing.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "OPTIME | Find the Right Senior Care, Based on What Matters",
    template: "%s | OPTIME",
  },
  description:
    "OPTIME helps families compare senior care and nursing home options using care needs, verified evidence, quality signals, and the details that matter to each family.",
  applicationName: "OPTIME",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    url: "/",
    siteName: "OPTIME",
    title: "OPTIME | Find the Right Senior Care, Based on What Matters",
    description:
      "Compare senior care options using care needs, verified evidence, quality signals, and family-specific priorities.",
  },
  twitter: {
    card: "summary_large_image",
    title: "OPTIME | Find the Right Senior Care, Based on What Matters",
    description:
      "Compare senior care options using care needs, verified evidence, quality signals, and family-specific priorities.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AppQuestionnaireProvider>
          <SiteHeader />
          <UnderstandingTreeCompanion />
          <div className="flex-1">{children}</div>
        </AppQuestionnaireProvider>
      </body>
    </html>
  );
}
