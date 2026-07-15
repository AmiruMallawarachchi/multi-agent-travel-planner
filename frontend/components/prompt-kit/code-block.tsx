"use client"

import { useMemo } from "react"
import bash from "highlight.js/lib/languages/bash"
import css from "highlight.js/lib/languages/css"
import javascript from "highlight.js/lib/languages/javascript"
import json from "highlight.js/lib/languages/json"
import python from "highlight.js/lib/languages/python"
import typescript from "highlight.js/lib/languages/typescript"
import xml from "highlight.js/lib/languages/xml"
import hljs from "highlight.js/lib/core"

import { cn } from "@/lib/utils"

hljs.registerLanguage("bash", bash)
hljs.registerLanguage("css", css)
hljs.registerLanguage("html", xml)
hljs.registerLanguage("javascript", javascript)
hljs.registerLanguage("js", javascript)
hljs.registerLanguage("json", json)
hljs.registerLanguage("python", python)
hljs.registerLanguage("py", python)
hljs.registerLanguage("tsx", typescript)
hljs.registerLanguage("typescript", typescript)
hljs.registerLanguage("ts", typescript)

type DivProps = React.HTMLAttributes<HTMLDivElement>

export function CodeBlock({ className, ...props }: DivProps) {
  return <div className={cn("not-prose code-block", className)} {...props} />
}

type CodeBlockCodeProps = DivProps & {
  code: string
  language?: string
  theme?: string
}

export function CodeBlockCode({
  code,
  language = "tsx",
  theme = "github-light",
  className,
  ...props
}: CodeBlockCodeProps) {
  const html = useMemo(() => {
    const normalizedLanguage = language.toLowerCase()
    if (hljs.getLanguage(normalizedLanguage)) {
      return hljs.highlight(code, { language: normalizedLanguage }).value
    }
    return hljs.highlightAuto(code).value
  }, [code, language])

  return (
    <div className={cn("code-block-code", `theme-${theme}`, className)} {...props}>
      <pre>
        <code dangerouslySetInnerHTML={{ __html: html }} />
      </pre>
    </div>
  )
}

export function CodeBlockGroup({ className, ...props }: DivProps) {
  return <div className={cn("code-block-group", className)} {...props} />
}
