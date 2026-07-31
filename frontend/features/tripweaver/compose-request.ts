import type { Attachment } from "./types"

/** Mirrors the backend's MAX_MESSAGE_LENGTH. Kept deliberately small: an
 * attachment is inlined into the message field, so this is the ceiling on how
 * much text one turn can push into the prompt. If the two ever drift, the
 * backend still rejects the request and `describeFailure` reports why. */
export const MAX_REQUEST_CHARS = Number(
  process.env.NEXT_PUBLIC_MAX_MESSAGE_CHARS ?? 6000,
)

export interface ComposedRequest {
  message: string
  /** Names of attachments that had to be shortened to fit the budget, so the
   * traveller is told rather than silently sent a truncated file. */
  trimmed: string[]
}

/** Build the outbound message, fitting attachments into the character budget.
 *
 * The typed message always wins the budget - it is what the traveller actually
 * asked. Whatever room is left is shared by the attachments, in order.
 */
export function composeRequest(
  content: string,
  attachments: Pick<Attachment, "name" | "content">[],
  limit = MAX_REQUEST_CHARS,
): ComposedRequest {
  if (attachments.length === 0) return { message: content, trimmed: [] }

  const parts = [content]
  const trimmed: string[] = []
  // Each block costs its wrapper plus the separator joining it to the previous.
  let remaining = limit - content.length

  for (const attachment of attachments) {
    const wrapper = `\n\n<attachment name="${attachment.name}">\n\n</attachment>`
    const room = remaining - wrapper.length
    if (room <= 0) {
      trimmed.push(attachment.name)
      continue
    }

    const body = attachment.content.slice(0, room)
    if (body.length < attachment.content.length) trimmed.push(attachment.name)
    parts.push(`<attachment name="${attachment.name}">\n${body}\n</attachment>`)
    remaining -= wrapper.length + body.length
  }

  return { message: parts.join("\n\n"), trimmed }
}
