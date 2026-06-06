import "@testing-library/jest-dom";

// jsdom does not implement scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn();

// jsdom's default opaque origin leaves localStorage undefined — provide a simple
// in-memory implementation so storage-backed code (thème, onboarding) is testable.
if (typeof window.localStorage === "undefined") {
  const store = new Map<string, string>();
  const mock: Storage = {
    get length() { return store.size; },
    clear: () => store.clear(),
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    removeItem: (k: string) => { store.delete(k); },
    setItem: (k: string, v: string) => { store.set(k, String(v)); },
  };
  Object.defineProperty(window, "localStorage", { value: mock, configurable: true });
  Object.defineProperty(globalThis, "localStorage", { value: mock, configurable: true });
}

// jsdom does not implement EventSource — provide a minimal stub
class MockEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;

  url: string;
  readyState = MockEventSource.CONNECTING;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    this.readyState = MockEventSource.OPEN;
  }

  close() {
    this.readyState = MockEventSource.CLOSED;
  }

  addEventListener() {}
  removeEventListener() {}
}

(global as any).EventSource = MockEventSource;
