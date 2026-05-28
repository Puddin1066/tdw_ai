import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RI Physician-Led Venture Syndicates",
  description:
    "Rhode Island technology opportunities with physician syndicates, clinical validation paths, and Slater SSBCI match financing",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${geistSans.variable} ${geistMono.variable} min-h-screen font-sans`}>
        <div className="relative min-h-screen">
          <div
            className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-teal-950/20 via-background to-background"
            aria-hidden
          />
          <div className="relative">{children}</div>
        </div>
      </body>
    </html>
  );
}
