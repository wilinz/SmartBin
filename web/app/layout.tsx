import type { Metadata } from "next";
import { Inter, Roboto_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const robotoMono = Roboto_Mono({
  variable: "--font-roboto-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SmartBin 智能垃圾分拣系统",
  description: "AI-powered waste sorting system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${robotoMono.variable} antialiased`}
      >
        {/* 加载 OpenCV.js */}
        <Script
          src="https://docs.opencv.org/4.10.0/opencv.js"
          strategy="beforeInteractive"
        />
        {children}
      </body>
    </html>
  );
}
