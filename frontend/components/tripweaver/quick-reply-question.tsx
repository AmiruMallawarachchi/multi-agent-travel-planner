"use client"

import { useState } from "react"
import { ArrowUp } from "lucide-react"

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
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <Button
            key={option.id}
            type="button"
            variant="outline"
            size="sm"
            className={cn(
              "glass-control glass-interactive min-h-10 rounded-lg px-3 text-left",
              answeredValue === option.value && "border-ring bg-accent text-accent-foreground",
            )}
            aria-pressed={answeredValue === option.value}
            disabled={disabled || isAnswered}
            onClick={() => onAnswer(option.value)}
          >
            {option.label}
          </Button>
        ))}
        {allowCustomAnswer ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="glass-control glass-interactive min-h-10 rounded-lg px-3"
            aria-expanded={customOpen}
            disabled={disabled || isAnswered}
            onClick={() => setCustomOpen((open) => !open)}
          >
            Other
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
