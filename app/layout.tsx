import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Joli’s Photo | Portrait & Group Photography",
  description: "Book a warm, relaxed portrait or group photo session with Joli’s Photo.",
  icons: { icon: "/logo-cherry-camera.png", shortcut: "/logo-cherry-camera.png" },
  openGraph: {
    title: "Joli’s Photo",
    description: "Portraits made personal.",
    images: [{ url: "/og-cherry-anime.png", width: 1536, height: 1024, alt: "Joli’s Photo — Portraits made personal." }],
  },
  twitter: { card: "summary_large_image", title: "Joli’s Photo", description: "Portraits made personal.", images: ["/og-cherry-anime.png"] },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
