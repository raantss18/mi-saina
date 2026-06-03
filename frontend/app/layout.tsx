import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "mi-saina",
  description: "Assistant IA local — mi-saina",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="h-full">
      <body className="h-full">{children}</body>
    </html>
  );
}
