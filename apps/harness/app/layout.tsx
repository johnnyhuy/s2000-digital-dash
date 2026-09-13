import type { Metadata } from "next";
import localFont from "next/font/local";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

const shareTech = localFont({
  src: "./fonts/ShareTechMono-Regular.ttf",
  variable: "--font-share-tech",
  display: "swap",
});

const oxanium = localFont({
  src: "./fonts/Oxanium-Bold.ttf",
  weight: "700",
  variable: "--font-oxanium",
  display: "swap",
});

/** OEM face numerals / labels — rounded sans (OFL subset, see fonts/OFL-MPLUSRounded1c.txt). */
const mplus = localFont({
  src: [
    { path: "./fonts/MPLUSRounded1c-Bold.ttf", weight: "700", style: "normal" },
    { path: "./fonts/MPLUSRounded1c-ExtraBold.ttf", weight: "800", style: "normal" },
  ],
  variable: "--font-mplus",
  display: "swap",
});

export const metadata: Metadata = {
  title: "S2000 Digital Dash — unofficial DIY",
  description:
    "Shareable web demo of the S2000 digital dash (AP1 / AP2 face styles). Unofficial enthusiast project — not affiliated with Honda Motor Co., Ltd.",
  icons: { icon: "/docs/assets/honda-unofficial-mark.svg" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en-AU"
      className={`${geistSans.variable} ${geistMono.variable} ${shareTech.variable} ${oxanium.variable} ${mplus.variable} h-full antialiased`}
    >
      <body className="min-h-full">{children}</body>
    </html>
  );
}
