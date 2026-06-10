import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  title: "mi-saina",
  description: "Assistant IA local — mi-saina",
};

// Applique le thème sauvegardé avant le rendu (évite le flash clair/sombre).
const themeInit =
  "(function(){try{var t=localStorage.getItem('ms-theme');" +
  "if(t==='dark'||t==='light'){document.documentElement.setAttribute('data-theme',t);}}catch(e){}})();";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="h-full">
      <body className="h-full">
        {/* [mi-saina-improve] next/script (strategy beforeInteractive) au lieu d'une
            balise <script> brute dans <head> : évite l'avertissement React
            « script tag while rendering » (indicateur dev rouge sous WebKitGTK). */}
        <Script id="ms-theme-init" strategy="beforeInteractive">
          {themeInit}
        </Script>
        {children}
      </body>
    </html>
  );
}
