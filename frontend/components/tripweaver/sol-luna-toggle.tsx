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
              "h-8 gap-1.5 rounded-md px-1.5 text-xs font-semibold",
              !isLuna && "bg-background/70 text-foreground shadow-sm hover:bg-background/80",
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
              "h-8 gap-1.5 rounded-md px-1.5 text-xs font-semibold",
              isLuna && "bg-background/70 text-foreground shadow-sm hover:bg-background/80",
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
