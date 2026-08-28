import '@testing-library/jest-dom/vitest'

// jsdom doesn't implement ResizeObserver — reactflow's core (used by
// PathGraph) needs one to mount at all. A no-op stub is enough for tests,
// which never assert on actual resize behavior.
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
