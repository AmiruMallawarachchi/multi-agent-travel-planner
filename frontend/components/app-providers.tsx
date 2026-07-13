"use client"

import { ThemeProvider } from "next-themes"

import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
      <TooltipProvider delayDuration={250}>
        {children}
        <Toaster position="bottom-right" />
      </TooltipProvider>
    </ThemeProvider>
  )
}
