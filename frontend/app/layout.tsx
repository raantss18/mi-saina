import type { Metadata } from "next";
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
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="h-full">{children}</body>
    </html>
  );
}
