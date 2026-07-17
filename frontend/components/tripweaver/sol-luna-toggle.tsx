"use client"

import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

export function SolLunaToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const isLuna = resolvedTheme === "dark"

  return (
    <div
      className="glass-control flex h-10 items-center gap-0.5 rounded-lg p-1"
      role="group"
      aria-label="Appearance"
    >
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={cn(
              "relative h-8 gap-1.5 rounded-md border border-transparent px-2 text-xs font-semibold transition-[background-color,border-color,box-shadow,color] focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-transparent",
              !isLuna
                ? "border-amber-600/70 bg-amber-100/95 text-amber-950 shadow-[0_2px_12px_rgba(180,83,9,0.22),inset_0_-2px_0_rgba(217,119,6,0.75)] hover:bg-amber-50"
                : "text-foreground/80 hover:border-amber-500/50 hover:bg-amber-100/70 hover:text-amber-950 dark:hover:bg-amber-300/15 dark:hover:text-amber-100",
            )}
            aria-pressed={!isLuna}
            onClick={() => setTheme("light")}
          >
            <Sun className="size-3.5" aria-hidden="true" />
            <span>SOL</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>Use the daylight appearance</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={cn(
              "relative h-8 gap-1.5 rounded-md border border-transparent px-2 text-xs font-semibold transition-[background-color,border-color,box-shadow,color] focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-transparent",
              isLuna
                ? "border-cyan-200/70 bg-slate-950/90 text-cyan-50 shadow-[0_2px_12px_rgba(8,145,178,0.3),inset_0_-2px_0_rgba(103,232,249,0.75)] hover:bg-slate-900"
                : "text-foreground/80 hover:border-indigo-500/50 hover:bg-indigo-100/75 hover:text-indigo-950 dark:hover:bg-indigo-300/15 dark:hover:text-indigo-100",
            )}
            aria-pressed={isLuna}
            onClick={() => setTheme("dark")}
          >
            <Moon className="size-3.5" aria-hidden="true" />
            <span>LUNA</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>Use the night appearance</TooltipContent>
      </Tooltip>
    </div>
  )
}
