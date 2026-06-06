import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

const sans = Geist({
  variable: "--ff-sans",
  subsets: ["latin"],
});

const mono = Geist_Mono({
  variable: "--ff-mono",
  subsets: ["latin"],
});

const display = Space_Grotesk({
  variable: "--ff-display",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: {
    default: "Helix — Autonomous Data Science Agent",
    template: "%s · Helix",
  },
  description:
    "Helix turns a CSV and a plain-English goal into insight. A multi-agent system that plans, writes Python, runs it in a sandbox, fixes its own errors, models with AutoML, explains with SHAP, and writes the report.",
  keywords: [
    "autonomous data science",
    "AI agent",
    "LangGraph",
    "AutoML",
    "FLAML",
    "SHAP",
    "self-correcting code",
  ],
  authors: [{ name: "Helix" }],
  openGraph: {
    title: "Helix — Autonomous Data Science Agent",
    description:
      "From a CSV and a sentence to a business-ready report. A self-correcting, multi-agent data science system.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#04060f",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${sans.variable} ${mono.variable} ${display.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-ink">{children}</body>
    </html>
  );
}
