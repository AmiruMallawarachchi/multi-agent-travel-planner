import type { SseEvent } from "@/lib/types";

export async function* parseSseStream(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<SseEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const data = frame
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (data) yield JSON.parse(data) as SseEvent;
    }

    if (done) break;
  }

  if (buffer.trim()) {
    const line = buffer.trim();
    if (line.startsWith("data:")) {
      yield JSON.parse(line.slice(5).trimStart()) as SseEvent;
    }
  }
}
