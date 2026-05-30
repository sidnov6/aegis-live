import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AEGIS Live — Chain Surveillance",
  description: "Real-time streaming AML detection on live blockchain transactions.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
