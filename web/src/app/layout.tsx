import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "FixFlow", description: "Service operations workspace" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><body>{children}</body></html>;
}
