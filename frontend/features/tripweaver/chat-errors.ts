import { readJsonObject, responseDetail } from "@/lib/http-response"

/** A chat request the backend actively rejected, carrying a message that is
 * safe and useful to show the traveller. */
export class ChatRequestError extends Error {}

/** Fallbacks used only when the backend sends no usable `detail`. Each names
 * the thing the traveller can actually act on - the old single message blamed
 * backend availability and API credentials for every failure, including
 * "your attachment is too long", which sent people looking in the wrong place. */
const STATUS_FALLBACKS: ReadonlyArray<[(status: number) => boolean, string]> = [
  [
    (status) => status === 401 || status === 403,
    "TripWeaver could not authenticate with its backend. Check the deployment's API key configuration.",
  ],
  [
    (status) => status === 413 || status === 422,
    "That message could not be sent. It may be too long - try a shorter note or a smaller attachment.",
  ],
  [
    (status) => status === 429,
    "That was a lot of messages very quickly. Wait a few seconds and try again.",
  ],
  [
    (status) => status >= 500,
    "TripWeaver's backend is having trouble right now. Try again in a moment.",
  ],
]

export async function describeFailure(response: Response): Promise<string> {
  const fallback =
    STATUS_FALLBACKS.find(([matches]) => matches(response.status))?.[1] ??
    "That request could not be completed. Try again."

  // The backend's own `detail` is written for humans ("Message exceeds 16000
  // characters"), so prefer it over anything we can infer from the status.
  return responseDetail(await readJsonObject(response), fallback)
}
