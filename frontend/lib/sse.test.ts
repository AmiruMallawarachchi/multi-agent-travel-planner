import { describe, expect, it } from "vitest";

import { detectDestination, formatDuration, formatMoney } from "./destinations";
import { parseSseStream } from "./sse";

describe("parseSseStream", () => {
  it("parses events split across network chunks", async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"token","content":"hel'));
        controller.enqueue(encoder.encode('lo"}\n\ndata: {"type":"done"}\n\n'));
        controller.close();
      },
    });

    const events = [];
    for await (const event of parseSseStream(stream)) events.push(event);

    expect(events).toEqual([
      { type: "token", content: "hello" },
      { type: "done" },
    ]);
  });
});

describe("travel formatting", () => {
  it("selects bundled destination imagery from text or IATA codes", () => {
    expect(detectDestination("A weekend in Paris").image).toBe("/images/paris.png");
    expect(detectDestination("Fly there", "LHR").city).toBe("London");
  });

  it("formats provider values for compact cards", () => {
    expect(formatDuration("PT11H30M")).toBe("11h 30m");
    expect(formatMoney("720.00", "USD")).toContain("720");
  });
});
