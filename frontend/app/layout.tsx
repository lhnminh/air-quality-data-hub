import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AerX — Hanoi Air Intelligence",
  description: "Hanoi air-quality observations and source investigation.",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
