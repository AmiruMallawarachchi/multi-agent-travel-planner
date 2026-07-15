import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

import { CodeBlock, CodeBlockCode, CodeBlockGroup } from "@/components/prompt-kit/code-block"
import { cn } from "@/lib/utils"

type MarkdownProps = {
  children: string
  className?: string
}

export function Markdown({ children, className }: MarkdownProps) {
  return (
    <ReactMarkdown
      className={cn("markdown", className)}
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className: codeClassName, children: codeChildren, ...props }) {
          const code = String(codeChildren).replace(/\n$/, "")
          const match = /language-(\w+)/.exec(codeClassName ?? "")

          if (match) {
            return (
              <CodeBlock>
                <CodeBlockGroup>
                  <span>{match[1]}</span>
                </CodeBlockGroup>
                <CodeBlockCode code={code} language={match[1]} {...props} />
              </CodeBlock>
            )
          }

          return (
            <code className={codeClassName} {...props}>
              {codeChildren}
            </code>
          )
        },
      }}
    >
      {children}
    </ReactMarkdown>
  )
}
