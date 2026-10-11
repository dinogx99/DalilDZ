import type { Metadata, Viewport } from "next";

import { LanguageProvider } from "../components/LanguageProvider";
import "./style.css";

export const metadata: Metadata = {
  title: "DalilDZ — evidence engine for Algerian business verification",
  description:
    "Open-source, provenance-first verification workspace for Algerian business information. No trust score, no fraud verdict.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0d625b",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" dir="ltr">
      <body>
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
