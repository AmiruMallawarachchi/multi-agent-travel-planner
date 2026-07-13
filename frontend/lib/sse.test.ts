import { describe, expect, it } from "vitest"

import { parseSseChunk } from "./sse"

describe("parseSseChunk", () => {
  it("keeps incomplete frames as the remainder", () => {
    const result = parseSseChunk('data: {"type":"token","content":"Hi"}\n\ndata: {"type"')

    expect(result.events).toEqual([{ type: "token", content: "Hi" }])
    expect(result.remainder).toBe('data: {"type"')
  })

  it("parses multiple complete frames", () => {
    const result = parseSseChunk(
      'data: {"type":"status","state":"ROUTING"}\n\ndata: {"type":"done"}\n\n',
    )

    expect(result.events).toEqual([
      { type: "status", state: "ROUTING" },
      { type: "done" },
    ])
    expect(result.remainder).toBe("")
  })

  it("parses structured result frames", () => {
    const result = parseSseChunk(
      'data: {"type":"result","result_type":"currency","tool":"convert_currency","data":{"converted_amount":42}}\n\n',
    )

    expect(result.events).toEqual([
      {
        type: "result",
        result_type: "currency",
        tool: "convert_currency",
        data: { converted_amount: 42 },
      },
    ])
  })
})
