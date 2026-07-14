import "@testing-library/jest-dom/vitest"

import { cleanup } from "@testing-library/react"
import { afterEach, vi } from "vitest"

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  }),
})

afterEach(() => {
  cleanup()
  window.localStorage.clear()
  document.documentElement.className = ""
  vi.unstubAllGlobals()
})
