import type { Metadata } from "next";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { BreatheWiseProvider } from "@/hooks/useBreatheWise";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "BreatheWise — Breathe Smarter. Live Better.",
  description:
    "AI-powered urban air quality companion helping families navigate winter smog and urban air pollution with verified environmental data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${jakarta.variable} ${mono.variable}`}>
      <body className="font-sans bg-bw-bg text-bw-text selection:bg-bw-accent selection:text-bw-bg">
        <BreatheWiseProvider>{children}</BreatheWiseProvider>
      </body>
    </html>
  );
}
