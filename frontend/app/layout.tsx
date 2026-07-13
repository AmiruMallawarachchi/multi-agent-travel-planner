import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "TripWeaver",
  description: "A minimal AI travel chat for TripWeaver.",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
