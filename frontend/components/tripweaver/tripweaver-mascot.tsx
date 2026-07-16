"use client"

import Image from "next/image"

import type { ChatMessage } from "@/features/tripweaver/types"
import { cn } from "@/lib/utils"

export type MascotMood = "calm" | "hello" | "question" | "success" | "thinking"

const MASCOT_ASSETS: Record<MascotMood, { alt: string; src: string }> = {
  calm: {
    alt: "TripWeaver ready to help",
    src: "/mascot/kimi_idle_calm.gif",
  },
  hello: {
    alt: "TripWeaver waving hello",
    src: "/mascot/kimi_hello_wave.gif",
  },
  question: {
    alt: "TripWeaver asking a question",
    src: "/mascot/kimi_question.gif",
  },
  success: {
    alt: "TripWeaver celebrating your answer",
    src: "/mascot/kimi_success.gif",
  },
  thinking: {
    alt: "TripWeaver thinking",
    src: "/mascot/kimi_thinking.gif",
  },
}

export function mascotMoodForMessage(message: ChatMessage): MascotMood {
  if (!message.content) return "thinking"
  if (message.quickReplies?.answeredValue) return "success"
  if (message.id.endsWith("-welcome")) return "hello"
  if (message.quickReplies?.options.length) return "question"
  return "calm"
}

export function TripWeaverMascot({
  mood,
  className,
  priority = false,
}: {
  mood: MascotMood
  className?: string
  priority?: boolean
}) {
  const asset = MASCOT_ASSETS[mood]

  return (
    <Image
      unoptimized
      priority={priority}
      draggable={false}
      width={560}
      height={560}
      src={asset.src}
      alt={asset.alt}
      className={cn("block shrink-0 select-none object-contain", className)}
    />
  )
}
