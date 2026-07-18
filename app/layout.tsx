import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Joli’s Photos | Portrait & Group Photography",
  description: "Book a warm, relaxed portrait or group photo session with Joli’s Photos.",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
  openGraph: {
    title: "Joli’s Photos",
    description: "Portraits made personal.",
    images: [{ url: "/og.png", width: 1731, height: 909, alt: "Joli’s Photos — Portraits made personal." }],
  },
  twitter: { card: "summary_large_image", title: "Joli’s Photos", description: "Portraits made personal.", images: ["/og.png"] },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
