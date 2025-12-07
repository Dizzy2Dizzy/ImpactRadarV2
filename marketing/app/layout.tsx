import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import Script from "next/script";
import { ThemeProvider } from "@/components/ThemeProvider";
import { CookieConsent } from "@/components/CookieConsent";
import { WebVitals } from "@/components/WebVitals";
import { GlobalNotificationBanner } from "@/components/GlobalNotificationBanner";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Impact Radar | Market-moving events tracked to the second",
  description: "Aggregates SEC, FDA, and company announcements into a single dashboard with deterministic impact scoring and actionable alerts.",
  metadataBase: new URL("https://impactradar.co"),
  openGraph: {
    title: "Impact Radar | Market-moving events tracked to the second",
    description: "Aggregates SEC, FDA, and company announcements into a single dashboard with deterministic impact scoring.",
    url: "https://impactradar.co",
    siteName: "Impact Radar",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Impact Radar",
    description: "Market-moving events tracked to the second",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable}`}>
      <body className={inter.className}>
        <ThemeProvider>
          <WebVitals />
          <GlobalNotificationBanner />
          {children}
          <CookieConsent />
        </ThemeProvider>
        <Script
          defer
          data-domain="impactradar.co"
          src="https://plausible.io/js/script.js"
          strategy="afterInteractive"
        />
      </body>
    </html>
  );
}
