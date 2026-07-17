"use client"

import { useState } from "react"
import { ArrowRight, ArrowUp, Check, Pencil } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { QuickReplyOption } from "@/features/tripweaver/types"
import { cn } from "@/lib/utils"

interface QuickReplyQuestionProps {
  options: QuickReplyOption[]
  allowCustomAnswer?: boolean
  answeredValue?: string
  disabled?: boolean
  onAnswer: (value: string) => void
}

export function QuickReplyQuestion({
  options,
  allowCustomAnswer = false,
  answeredValue,
  disabled = false,
  onAnswer,
}: QuickReplyQuestionProps) {
  const [customOpen, setCustomOpen] = useState(false)
  const [customValue, setCustomValue] = useState("")
  const isAnswered = Boolean(answeredValue)

  function submitCustom() {
    const value = customValue.trim()
    if (!value || disabled || isAnswered) return
    onAnswer(value)
  }

  return (
    <div className="glass-divider mt-3 border-t pt-3" aria-label="Suggested answers">
      <div className="space-y-1" role="group" aria-label="Answer choices">
        {options.map((option, index) => (
          <Button
            key={option.id}
            type="button"
            variant="outline"
            className={cn(
              "glass-control glass-interactive h-auto min-h-11 w-full justify-start gap-3 rounded-lg px-2.5 py-2 text-left",
              answeredValue === option.value &&
                "border-ring bg-accent text-accent-foreground opacity-100",
            )}
            aria-label={option.label}
            aria-pressed={answeredValue === option.value}
            disabled={disabled || isAnswered}
            onClick={() => onAnswer(option.value)}
          >
            <span className="glass-control flex size-7 shrink-0 items-center justify-center rounded-md text-xs font-semibold">
              {index + 1}
            </span>
            <span className="min-w-0 flex-1 whitespace-normal">{option.label}</span>
            {answeredValue === option.value ? (
              <Check className="size-4 shrink-0 text-emerald-600" aria-hidden="true" />
            ) : (
              <ArrowRight className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            )}
          </Button>
        ))}
        {allowCustomAnswer ? (
          <Button
            type="button"
            variant="outline"
            className="glass-control glass-interactive h-auto min-h-11 w-full justify-start gap-3 rounded-lg px-2.5 py-2"
            aria-label="Something else"
            aria-expanded={customOpen}
            disabled={disabled || isAnswered}
            onClick={() => setCustomOpen((open) => !open)}
          >
            <span className="glass-control flex size-7 shrink-0 items-center justify-center rounded-md">
              <Pencil className="size-3.5" aria-hidden="true" />
            </span>
            Something else
          </Button>
        ) : null}
      </div>

      {customOpen && !isAnswered ? (
        <div className="mt-2 flex gap-2">
          <Input
            autoFocus
            aria-label="Custom answer"
            placeholder="Type your answer..."
            className="glass-control min-h-11 flex-1"
            value={customValue}
            disabled={disabled}
            onChange={(event) => setCustomValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") submitCustom()
            }}
          />
          <Button
            type="button"
            size="icon"
            className="size-11 shrink-0 rounded-lg"
            aria-label="Send custom answer"
            disabled={disabled || !customValue.trim()}
            onClick={submitCustom}
          >
            <ArrowUp aria-hidden="true" />
          </Button>
        </div>
      ) : null}
    </div>
  )
}
